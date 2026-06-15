from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppConfig:
    root: Path
    knowledge_root: Path
    index_dir: Path
    embedding_model: str
    llm_base_url: str
    llm_model: str
    chunk_size_chars: int
    chunk_overlap_chars: int
    top_k: int
    candidate_k: int
    rerank_enabled: bool
    rerank_model: str
    pdf_ocr_enabled: bool
    pdf_ocr_language: str
    pdf_min_extracted_chars: int


def load_config(project_root: Path | None = None) -> AppConfig:
    root = project_root or Path.cwd()
    config_path = root / "pka.yaml"
    data: dict[str, Any] = {}
    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    embedding = data.get("embedding", {})
    llm = data.get("llm", {})
    retrieval = data.get("retrieval", {})
    rerank = data.get("rerank", {})
    pdf = data.get("pdf", {})

    return AppConfig(
        root=root,
        knowledge_root=(root / data.get("knowledge_root", "data")).resolve(),
        index_dir=(root / data.get("index_dir", ".pka")).resolve(),
        embedding_model=embedding.get("model", "sentence-transformers/all-MiniLM-L6-v2"),
        llm_base_url=llm.get("base_url", "https://api.deepseek.com"),
        llm_model=llm.get("model", "deepseek-v4-flash"),
        chunk_size_chars=int(retrieval.get("chunk_size_chars", 1600)),
        chunk_overlap_chars=int(retrieval.get("chunk_overlap_chars", 220)),
        top_k=int(retrieval.get("top_k", 5)),
        candidate_k=int(retrieval.get("candidate_k", max(int(retrieval.get("top_k", 5)) * 2, 10))),
        rerank_enabled=bool(rerank.get("enabled", True)),
        rerank_model=rerank.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
        pdf_ocr_enabled=bool(pdf.get("ocr_enabled", True)),
        pdf_ocr_language=pdf.get("ocr_language", "eng+chi_sim"),
        pdf_min_extracted_chars=int(pdf.get("min_extracted_chars", 80)),
    )
