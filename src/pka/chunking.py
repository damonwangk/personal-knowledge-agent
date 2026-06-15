from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

from .loaders import SourceDocument


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    metadata: dict[str, str | int]


def chunk_document(doc: SourceDocument, size: int, overlap: int) -> list[Chunk]:
    text, spans = normalize_text(doc)
    if not text:
        return []

    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk_text = text[start:end].strip()
        if chunk_text:
            # 这里用内容和位置生成稳定 ID，便于重复导入时覆盖旧向量。
            raw_id = f"{doc.source_id}:{doc.page or 0}:{start}:{sha1(chunk_text.encode()).hexdigest()}"
            metadata: dict[str, str | int] = {
                "source_id": doc.source_id,
                "source_key": doc.source_key,
                "source_hash": doc.source_hash,
                "source_type": doc.source_type,
                "title": doc.title,
                "start_char": start,
                "end_char": end,
            }
            if doc.page is not None:
                metadata["page"] = doc.page
            if doc.source_url:
                metadata["source_url"] = doc.source_url
            start_line, end_line = lines_for_span(spans, start, end)
            if start_line is not None and end_line is not None:
                metadata["start_line"] = start_line
                metadata["end_line"] = end_line
            chunks.append(Chunk(id=sha1(raw_id.encode()).hexdigest(), text=chunk_text, metadata=metadata))
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def normalize_text(doc: SourceDocument) -> tuple[str, list[tuple[int, int, int]]]:
    lines = doc.lines or [(index, line.rstrip()) for index, line in enumerate(doc.text.splitlines(), start=1)]
    parts: list[str] = []
    spans: list[tuple[int, int, int]] = []
    cursor = 0
    for line_no, line in lines:
        clean = line.rstrip()
        if not clean:
            continue
        if parts:
            parts.append("\n")
            cursor += 1
        start = cursor
        parts.append(clean)
        cursor += len(clean)
        spans.append((start, cursor, line_no))
    return "".join(parts), spans


def lines_for_span(spans: list[tuple[int, int, int]], start: int, end: int) -> tuple[int | None, int | None]:
    matched = [line_no for line_start, line_end, line_no in spans if line_end > start and line_start < end]
    if not matched:
        return None, None
    return min(matched), max(matched)
