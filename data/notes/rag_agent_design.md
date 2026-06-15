# Personal Knowledge Agent 设计笔记

## 项目定位

Personal Knowledge Agent 是一个本地优先的个人知识库工具。它的目标不是替代通用聊天机器人，而是帮助用户在自己的资料中检索、摘要和追溯来源。

## 基础版能力

- 导入 Markdown、TXT、PDF 和网页快照。
- 使用本地 embedding 模型生成向量，避免把原文发送到云端。
- 使用 Chroma 在本地保存向量索引。
- 使用 DeepSeek 根据检索片段生成中文回答。
- 当没有 API key 时，返回检索片段，保证功能可离线验证。

## LangGraph 工作流

基础版使用三条 LangGraph 状态图：

1. ingest 图：加载资料、切块、生成 embedding、写入向量库。
2. ask 图：生成问题向量、检索相关片段、调用模型生成答案。
3. summarize 图：加载资料、拼接正文、调用模型生成摘要。

这种结构方便最终版继续增加路由节点、重排序节点、人工确认节点和工具调用节点。

## 引用原则

回答应该尽量附带来源。Markdown 和 TXT 使用文件路径，PDF 使用文件路径加页码，网页使用 URL 或本地 HTML 快照路径。

## 后续增强

- 增量索引，避免重复处理未变化文件。
- 混合检索，结合关键词检索和向量检索。
- related 命令，发现与当前笔记相关的资料。
- todos 命令，从会议记录或研究笔记里提取行动项。
- Web UI，展示来源片段和问答历史。

## 已实现的索引与检索增强

增量索引使用 `.pka/manifest.json` 记录每个 source 的 hash 和 chunk ids。导入时先计算文件或 URL 的 hash，如果 hash 未变化，就跳过该来源；如果 hash 变化，就删除该来源旧 chunk，再重新切块、生成 embedding、写入 Chroma。

混合检索由向量检索和关键词检索组成。向量检索负责语义相似召回，关键词检索负责精确术语匹配，例如 API key、base_url、LangGraph、Chroma 等词。两个结果列表会按 rank fusion 合并，得到最终上下文。

引用增强在切块时写入元数据。Markdown 和 TXT 保存起止行号，PDF 保存页码，网页优先保存 canonical URL，并附带字符范围，方便用户回到原始资料。
