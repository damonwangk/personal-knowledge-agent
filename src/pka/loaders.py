from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urljoin, urlparse

import fitz
import requests
from bs4 import BeautifulSoup
from PIL import Image
from pypdf import PdfReader
import pytesseract
from readability import Document


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


def load_input(
    value: str,
    *,
    pdf_ocr_enabled: bool = False,
    pdf_ocr_language: str = "eng",
    pdf_min_extracted_chars: int = 80,
) -> list[SourceDocument]:
    if is_url(value):
        return [load_url(value)]

    path = Path(value).expanduser().resolve()
    if path.is_dir():
        docs: list[SourceDocument] = []
        for file_path in sorted(path.rglob("*")):
            if file_path.suffix.lower() in SUPPORTED_SUFFIXES:
                docs.extend(
                    load_file(
                        file_path,
                        pdf_ocr_enabled=pdf_ocr_enabled,
                        pdf_ocr_language=pdf_ocr_language,
                        pdf_min_extracted_chars=pdf_min_extracted_chars,
                    )
                )
        return docs
    return load_file(
        path,
        pdf_ocr_enabled=pdf_ocr_enabled,
        pdf_ocr_language=pdf_ocr_language,
        pdf_min_extracted_chars=pdf_min_extracted_chars,
    )


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


def load_file(
    path: Path,
    *,
    pdf_ocr_enabled: bool = False,
    pdf_ocr_language: str = "eng",
    pdf_min_extracted_chars: int = 80,
) -> list[SourceDocument]:
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
        return load_pdf(
            path,
            ocr_enabled=pdf_ocr_enabled,
            ocr_language=pdf_ocr_language,
            min_extracted_chars=pdf_min_extracted_chars,
        )
    raise ValueError(f"Unsupported file type: {path}")


def load_pdf(
    path: Path,
    *,
    ocr_enabled: bool = False,
    ocr_language: str = "eng",
    min_extracted_chars: int = 80,
) -> list[SourceDocument]:
    reader = PdfReader(str(path))
    file_hash = sha256(path.read_bytes()).hexdigest()
    docs: list[SourceDocument] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if ocr_enabled and len(text.strip()) < min_extracted_chars:
            text = ocr_pdf_page(path, index, ocr_language) or text
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


def ocr_pdf_page(path: Path, page_number: int, language: str) -> str:
    configure_tesseract()
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return ""

    try:
        with TemporaryDirectory() as tmp_dir:
            document = fitz.open(str(path))
            page = document.load_page(page_number - 1)
            # 2 倍缩放约等于 144 DPI，速度和识别质量对小型样本比较均衡。
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image_path = Path(tmp_dir) / f"page-{page_number}.png"
            pixmap.save(str(image_path))
            image = Image.open(image_path)
            try:
                return pytesseract.image_to_string(image, lang=language).strip()
            except pytesseract.TesseractError:
                return pytesseract.image_to_string(image, lang="eng").strip()
    except Exception:
        return ""


def configure_tesseract() -> None:
    if shutil.which("tesseract"):
        return
    env_tesseract = Path(sys.executable).resolve().parent / "tesseract"
    if env_tesseract.exists():
        pytesseract.pytesseract.tesseract_cmd = str(env_tesseract)


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
    title, source_url = html_title_and_url(html, base_url)
    try:
        # Readability 先抽正文，失败时再回退到普通 HTML 清洗。
        article = Document(html)
        readable_html = article.summary(html_partial=True)
        title = article.short_title() or title
        soup = BeautifulSoup(readable_html, "html.parser")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
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
