# Personal Knowledge Agent

Personal Knowledge Agent 是一个 Python 本地优先个人知识库 Agent。它使用 LangGraph 组织导入、问答和摘要流程，支持导入 Markdown、TXT、PDF 和网页，使用本地 `sentence-transformers/all-MiniLM-L6-v2` 生成 embedding，使用 Chroma 做本地持久化向量数据库，默认通过 DeepSeek 生成带引用回答。

## 项目特性

- 本地优先：文档索引和向量库默认保存在本地 `.pka/` 目录。
- 可追溯回答：回答会附带 Markdown 行号、PDF 页码或网页 URL 引用。
- LangGraph 工作流：`ingest`、`ask`、`summarize` 三条流程都由显式 graph 节点组织。
- DeepSeek 默认模型：DeepSeek API 兼容 OpenAI SDK，默认 `base_url=https://api.deepseek.com`，模型默认 `deepseek-v4-flash`。
- 轻量 embedding：默认使用 `sentence-transformers/all-MiniLM-L6-v2`，适合本地小型知识库和示例数据。
- 本地向量库：使用 Chroma 持久化索引，不依赖远程向量数据库。
- 增量索引：使用 `.pka/manifest.json` 记录 source hash，未变化文件会跳过，变化文件会先删除旧 chunk 再重建。
- 混合检索：向量召回 + 关键词召回，按简单融合分数排序。

## 快速开始

```bash
git clone https://github.com/damonwangk/personal-knowledge-agent.git
cd personal-knowledge-agent

python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

python scripts/download_sample_data.py
python -m pka init
python -m pka ingest data
python -m pka ask "what is RAG?"
python -m pka summarize data/notes/rag_agent_design.md
```

如果要让模型生成自然语言回答：

```bash
export DEEPSEEK_API_KEY="<your-deepseek-api-key>"
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
