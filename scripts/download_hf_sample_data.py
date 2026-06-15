from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://datasets-server.huggingface.co"


DATASETS = [
    {
        "dataset": "HuggingFaceFW/fineweb-edu",
        "config": "default",
        "split": "train",
        "length": 6,
        "formatter": "fineweb_edu",
    },
    {
        "dataset": "sentence-transformers/natural-questions",
        "config": "pair",
        "split": "train",
        "length": 8,
        "formatter": "natural_questions",
    },
    {
        "dataset": "MongoDB/embedded_movies",
        "config": "default",
        "split": "train",
        "length": 8,
        "formatter": "embedded_movies",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download small Hugging Face dataset samples.")
    parser.add_argument("--output", default="data/hf", help="Output directory inside the project.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing sample files.")
    args = parser.parse_args()

    output_dir = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    for spec in DATASETS:
        target = output_dir / f"{slug(spec['dataset'])}.md"
        if target.exists() and not args.overwrite:
            print(f"skip {target.relative_to(ROOT)}")
            continue
        rows = fetch_rows(spec)
        content = render_markdown(spec, rows)
        target.write_text(content, encoding="utf-8")
        print(f"downloaded {target.relative_to(ROOT)}")


def fetch_rows(spec: dict[str, Any]) -> list[dict[str, Any]]:
    response = requests.get(
        f"{API_BASE}/rows",
        params={
            "dataset": spec["dataset"],
            "config": spec["config"],
            "split": spec["split"],
            "offset": 0,
            "length": spec["length"],
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    return [item["row"] for item in payload.get("rows", [])]


def render_markdown(spec: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# Hugging Face sample: {spec['dataset']}",
        "",
        f"- Dataset: `{spec['dataset']}`",
        f"- Config: `{spec['config']}`",
        f"- Split: `{spec['split']}`",
        "- Source: Hugging Face Dataset Viewer API",
        "",
    ]
    formatter = FORMATTERS[spec["formatter"]]
    for index, row in enumerate(rows, start=1):
        lines.extend(formatter(index, row))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def format_fineweb_edu(index: int, row: dict[str, Any]) -> list[str]:
    text = truncate(str(row.get("text") or ""), 3500)
    return [
        f"## FineWeb-Edu sample {index}",
        "",
        f"- URL: {row.get('url') or 'unknown'}",
        f"- Dump: {row.get('dump') or 'unknown'}",
        f"- Language: {row.get('language') or 'unknown'}",
        "",
        text,
    ]


def format_natural_questions(index: int, row: dict[str, Any]) -> list[str]:
    return [
        f"## Natural Questions sample {index}",
        "",
        f"Question: {row.get('query') or ''}",
        "",
        f"Answer: {truncate(str(row.get('answer') or ''), 2500)}",
    ]


def format_embedded_movies(index: int, row: dict[str, Any]) -> list[str]:
    genres = ", ".join(row.get("genres") or [])
    directors = ", ".join(row.get("directors") or [])
    cast = ", ".join((row.get("cast") or [])[:8])
    fullplot = row.get("fullplot") or row.get("plot") or ""
    return [
        f"## Movie sample {index}: {row.get('title') or 'Untitled'}",
        "",
        f"- Genres: {genres or 'unknown'}",
        f"- Directors: {directors or 'unknown'}",
        f"- Cast: {cast or 'unknown'}",
        f"- Runtime: {row.get('runtime') or 'unknown'}",
        "",
        truncate(str(fullplot), 2200),
    ]


def truncate(text: str, limit: int) -> str:
    clean = re.sub(r"\n{3,}", "\n\n", text.strip())
    return clean if len(clean) <= limit else clean[:limit].rstrip() + "\n\n[truncated]"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


FORMATTERS = {
    "fineweb_edu": format_fineweb_edu,
    "natural_questions": format_natural_questions,
    "embedded_movies": format_embedded_movies,
}


if __name__ == "__main__":
    main()
