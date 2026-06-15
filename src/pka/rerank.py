from __future__ import annotations

from functools import cached_property

from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @cached_property
    def model(self) -> CrossEncoder:
        return CrossEncoder(self.model_name)

    def rerank(self, query: str, rows: list[dict], top_k: int) -> list[dict]:
        if not rows:
            return []
        pairs = [(query, row["text"]) for row in rows]
        try:
            scores = self.model.predict(pairs)
        except Exception:
            return rows[:top_k]

        ranked: list[dict] = []
        for row, score in zip(rows, scores):
            item = dict(row)
            # rerank 分数单独保存，方便调试时区分召回分和重排分。
            item["rerank_score"] = float(score)
            ranked.append(item)
        ranked.sort(key=lambda item: item["rerank_score"], reverse=True)
        return ranked[:top_k]
