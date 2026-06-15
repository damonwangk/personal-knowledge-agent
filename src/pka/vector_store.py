from __future__ import annotations

from pathlib import Path

import chromadb

from .bm25 import BM25Index
from .chunking import Chunk
from .query import expand_query


class VectorStore:
    def __init__(self, index_dir: Path) -> None:
        self.index_dir = index_dir
        self.client = chromadb.PersistentClient(path=str(index_dir / "chroma"))
        self.collection = self.client.get_or_create_collection(name="knowledge")
        self.bm25 = BM25Index(index_dir)

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
        return self.bm25.search(expanded_query, top_k)

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

    def rebuild_bm25(self) -> None:
        rows = self.all_documents()
        self.bm25.save(rows)

    def all_documents(self) -> list[dict]:
        result = self.collection.get(include=["documents", "metadatas"])
        return [
            {
                "id": chunk_id,
                "text": document or "",
                "metadata": metadata or {},
            }
            for chunk_id, document, metadata in zip(result["ids"], result["documents"], result["metadatas"])
        ]
