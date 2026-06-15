from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
import re

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
        end = choose_chunk_end(text, start, size, doc.source_type)
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
        start = next_chunk_start(text, end, overlap)
    return chunks


def normalize_text(doc: SourceDocument) -> tuple[str, list[tuple[int, int, int]]]:
    lines = doc.lines or [(index, line.rstrip()) for index, line in enumerate(doc.text.splitlines(), start=1)]
    parts: list[str] = []
    spans: list[tuple[int, int, int]] = []
    cursor = 0
    for line_no, line in lines:
        clean = line.rstrip()
        if not clean:
            if parts and parts[-1] != "\n\n":
                parts.append("\n\n")
                cursor += 2
            continue
        if parts:
            separator = "" if parts[-1] == "\n\n" else "\n"
            parts.append(separator)
            cursor += len(separator)
        start = cursor
        parts.append(clean)
        cursor += len(clean)
        spans.append((start, cursor, line_no))
    return "".join(parts).rstrip(), spans


def choose_chunk_end(text: str, start: int, size: int, source_type: str) -> int:
    hard_end = min(start + size, len(text))
    if hard_end == len(text):
        return hard_end

    window = text[start:hard_end]
    min_offset = max(int(size * 0.45), 300)
    candidates: list[int] = []

    if source_type in {"md", "mdx"}:
        # Markdown 优先在下一个标题前截断，减少把一个章节切散的概率。
        candidates.extend(match.start() for match in re.finditer(r"\n#{1,6}\s+", window))

    candidates.extend(match.end() for match in re.finditer(r"\n\s*\n", window))
    candidates.extend(match.end() for match in re.finditer(r"[。！？.!?]\s+", window))
    candidates.extend(match.end() for match in re.finditer(r"\n", window))

    valid = [start + offset for offset in candidates if offset >= min_offset]
    return max(valid) if valid else hard_end


def next_chunk_start(text: str, end: int, overlap: int) -> int:
    start = max(0, end - overlap)
    if start == 0:
        return start

    # 重叠区也尽量从自然边界开始，避免下一块开头落在半句话中间。
    boundary = text.find("\n\n", start, end)
    if boundary != -1:
        return boundary + 2
    return start


def lines_for_span(spans: list[tuple[int, int, int]], start: int, end: int) -> tuple[int | None, int | None]:
    matched = [line_no for line_start, line_end, line_no in spans if line_end > start and line_start < end]
    if not matched:
        return None, None
    return min(matched), max(matched)
