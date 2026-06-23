---
name: short-video-plan
description: 根据一句话主题调用 short-video-agent MCP 生成短视频策划预览。用于用户想先看 60 秒、15 分镜短视频标题、脚本、字幕、配音文案、image_prompt、video_prompt，而暂时不导出 MP4 的场景。触发语包括“生成短视频方案”“预览分镜”“根据这句话做视频脚本”“先看视频计划”。
---

# Short Video Plan

使用这个 Skill 时，优先调用 MCP 服务 `short-video-agent`。

## 流程

1. 从用户话语中提取一句话主题。
2. 调用 MCP 工具 `generate_short_video_plan(topic)`。
3. 返回标题、摘要、15 个分镜、每个分镜的字幕、图片生成提示词和视频生成提示词。
4. 明确说明这一步只生成预览方案，不生成 MP4，不调用 RAG。

## 输出

用简洁中文汇报：

- 标题
- 生成模式
- 15 个分镜表
- 配音文案摘要

如果 MCP 未连接，提示用户在项目目录 `E:\光庭实训\short-video-agent` 中重启 Claude Code 并检查 `/mcp`。
