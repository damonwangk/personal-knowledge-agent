from __future__ import annotations

from .config import AppConfig
from .graphs import build_ask_graph, build_ingest_graph, build_summarize_graph


def ingest(config: AppConfig, target: str) -> tuple[int, int, int]:
    state = build_ingest_graph().invoke({"config": config, "target": target})
    return (
        int(state.get("doc_count", 0)),
        int(state.get("chunk_count", 0)),
        int(state.get("skipped_source_count", 0)),
    )


def ask(config: AppConfig, question: str) -> str:
    state = build_ask_graph().invoke({"config": config, "question": question})
    return str(state.get("answer", ""))


def summarize(config: AppConfig, target: str) -> str:
    state = build_summarize_graph().invoke({"config": config, "target": target})
    return str(state.get("summary", ""))
