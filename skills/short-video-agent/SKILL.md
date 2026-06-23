---
name: short-video-agent
description: 根据用户输入的视频主题、受众、风格和时长，生成 1 分钟短视频标题、脚本、15-20 个分镜、配音文案、字幕，并调用本地工具导出 MP4。
---

# AI短视频生成 Agent

当用户要求生成短视频、短视频脚本、分镜、配音、字幕或 1 分钟 MP4 时，使用本 Skill。

## 输入

- 视频主题，例如“人工智能如何改变大学生活”
- 用户指定标题
- 用户自定义生成提示词
- 目标受众，默认“大学生”
- 视频风格，默认“科技感”
- 视频时长，默认 60 秒
- 分镜数量，默认 16 个，范围 15-20 个

## 工作流

1. 明确主题、受众、风格和时长。
2. 生成视频标题、视频概述和完整配音文案。
3. 如果用户提供资料，先调用 `add_knowledge_text` 写入 RAG 知识库。
4. 调用 `search_knowledge` 检索主题相关上下文。
5. 调用 MCP 工具 `generate_video_plan`，优先启用 `use_llm=true` 和 `use_rag=true`。
6. 将脚本拆分为 15-20 个分镜，每个分镜包含时间、画面描述、字幕和素材关键词。
7. 如用户要求导出成品，调用 `create_short_video` 生成字幕、配音、场景图和 MP4。
8. 返回输出目录和关键文件路径。

## 推荐调用

```powershell
python E:\光庭实训\short-video-agent\generate_video.py --title "用户自己的标题" --topic "用户自己的主题" --prompt "用户自己的生成提示词" --audience "大学生" --style "科技感" --duration 60 --scenes 16 --use-llm
```

## 输出要求

- 优先给出最终 MP4 路径
- 同时给出 Markdown 策划报告和 SRT 字幕路径
- 说明生成模式：`llm`、`template` 或 `template_fallback`
- 说明 RAG 命中数量和主要来源
- 如果音频未能合入 MP4，说明已生成单独的 WAV 配音文件

## 技术点

- RAG：`modules/vector_store.py`
- Prompt 工程：`modules/script_generator.py`
- Tool Use：`mcp_server.py`
- 多步骤工作流：`modules/pipeline.py`
- 多模态 UI：`app.py`
- MCP 标准协议：`mcp_server.py`
