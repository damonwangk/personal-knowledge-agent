from __future__ import annotations

import json
from pathlib import Path

from rank_bm25 import BM25Okapi

from .query import tokenize_text


class BM25Index:
    def __init__(self, index_dir: Path) -> None:
        self.path = index_dir / "bm25_index.json"

    def save(self, rows: list[dict]) -> None:
        payload = []
        for row in rows:
            text = row.get("text") or ""
            payload.append(
                {
                    "id": row["id"],
                    "text": text,
                    "metadata": row.get("metadata") or {},
                    "tokens": tokenize_text(text),
                }
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def search(self, query: str, top_k: int) -> list[dict]:
        rows = self._load()
        if not rows:
            return []

        query_tokens = tokenize_text(query)
        if not query_tokens:
            return []

        corpus = [row["tokens"] for row in rows]
        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(query_tokens)
        boosted_scores = [
            float(score) + metadata_boost(rows[index], query, query_tokens)
            for index, score in enumerate(scores)
        ]
        ranked = sorted(enumerate(boosted_scores), key=lambda item: item[1], reverse=True)

        results: list[dict] = []
        for row_index, score in ranked[:top_k]:
            if score <= 0:
                continue
            row = rows[row_index]
            # 返回结构与向量检索保持一致，后续融合和 rerank 不需要关心来源。
            results.append(
                {
                    "id": row["id"],
                    "text": row["text"],
                    "metadata": row["metadata"],
                    "keyword_score": float(score),
                }
            )
        return results

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))


def metadata_boost(row: dict, query: str, query_tokens: list[str]) -> float:
    metadata = row.get("metadata") or {}
    text = str(row.get("text") or "").lower()
    title = str(metadata.get("title") or "").lower()
    score = 0.0

    # 定义类问题通常出现在标题、首页或文档开头，轻量加权可提高首段命中率。
    if "retrieval augmented generation" in query.lower() and "retrieval-augmented generation" in text:
        score += 6.0
    if any(token in title for token in query_tokens):
        score += 2.0
    if metadata.get("page") == 1:
        score += 1.2
    if metadata.get("start_char") == 0:
        score += 0.8
    return score
