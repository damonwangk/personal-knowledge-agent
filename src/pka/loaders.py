from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


SUPPORTED_SUFFIXES = {".md", ".mdx", ".txt", ".pdf", ".html", ".htm"}


@dataclass(frozen=True)
class SourceDocument:
    text: str
    source_id: str
    source_key: str
    source_hash: str
    source_type: str
    title: str
    page: int | None = None
    source_url: str | None = None
    lines: list[tuple[int, str]] | None = None


def is_url(value: str) -> bool:
    return urlparse(value).scheme in {"http", "https"}


def load_input(value: str) -> list[SourceDocument]:
    if is_url(value):
        return [load_url(value)]

    path = Path(value).expanduser().resolve()
    if path.is_dir():
        docs: list[SourceDocument] = []
        for file_path in sorted(path.rglob("*")):
            if file_path.suffix.lower() in SUPPORTED_SUFFIXES:
                docs.extend(load_file(file_path))
        return docs
    return load_file(path)


def discover_sources(value: str) -> list[str]:
    if is_url(value):
        return [value]

    path = Path(value).expanduser().resolve()
    if path.is_dir():
        return [
            str(file_path)
            for file_path in sorted(path.rglob("*"))
            if file_path.suffix.lower() in SUPPORTED_SUFFIXES
        ]
    return [str(path)]


def source_fingerprint(value: str) -> tuple[str, str]:
    if is_url(value):
        response = requests.get(value, timeout=20, headers={"User-Agent": "pka/0.1"})
        response.raise_for_status()
        return value, sha256(response.content).hexdigest()

    path = Path(value).expanduser().resolve()
    return str(path), sha256(path.read_bytes()).hexdigest()


def load_file(path: Path) -> list[SourceDocument]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".mdx", ".txt", ".html", ".htm"}:
        raw_text = path.read_text(encoding="utf-8", errors="ignore")
        text = raw_text
        title = path.name
        source_url = None
        source_type = suffix.lstrip(".")
        if suffix in {".html", ".htm"}:
            text, title, source_url = html_to_text(raw_text, path.as_uri())
            source_type = "web"
        return [
            SourceDocument(
                text=text,
                source_id=str(path),
                source_key=str(path),
                source_hash=sha256(path.read_bytes()).hexdigest(),
                source_type=source_type,
                title=title,
                source_url=source_url,
                lines=numbered_lines(text),
            )
        ]
    if suffix == ".pdf":
        return load_pdf(path)
    raise ValueError(f"Unsupported file type: {path}")


def load_pdf(path: Path) -> list[SourceDocument]:
    reader = PdfReader(str(path))
    file_hash = sha256(path.read_bytes()).hexdigest()
    docs: list[SourceDocument] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            docs.append(
                SourceDocument(
                    text=text,
                    source_id=str(path),
                    source_key=str(path),
                    source_hash=file_hash,
                    source_type="pdf",
                    title=path.name,
                    page=index,
                )
            )
    return docs


def load_url(url: str) -> SourceDocument:
    response = requests.get(url, timeout=20, headers={"User-Agent": "pka/0.1"})
    response.raise_for_status()
    text, title, source_url = html_to_text(response.text, url)
    return SourceDocument(
        text=text,
        source_id=source_url or url,
        source_key=url,
        source_hash=sha256(response.content).hexdigest(),
        source_type="web",
        title=title,
        source_url=source_url or url,
        lines=numbered_lines(text),
    )


def html_to_text(html: str, base_url: str) -> tuple[str, str, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title, source_url = html_title_and_url(str(soup), base_url)
    text = soup.get_text("\n", strip=True)
    return text, title, source_url


def html_title_and_url(html: str, base_url: str) -> tuple[str, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else base_url
    canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
    if canonical and canonical.get("href"):
        return title, urljoin(base_url, str(canonical["href"]))
    og_url = soup.find("meta", property="og:url")
    if og_url and og_url.get("content"):
        return title, urljoin(base_url, str(og_url["content"]))
    return title, None


def numbered_lines(text: str) -> list[tuple[int, str]]:
    return [(line_no, line.rstrip()) for line_no, line in enumerate(text.splitlines(), start=1)]
