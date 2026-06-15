from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .chunking import Chunk, chunk_document
from .config import AppConfig
from .embeddings import LocalEmbedder
from .index_manifest import IndexManifest, SourceRecord
from .llm import answer_with_deepseek, format_source, summarize_with_deepseek
from .loaders import SourceDocument, discover_sources, load_input, source_fingerprint
from .query import expand_query
from .vector_store import VectorStore


class IngestState(TypedDict, total=False):
    config: AppConfig
    target: str
    docs: list[SourceDocument]
    chunks: list[Chunk]
    embeddings: list[list[float]]
    changed_sources: list[dict[str, str]]
    old_chunk_ids: list[str]
    doc_count: int
    chunk_count: int
    skipped_source_count: int


class AskState(TypedDict, total=False):
    config: AppConfig
    question: str
    expanded_question: str
    query_embedding: list[float]
    contexts: list[dict]
    answer: str


class SummarizeState(TypedDict, total=False):
    config: AppConfig
    target: str
    docs: list[SourceDocument]
    text: str
    title: str
    summary: str


def build_ingest_graph():
    graph = StateGraph(IngestState)
    graph.add_node("load", _load_ingest_docs)
    graph.add_node("chunk", _chunk_ingest_docs)
    graph.add_node("embed", _embed_chunks)
    graph.add_node("store", _store_chunks)
    graph.add_edge(START, "load")
    graph.add_edge("load", "chunk")
    graph.add_edge("chunk", "embed")
    graph.add_edge("embed", "store")
    graph.add_edge("store", END)
    return graph.compile()


def build_ask_graph():
    graph = StateGraph(AskState)
    graph.add_node("embed_query", _embed_query)
    graph.add_node("retrieve", _retrieve_contexts)
    graph.add_node("generate", _generate_answer)
    graph.add_edge(START, "embed_query")
    graph.add_edge("embed_query", "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


def build_summarize_graph():
    graph = StateGraph(SummarizeState)
    graph.add_node("load", _load_summary_docs)
    graph.add_node("generate", _generate_summary)
    graph.add_edge(START, "load")
    graph.add_edge("load", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


def _load_ingest_docs(state: IngestState) -> IngestState:
    config = state["config"]
    manifest = IndexManifest(config.index_dir)
    docs: list[SourceDocument] = []
    changed_sources: list[dict[str, str]] = []
    old_chunk_ids: list[str] = []
    skipped = 0

    for source in discover_sources(state["target"]):
        source_key, source_hash = source_fingerprint(source)
        if manifest.unchanged(source_key, source_hash):
            skipped += 1
            continue
        old_chunk_ids.extend(manifest.old_chunk_ids(source_key))
        docs.extend(load_input(source))
        changed_sources.append({"source_key": source_key, "source_hash": source_hash})

    return {
        "docs": docs,
        "doc_count": len(docs),
        "changed_sources": changed_sources,
        "old_chunk_ids": old_chunk_ids,
        "skipped_source_count": skipped,
    }


def _chunk_ingest_docs(state: IngestState) -> IngestState:
    config = state["config"]
    chunks: list[Chunk] = []
    for doc in state.get("docs", []):
        chunks.extend(chunk_document(doc, config.chunk_size_chars, config.chunk_overlap_chars))
    return {"chunks": chunks, "chunk_count": len(chunks)}


def _embed_chunks(state: IngestState) -> IngestState:
    chunks = state.get("chunks", [])
    if not chunks:
        return {"embeddings": []}
    embedder = LocalEmbedder(state["config"].embedding_model)
    return {"embeddings": embedder.encode([chunk.text for chunk in chunks])}


def _store_chunks(state: IngestState) -> IngestState:
    # 变化的 source 先删除旧 chunk，再写入新 chunk，避免旧内容残留。
    store = VectorStore(state["config"].index_dir)
    store.delete_ids(state.get("old_chunk_ids", []))
    for source in state.get("changed_sources", []):
        store.delete_source(source["source_key"])
    chunks = state.get("chunks", [])
    store.upsert(chunks, state.get("embeddings", []))

    manifest = IndexManifest(state["config"].index_dir)
    chunks_by_source: dict[str, list[str]] = {}
    for chunk in chunks:
        source_key = str(chunk.metadata["source_key"])
        chunks_by_source.setdefault(source_key, []).append(chunk.id)

    for source in state.get("changed_sources", []):
        manifest.update_source(
            SourceRecord(
                source_key=source["source_key"],
                source_hash=source["source_hash"],
                chunk_ids=chunks_by_source.get(source["source_key"], []),
            )
        )
    manifest.save()
    return {}


def _embed_query(state: AskState) -> AskState:
    expanded_question = expand_query(state["question"])
    embedder = LocalEmbedder(state["config"].embedding_model)
    return {"expanded_question": expanded_question, "query_embedding": embedder.encode([expanded_question])[0]}


def _retrieve_contexts(state: AskState) -> AskState:
    store = VectorStore(state["config"].index_dir)
    contexts = store.hybrid_query(
        state["query_embedding"],
        state.get("expanded_question", state["question"]),
        state["config"].top_k,
    )
    return {"contexts": contexts}


def _generate_answer(state: AskState) -> AskState:
    contexts = state.get("contexts", [])
    if not contexts:
        return {"answer": "没有在本地知识库中找到相关资料。"}

    generated = answer_with_deepseek(state["config"], state["question"], contexts)
    if generated:
        return {"answer": generated + "\n\n" + render_sources(contexts)}

    lines = ["未设置 DEEPSEEK_API_KEY，以下是本地检索到的相关片段："]
    for i, item in enumerate(contexts, start=1):
        snippet = item["text"].replace("\n", " ")[:450]
        lines.append(f"\n[{i}] {snippet}\n来源: {format_source(item['metadata'])}")
    return {"answer": "\n".join(lines)}


def _load_summary_docs(state: SummarizeState) -> SummarizeState:
    docs = load_input(state["target"])
    text = "\n\n".join(doc.text for doc in docs)
    target = state["target"]
    title = Path(target).name if not target.startswith("http") else target
    return {"docs": docs, "text": text, "title": title}


def _generate_summary(state: SummarizeState) -> SummarizeState:
    generated = summarize_with_deepseek(state["config"], state["title"], state["text"])
    if generated:
        return {"summary": generated}

    preview = state.get("text", "").replace("\n", " ")[:1200]
    return {"summary": f"未设置 DEEPSEEK_API_KEY，离线摘要预览：\n\n{preview}"}


def render_sources(contexts: list[dict]) -> str:
    lines = ["Sources:"]
    seen: set[str] = set()
    for item in contexts:
        source = format_source(item["metadata"])
        if source not in seen:
            lines.append(f"- {source}")
            seen.add(source)
    return "\n".join(lines)
