from __future__ import annotations

from pathlib import Path

import chromadb

from .chunking import Chunk
from .query import expand_query, tokenize_query


class VectorStore:
    def __init__(self, index_dir: Path) -> None:
        self.client = chromadb.PersistentClient(path=str(index_dir / "chroma"))
        self.collection = self.client.get_or_create_collection(name="knowledge")

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        self.collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
            embeddings=embeddings,
        )

    def delete_ids(self, ids: list[str]) -> None:
        if ids:
            self.collection.delete(ids=ids)

    def delete_source(self, source_key: str) -> None:
        result = self.collection.get(include=["metadatas"])
        ids_to_delete = [
            chunk_id
            for chunk_id, metadata in zip(result["ids"], result["metadatas"])
            if metadata.get("source_key") == source_key or metadata.get("source_id") == source_key
        ]
        self.delete_ids(ids_to_delete)

    def query(self, embedding: list[float], top_k: int) -> list[dict]:
        result = self.collection.query(query_embeddings=[embedding], n_results=top_k)
        rows: list[dict] = []
        for index, chunk_id in enumerate(result["ids"][0]):
            rows.append(
                {
                    "id": chunk_id,
                    "text": result["documents"][0][index],
                    "metadata": result["metadatas"][0][index],
                    "distance": result["distances"][0][index],
                }
            )
        return rows

    def keyword_query(self, query: str, top_k: int) -> list[dict]:
        expanded_query = expand_query(query)
        terms = tokenize_query(expanded_query)
        if not terms:
            return []

        result = self.collection.get(include=["documents", "metadatas"])
        rows: list[dict] = []
        for chunk_id, document, metadata in zip(result["ids"], result["documents"], result["metadatas"]):
            if not document:
                continue
            score = keyword_score(document, terms, expanded_query, metadata)
            if score > 0:
                rows.append(
                    {
                        "id": chunk_id,
                        "text": document,
                        "metadata": metadata,
                        "keyword_score": score,
                    }
                )
        rows.sort(key=lambda row: row["keyword_score"], reverse=True)
        return rows[:top_k]

    def hybrid_query(self, embedding: list[float], query: str, top_k: int) -> list[dict]:
        vector_rows = self.query(embedding, top_k)
        keyword_rows = self.keyword_query(query, top_k)

        merged: dict[str, dict] = {}
        for rank, row in enumerate(vector_rows, start=1):
            row["vector_rank"] = rank
            row["hybrid_score"] = row.get("hybrid_score", 0) + 1 / rank
            merged[row["id"]] = row

        for rank, row in enumerate(keyword_rows, start=1):
            existing = merged.get(row["id"], row)
            existing["keyword_rank"] = rank
            existing["keyword_score"] = row["keyword_score"]
            # 定义类问题更依赖精确术语命中，关键词召回权重略高于纯语义召回。
            existing["hybrid_score"] = existing.get("hybrid_score", 0) + 1.2 / rank
            merged[row["id"]] = existing

        return sorted(merged.values(), key=lambda row: row.get("hybrid_score", 0), reverse=True)[:top_k]


def keyword_score(text: str, terms: list[str], query: str, metadata: dict) -> float:
    lower = text.lower()
    title = str(metadata.get("title", "")).lower()
    score = sum(lower.count(term) for term in terms)

    # 缩写定义常出现在标题、摘要页或文档开头，这里给定义页一点优先级。
    if "retrieval augmented generation" in query.lower() and "retrieval-augmented generation" in lower:
        score += 25
    if any(term in title for term in terms):
        score += 5
    if metadata.get("page") == 1:
        score += 4
    if metadata.get("start_char") == 0:
        score += 2
    return score
