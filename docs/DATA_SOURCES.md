# 样例数据来源

本项目样例数据用于本地 RAG 功能测试，刻意控制在小型本地知识库可处理的范围内。PDF 文件如果用普通文本编辑器打开会显示二进制内容，这是 PDF 格式本身的压缩流；请用 PDF 阅读器打开。项目读取 PDF 时会优先使用 `pypdf` 抽取文本，抽取文本不足时会通过 Tesseract OCR 兜底识别。

## PDF 论文

| 文件 | 来源 | 说明 |
|---|---|---|
| `data/raw/rag_paper_arxiv_2005_11401.pdf` | https://arxiv.org/pdf/2005.11401 | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks，用于测试 RAG 论文检索和 PDF 页码引用。 |
| `data/raw/attention_is_all_you_need_arxiv_1706_03762.pdf` | https://arxiv.org/pdf/1706.03762 | Attention Is All You Need，用于测试 Transformer 相关论文检索。 |
| `data/raw/bert_arxiv_1810_04805.pdf` | https://arxiv.org/pdf/1810.04805 | BERT: Pre-training of Deep Bidirectional Transformers，用于测试 NLP 论文检索。 |
| `data/raw/gpt3_arxiv_2005_14165.pdf` | https://arxiv.org/pdf/2005.14165 | Language Models are Few-Shot Learners，用于测试长 PDF 和大模型相关检索。 |

PDF 文本抽取预览：

```text
docs/pdf_previews/
```

## TXT

| 文件 | 来源 | 说明 |
|---|---|---|
| `data/raw/alice_project_gutenberg.txt` | https://www.gutenberg.org/cache/epub/11/pg11.txt | Project Gutenberg 公版文本，用于测试长 TXT 切块。 |

## HTML 网页

| 文件 | 来源 | 说明 |
|---|---|---|
| `data/web/deepseek_api_docs.html` | https://api-docs.deepseek.com/ | DeepSeek 官方文档快照，用于测试模型配置相关网页检索。 |
| `data/web/wikipedia_artificial_intelligence.html` | https://en.wikipedia.org/wiki/Artificial_intelligence | 公开百科页面，用于测试 AI 主题网页检索。 |
| `data/web/wikipedia_go_game.html` | https://en.wikipedia.org/wiki/Go_(game) | 公开百科页面，用于测试围棋主题网页检索。 |
| `data/web/wikipedia_minecraft.html` | https://en.wikipedia.org/wiki/Minecraft | 公开百科页面，用于测试游戏主题网页检索。 |

说明：曾尝试直接抓取百度百科页面，但返回 403；由于当前数据只用于测试，已跳过百度百科，改用公开可下载网页。

## Markdown 游戏知识

| 文件 | 说明 |
|---|---|
| `data/notes/open_world_game_design.md` | 开放世界游戏设计知识。 |
| `data/notes/roguelike_game_design.md` | Roguelike 游戏设计知识。 |
| `data/notes/go_strategy.md` | 围棋入门知识。 |
| `data/notes/minecraft_survival.md` | Minecraft 生存模式知识。 |
| `data/notes/rag_agent_design.md` | 项目自身 RAG/Agent 设计笔记。 |

## Hugging Face 小样本

这些文件由 `scripts/download_hf_sample_data.py` 通过 Hugging Face Dataset Viewer API 拉取少量 rows 后转成 Markdown。只保存少量样本，不下载完整数据集。

| 文件 | 数据集 | 说明 |
|---|---|---|
| `data/hf/huggingfacefw_fineweb_edu.md` | `HuggingFaceFW/fineweb-edu` | 教育网页文本样本，用于测试较长网页正文检索。 |
| `data/hf/sentence_transformers_natural_questions.md` | `sentence-transformers/natural-questions` | 问答样本，用于测试自然语言问题和答案片段检索。 |
| `data/hf/mongodb_embedded_movies.md` | `MongoDB/embedded_movies` | 电影结构化条目转 Markdown，用于测试标题、字段和正文混合检索。 |
