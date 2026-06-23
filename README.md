# AI短视频生成 Agent

这是选题 10 的可演示版本：用户输入主题、受众、风格和时长，Agent 自动生成 1 分钟短视频方案，并导出脚本、分镜、配音、字幕和 MP4。

## 功能

- 生成视频标题和 1 分钟脚本
- 自动拆分 15-20 个分镜
- 支持 OpenAI 兼容 API 调用大模型生成脚本
- 支持本地 RAG 知识库检索增强生成
- 生成配音文案和 SRT 字幕
- 使用 Windows SAPI 生成 WAV 配音
- 使用 Pillow/OpenCV 生成竖屏场景图和 MP4
- 有可视化 Streamlit 页面
- 提供 MCP Server 工具
- 提供 Claude Code Skill 说明
- 使用 LangGraph 编排 Agent 工作流
- 借鉴 MoneyPrinterTurbo 的短视频流水线，增加视频素材优先、字幕烧录、统一重编码和本地素材兜底

## 安装依赖

```powershell
cd E:\光庭实训\short-video-agent
pip install -r requirements.txt
```

如果暂时不能安装 `imageio-ffmpeg`，程序仍会导出静音 MP4 和单独的 WAV 配音；安装后会自动把配音合进 MP4。

## 启动界面

```powershell
streamlit run app.py
```

界面包含四个页面：

- 一句话生成：只填写一句话主题，系统固定生成 60 秒、15 分镜，其余内容全部由 LLM 生成
- 模型配置：配置文本大模型、Embedding/RAG、TTS 语音、视频生成预留、本地合成工具
- 知识库：上传 TXT/MD 并测试 RAG 检索
- 预览导出：查看脚本、分镜、RAG 来源，并导出 MP4

## 命令行生成

```powershell
python generate_video.py --title "我的短视频标题" --topic "你的真实视频主题" --prompt "你的自定义生成提示词" --audience "大学生" --style "科技感" --duration 60 --scenes 16
```

调用硅基流动 / OpenAI 兼容模型：

```powershell
$env:OPENAI_API_KEY="你的 API Key"
$env:OPENAI_BASE_URL="https://api.siliconflow.cn/v1"
$env:OPENAI_MODEL="Qwen/Qwen3-8B"
python generate_video.py --title "AI学习助手来了" --topic "AI如何帮助大学生完成课程学习" --prompt "突出校园场景，语言口语化，结尾给行动建议" --use-llm
```

## 模型类型说明

这个项目建议配置多类模型：

| 模型类型 | 是否当前接入 | 用途 |
|---|---|---|
| 文本大模型 | 已接入硅基流动/OpenAI 兼容 Chat Completions | 生成标题、脚本、分镜、字幕文案 |
| Embedding 模型 | 已支持硅基流动 Embeddings，失败降级 TF-IDF | RAG 知识库语义检索增强 |
| TTS 语音模型 | 已预留硅基流动 Speech API，当前 Windows SAPI 回退 | 生成配音音频 |
| 视频生成模型 | 已预留硅基流动 Video Submit/Status 配置 | 按分镜生成视频素材片段，不替代最终合成 |
| 本地合成工具 | 已接入 OpenCV + imageio-ffmpeg | 合成字幕、配音、画面并导出 MP4 |

## 硅基流动配置建议

在网页的“模型配置”页先填写“硅基流动统一配置”：

```text
Provider: SiliconFlow
Base URL: https://api.siliconflow.cn/v1
API Key: 你的硅基流动 Key
```

点击“同步到所有 API 模型”后，再分别确认：

- 文本大模型 endpoint：`/chat/completions`
- Embedding endpoint：`/embeddings`
- TTS endpoint：`/audio/speech`
- 视频生成 endpoint：`/video/submit`
- 视频状态 endpoint：`/video/status`

RAG 上传资料时，如果 Embedding 模型已启用并配置了 Key，会写入真实向量；如果接口失败，会自动降级为本地 TF-IDF 检索。

## RAG 向量检索

当前知识库文件保存在：

```text
knowledge/vector_store.json
```

启用硅基流动向量检索：

1. 打开网页 `http://localhost:8501`
2. 进入“模型配置”
3. 在“硅基流动统一配置”中填写 API Key 并同步
4. 进入 `Embedding/RAG`
5. 勾选启用
6. 确认配置：

```text
Base URL: https://api.siliconflow.cn/v1
Endpoint: /embeddings
Model: Qwen/Qwen3-Embedding-8B
Encoding Format: float
Batch Size: 16
```

旧资料可在“知识库”页点击“使用 Embedding API 重建向量索引”。Claude Code 接入后也可以通过 MCP 工具 `rebuild_knowledge_embeddings` 重建向量。

输出文件在 `outputs/` 下，包括：

- `plan.json`
- `video_plan.md`
- `subtitles.srt`
- `voiceover.wav`
- `silent_video.mp4`
- `final_video.mp4`
- `scenes/`
- `generated_clips/`

## 素材与合成策略

当前主流程：

```text
一句话主题
-> LLM 生成标题、15 个分镜、配音文案、image_prompt、video_prompt
-> 生图模型生成 I2V 参考图
-> 视频模型基于参考图生成视频片段
-> TTS 生成配音
-> UTF-8 ASS 字幕烧录
-> 本地合成 MP4
```

当前合成优先级：

```text
视频生成模型生成的分镜片段
-> assets/videos 中的本地素材
-> Pillow 生成的兜底视觉背景
```

最终合成会统一：

- 竖屏 9:16
- H.264 重编码
- 烧录 UTF-8 BOM ASS 字幕，适配中文环境
- 混入配音
- 导出 `final_video.mp4`

如果想提升画面效果，可以把校园、学习、AI、电脑、课堂、图书馆等素材视频放进：

```text
assets/videos/
```

## MCP 注册示例

```powershell
claude mcp add short-video-agent -s user -- python E:\光庭实训\short-video-agent\mcp_server.py
```

重新启动 Claude Code 后输入：

```text
/mcp
```

应该能看到 `short-video-agent` 已连接。

## MCP 工具

- `generate_video_plan`：生成 JSON 视频方案
- `generate_video_report`：生成 Markdown 策划报告
- `export_subtitles`：导出 SRT 字幕
- `create_short_video`：一键生成完整短视频文件
- `add_knowledge_text`：向 RAG 知识库写入文本
- `search_knowledge`：检索 RAG 知识库

## 技术点对应

| 技术点 | 实现位置 |
|---|---|
| RAG 检索增强生成 | `modules/vector_store.py` + `knowledge/short_video_basics.md` |
| Prompt 工程 | `modules/script_generator.py` 的模型提示词 |
| 工具调用 Tool Use | `mcp_server.py` 暴露 6 个 MCP 工具 |
| 多步骤 Agent 工作流 | `modules/pipeline.py` 串联脚本、RAG、配音、字幕、画面、视频 |
| 多模态 UI | `app.py` Streamlit 页面，支持文本、文件、视频预览 |
| 标准化协议 MCP | `mcp_server.py` |
| Skill | `skills/short-video-agent/SKILL.md` |

LangGraph 编排层：

```text
modules/agent_graph.py
```

节点流程：

```text
retrieve_context
-> generate_script_plan
-> prepare_output_dir
-> write_artifacts
-> finalize
```
