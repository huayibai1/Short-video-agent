---
name: short-video-knowledge
description: 管理 short-video-agent 的本地 RAG 知识库并进行检索问答。用于用户要导入知识、重建向量、检索资料、演示 RAG、查询短视频知识库内容时使用。该 Skill 只处理展示和问答，不把 RAG 强制接入默认视频生成流程。
---

# Short Video Knowledge

使用这个 Skill 时，优先调用 MCP 服务 `short-video-agent` 的知识库工具。

## 可用操作

- 用户提供文本资料：调用 `add_knowledge_text(text, source)`。
- 用户提供 TXT/MD 文件路径：调用 `add_knowledge_file(path)`。
- 用户要求检索或问答：调用 `search_knowledge(query, top_k)`。
- 用户更换 Embedding API 或导入大量资料后：调用 `rebuild_knowledge_embeddings()`。
- 用户询问配置状态：调用 `get_agent_config_status()`。

## 约束

RAG 知识库仅用于展示、检索和问答。默认短视频生成流程保持：

```text
一句话主题 -> LLM 分镜 -> 生图参考图 -> 视频模型 -> TTS -> 字幕 -> MP4
```

不要在用户只要求生成视频时主动要求先导入 RAG。

## 输出

返回命中的来源、相关内容摘要和下一步建议。不要输出完整 API Key。
