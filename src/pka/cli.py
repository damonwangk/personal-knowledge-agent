from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .rag import ask, ingest, summarize


def main() -> None:
    parser = argparse.ArgumentParser(prog="pka", description="Personal Knowledge Agent")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="创建本地索引目录")

    ingest_parser = sub.add_parser("ingest", help="导入文件夹、文件或 URL")
    ingest_parser.add_argument("target")

    ask_parser = sub.add_parser("ask", help="基于知识库问答")
    ask_parser.add_argument("question")

    summary_parser = sub.add_parser("summarize", help="摘要文件、文件夹或 URL")
    summary_parser.add_argument("target")

    args = parser.parse_args()
    config = load_config(Path.cwd())

    if args.command == "init":
        config.index_dir.mkdir(parents=True, exist_ok=True)
        print(f"已创建索引目录: {config.index_dir}")
        return

    if args.command == "ingest":
        doc_count, chunk_count, skipped_count = ingest(config, args.target)
        print(f"导入完成: {doc_count} 个文档单元，{chunk_count} 个文本块，跳过 {skipped_count} 个未变化来源")
        return

    if args.command == "ask":
        print(ask(config, args.question))
        return

    if args.command == "summarize":
        print(summarize(config, args.target))
