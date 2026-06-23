---
name: short-video-generate
description: 根据一句话主题调用 short-video-agent MCP 完整生成 1 分钟短视频。用于用户要求“一句话生成视频”“生成 MP4”“导出短视频成品”“开始生成视频”时，自动调用已配置 API：LLM 生成分镜，生图模型生成参考图，视频模型生成片段，TTS 生成配音，UTF-8 ASS 字幕烧录，最后导出 MP4。
---

# Short Video Generate

使用这个 Skill 时，优先调用 MCP 服务 `short-video-agent` 的 `create_short_video_from_topic(topic)`。

## 固定工作流

1. 接收用户的一句话主题。
2. 调用 LLM 生成 60 秒、15 分镜方案。
3. 根据每个分镜的 `image_prompt` 生成参考图。
4. 将参考图和 `video_prompt` 交给视频模型生成分镜片段。
5. 使用分镜 `subtitle` 生成 TTS 配音，确保配音和字幕一致。
6. 使用 UTF-8 ASS 字幕烧录并合成 `final_video.mp4`。

## 输出

生成结束后只汇报关键路径：

- `final_video.mp4`
- `plan.json`
- `video_plan.md`
- `subtitles.ass`
- `voiceover.wav`
- `image` 参考图目录
- `generated_clips` 视频片段目录

同时说明 `generation_mode`、`agent_framework`、图像/视频/TTS API 状态。不要输出完整 API Key。

## 失败处理

如果 MCP 返回 API 调用失败，先调用 `get_agent_config_status()` 查看哪些模型未启用或未保存 Key，再把具体失败模型告诉用户。
