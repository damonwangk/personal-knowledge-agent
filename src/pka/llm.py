from __future__ import annotations

import os

from openai import OpenAI
from dotenv import load_dotenv

from .config import AppConfig


def answer_with_deepseek(config: AppConfig, question: str, contexts: list[dict]) -> str | None:
    # 从项目本地 .env 读取密钥，避免每次手动 export。
    load_dotenv(config.root / ".env")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None

    source_text = "\n\n".join(
        f"[{i}] {item['text']}\n来源: {format_source(item['metadata'])}"
        for i, item in enumerate(contexts, start=1)
    )
    client = OpenAI(api_key=api_key, base_url=config.llm_base_url)
    response = client.chat.completions.create(
        model=config.llm_model,
        messages=[
            {
                "role": "system",
                "content": "你是个人知识库助手。只能依据给定资料回答；如果资料不足，直接说明不足。回答必须包含引用编号。",
            },
            {"role": "user", "content": f"资料：\n{source_text}\n\n问题：{question}"},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def summarize_with_deepseek(config: AppConfig, title: str, text: str) -> str | None:
    # 摘要流程同样复用项目本地 .env 中的 DeepSeek 密钥。
    load_dotenv(config.root / ".env")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None

    client = OpenAI(api_key=api_key, base_url=config.llm_base_url)
    response = client.chat.completions.create(
        model=config.llm_model,
        messages=[
            {"role": "system", "content": "你是资料整理助手。用中文输出简洁摘要、关键点和待办事项。"},
            {"role": "user", "content": f"标题：{title}\n\n正文：\n{text[:12000]}"},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def format_source(metadata: dict) -> str:
    source_type = metadata.get("source_type", "")
    source = metadata.get("source_url") or metadata.get("source_id", "")
    page = metadata.get("page")
    if page:
        return f"{source}#page={page}"
    start_line = metadata.get("start_line")
    end_line = metadata.get("end_line")
    if start_line and end_line and source_type in {"md", "mdx", "txt"}:
        if start_line == end_line:
            return f"{source}:{start_line}"
        return f"{source}:{start_line}-{end_line}"
    if source_type == "web":
        start_char = metadata.get("start_char")
        end_char = metadata.get("end_char")
        if start_char is not None and end_char is not None:
            return f"{source}#char={start_char}-{end_char}"
    return str(source)
