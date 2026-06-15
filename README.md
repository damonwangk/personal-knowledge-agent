# Personal Knowledge Agent

本项目是一个 Python 本地优先个人知识库 Agent。基础版使用 LangGraph 组织导入、问答和摘要流程，支持导入 Markdown、TXT、PDF 和网页，使用本地 `sentence-transformers/all-MiniLM-L6-v2` 生成 embedding，使用 Chroma 做本地持久化向量数据库，默认使用 DeepSeek 生成带引用回答。

## 为什么这样选型

- 你的电脑是 Apple M4、16GB 内存、约 65GB 可用空间，适合小型本地向量库和 80MB 级别 embedding 模型。
- DeepSeek API 兼容 OpenAI SDK，代码里默认 `base_url=https://api.deepseek.com`，模型默认 `deepseek-v4-flash`。
- Chroma 官方支持 Python 本地运行和持久化；对个人知识库比远程向量数据库更合适。
- MiniLM 输出 384 维向量，体积小，CPU 可跑，适合本机小数据量样例。
- LangGraph 用来表达 workflow 节点，基础版保持三条图：`ingest`、`ask`、`summarize`。
- 增量索引用 `.pka/manifest.json` 记录 source hash，未变化文件会跳过，变化文件会先删除旧 chunk 再重建。
- 检索使用 hybrid 策略：向量召回 + 关键词召回，按简单融合分数排序。

## 快速开始

```bash
cd /Users/x-1w/Project_codex/personal-knowledge-agent
/opt/miniconda3/envs/test1-rag/bin/python -m pip install -e .

/opt/miniconda3/envs/test1-rag/bin/python scripts/download_sample_data.py
/opt/miniconda3/envs/test1-rag/bin/python -m pka init
/opt/miniconda3/envs/test1-rag/bin/python -m pka ingest data
/opt/miniconda3/envs/test1-rag/bin/python -m pka ask "这些资料里如何描述检索增强生成？"
/opt/miniconda3/envs/test1-rag/bin/python -m pka summarize data/notes/rag_agent_design.md
```

如果要让模型生成自然语言回答：

```bash
export DEEPSEEK_API_KEY="你的 key"
pka ask "这些资料里有哪些 agent 设计原则？"
```

没有 `DEEPSEEK_API_KEY` 时，`ask` 会退化为检索式回答，方便离线验证基础功能。

## 数据位置

样例数据放在：

```text
data/
  raw/       # PDF/TXT
  web/       # 网页正文快照
  notes/     # Markdown 笔记
```

索引数据默认放在 `.pka/`，不提交到 Git。

## LangGraph 流程

基础版在 `src/pka/graphs.py` 里定义三条图：

- `ingest`：加载资料 -> 切块 -> embedding -> 写入 Chroma。
- `ask`：问题 embedding -> Chroma 检索 -> DeepSeek 生成回答或离线返回片段。
- `summarize`：加载资料 -> DeepSeek 摘要或离线预览。

## 引用格式

- Markdown/TXT：`path:start_line-end_line`
- PDF：`path#page=N`
- 网页：优先使用 canonical URL，格式为 `url#char=start-end`
