# AI 短视频生成 Agent

这是一个面向中文短视频创作流程的 Agent 原型项目。用户输入一个主题后，系统会生成短视频策划方案、分镜、配音文案、字幕文件，并通过图像生成模型、视频生成模型、TTS 与本地合成工具导出竖屏 MP4。

项目重点不是提供一个成品级剪辑软件，而是展示一个可部署、可扩展的短视频生成 Agent 工作流：LLM 负责策划，RAG 提供知识增强，多模态模型生成素材，本地渲染工具完成字幕、配音和视频合成。

## 功能概览

- 一句话生成短视频主题策划
- 使用大模型生成标题、脚本、分镜、字幕、图像提示词和视频提示词
- 支持本地 RAG 知识库检索，默认带 TF-IDF 兜底
- 支持 OpenAI 兼容接口的文本模型、Embedding 模型、图像生成模型、TTS 模型和视频生成模型
- 使用 LangGraph 编排 Agent 节点流程
- 使用 Streamlit 提供可视化 Web 页面
- 使用 FastMCP 暴露 MCP 工具，便于接入 Claude Code 等 Agent 客户端
- 使用 OpenCV、Pillow 和 ffmpeg/imageio-ffmpeg 进行本地合成
- 导出 `plan.json`、`video_plan.md`、`subtitles.srt`、`subtitles.ass`、`voiceover.wav`、`final_video.mp4`

## 工作流

```text
用户主题
  -> RAG 检索知识库上下文
  -> LLM 生成脚本、分镜、配音文案、image_prompt、video_prompt
  -> 图像生成模型生成每个分镜的参考图
  -> 视频生成模型按分镜生成视频片段
  -> TTS 生成配音
  -> 本地工具烧录字幕、混入音频、导出 MP4
```

当前主流程要求画面素材来自模型返回内容：

- 分镜参考图必须由图像生成模型返回。
- 视频片段只使用视频生成模型返回的结果。
- 如果视频模型没有返回某个分镜片段，系统会基于模型生成的参考图合成该分镜。
- 不再从本地 `assets/` 目录查找视频背景素材作为后半段兜底。
- 如果图像生成模型调用失败，流程会直接报错，避免生成“看似完成但实际使用本地素材”的视频。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| Web UI | Streamlit |
| Agent 编排 | LangGraph |
| MCP 服务 | FastMCP |
| 文本模型 | OpenAI 兼容 Chat Completions |
| RAG | 本地 VectorStore，支持 Embedding API 和 TF-IDF |
| 图像生成 | OpenAI 兼容图片生成接口 |
| 视频生成 | OpenAI/SiliconFlow 风格视频任务接口 |
| TTS | OpenAI 兼容 Speech API，失败时可降级到 Windows SAPI |
| 视频合成 | Pillow、OpenCV、ffmpeg、imageio-ffmpeg |

## 目录结构

```text
short-video-agent/
├── app.py                      # Streamlit Web 页面
├── generate_video.py           # 命令行生成入口
├── mcp_server.py               # MCP Server 工具入口
├── requirements.txt            # Python 依赖
├── modules/
│   ├── agent_graph.py          # LangGraph 主工作流
│   ├── pipeline.py             # 对外统一调用入口
│   ├── script_generator.py     # 脚本和分镜生成
│   ├── llm_client.py           # 文本模型调用
│   ├── image_generation.py     # 生图模型调用
│   ├── video_generation.py     # 视频模型调用
│   ├── tts_client.py           # TTS API 调用
│   ├── voice_generator.py      # Windows SAPI 兜底配音
│   ├── subtitle_generator.py   # SRT/ASS 字幕生成
│   ├── video_editor.py         # 视频拼接、字幕烧录、音频混流
│   ├── vector_store.py         # 本地 RAG 知识库
│   └── config_store.py         # 模型配置保存与读取
├── knowledge/
│   ├── short_video_basics.md   # 默认知识库资料
│   └── vector_store.json       # 本地知识库索引
└── skills/                     # Claude Code Skill 示例
```

## 环境要求

- Python 3.10 或更高版本
- Windows 推荐，因为本项目包含 Windows SAPI 配音兜底
- 已安装 ffmpeg，或安装 `imageio-ffmpeg` 后使用其内置 ffmpeg
- 可访问 OpenAI 兼容模型服务

如果只运行页面和配置功能，不需要立即配置模型 Key。  
如果要完整生成视频，必须配置有效的图像生成模型 Key；否则主流程会在生图阶段停止。

## 安装

```powershell
git clone https://github.com/huayibai1/Short-video-agent.git
cd Short-video-agent
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

如果你使用 Conda，也可以直接在已有环境中安装依赖：

```powershell
pip install -r requirements.txt
```

## 启动 Web 页面

```powershell
streamlit run app.py
```

默认访问：

```text
http://localhost:8501
```

页面包含四个主要区域：

- 一句话生成：输入主题，生成短视频方案
- 模型配置：配置文本模型、Embedding、图像生成、TTS、视频生成和本地合成工具
- 知识库：上传 TXT/MD 文档并测试 RAG 检索
- 预览导出：查看脚本、分镜、字幕、RAG 来源并导出视频

## 模型配置

打开 Web 页面后，进入“模型配置”页。可以先填写统一供应商配置，再同步到各模型模块。

以 SiliconFlow/OpenAI 兼容服务为例：

```text
Provider: SiliconFlow
Base URL: https://api.siliconflow.cn/v1
API Key: 你的 API Key
```

建议分别确认以下配置：

| 模块 | Endpoint 示例 | 作用 |
| --- | --- | --- |
| 文本大模型 | `/chat/completions` | 生成标题、脚本、分镜和提示词 |
| Embedding/RAG | `/embeddings` | 知识库语义检索 |
| 图像生成 | `/images/generations` | 为每个分镜生成参考图 |
| TTS | `/audio/speech` | 生成配音 |
| 视频生成 | `/video/submit`、`/video/status` | 生成分镜视频片段 |

模型配置会保存到本地 SQLite 数据库：

```text
config/model_config.db
```

该文件已被 `.gitignore` 排除，不会提交到 GitHub。

## 命令行生成

```powershell
python generate_video.py `
  --topic "AI 如何帮助大学生高效学习" `
  --title "AI 学习助手来了" `
  --prompt "突出校园场景，语言口语化，结尾给行动建议" `
  --audience "大学生" `
  --style "真实竖屏短视频" `
  --duration 60 `
  --scenes 15 `
  --use-llm
```

如果没有配置有效的图像生成 API，命令会在生图阶段失败。这是预期行为，因为当前版本禁止使用本地图片或本地视频素材兜底。

## MCP Server

启动 MCP Server：

```powershell
python mcp_server.py
```

Claude Code 注册示例：

```powershell
claude mcp add short-video-agent -s user -- python E:\path\to\Short-video-agent\mcp_server.py
```

主要工具：

- `get_agent_config_status`：查看模型配置状态
- `generate_short_video_plan`：根据一句话主题生成短视频方案
- `create_short_video_from_topic`：根据一句话主题生成完整短视频文件
- `generate_video_plan`：自定义参数生成 JSON 方案
- `generate_video_report`：生成 Markdown 策划报告
- `export_subtitles`：导出 SRT 字幕
- `add_knowledge_text`：写入 RAG 文本
- `add_knowledge_file`：写入 RAG 文件
- `search_knowledge`：检索知识库
- `rebuild_knowledge_embeddings`：重建 Embedding 索引

## 输出文件

每次生成会在 `outputs/` 下创建一个项目目录：

```text
outputs/YYYYMMDD_HHMMSS_主题/
├── plan.json
├── video_plan.md
├── subtitles.srt
├── subtitles.ass
├── voiceover.wav
├── silent_video.mp4
├── final_video.mp4
├── image/
└── generated_clips/
```

`outputs/` 已被 `.gitignore` 排除，不会提交到仓库。

## RAG 知识库

默认知识库文件：

```text
knowledge/short_video_basics.md
```

索引文件：

```text
knowledge/vector_store.json
```

未配置 Embedding API 时，系统会使用本地 TF-IDF 检索。配置 Embedding API 后，可以在 Web 页面或 MCP 工具中重建语义向量索引。

## 常见问题

### 1. 生成时报 `Image generation failed`

当前版本要求图像素材必须由模型生成。如果图像生成模型没有启用、API Key 无效、余额不足或接口不兼容，流程会停止。

请检查：

- 图像生成模型是否启用
- API Key 是否有效
- Base URL 和 Endpoint 是否正确
- 模型名称是否可用

### 2. 为什么不再使用本地素材兜底？

为了保证生成结果可追溯，当前版本要求视频画面素材来自模型返回内容。这样可以避免后半段使用本地素材导致演示结果和提示词不一致。

### 3. 没有视频生成模型还能运行吗？

可以，但仍然需要图像生成模型。视频生成模型关闭或部分分镜失败时，系统会使用模型生成的参考图完成分镜合成。

### 4. TTS 失败会怎样？

TTS API 失败时，系统会尝试使用 Windows SAPI 生成配音。如果本机没有可用中文语音，会生成静音 WAV 作为兜底。

### 5. 可以直接部署到服务器吗？

可以。核心步骤是安装依赖、配置模型 API、启动 Streamlit。Linux 服务器上 Windows SAPI 不可用，建议配置 TTS API。

## 部署建议

最小部署方式：

```powershell
pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

生产或公网部署时建议：

- 使用环境变量或服务器密钥管理保存 API Key
- 不提交 `config/model_config.db`
- 为 `outputs/` 设置定期清理策略
- 为视频生成接口增加超时、重试和任务队列
- 将 ffmpeg 安装为系统命令

## 许可证

本项目使用 MIT License。详见 [LICENSE](LICENSE)。
