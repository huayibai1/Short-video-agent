# Claude Code 接入说明

## MCP

本项目已提供项目级 MCP 配置：

```text
E:\光庭实训\short-video-agent\.mcp.json
```

在 Claude Code 中打开 `E:\光庭实训\short-video-agent` 目录后，重启 Claude Code，输入：

```text
/mcp
```

在 `/mcp` 中需要启用的是 MCP 服务器 `short-video-agent`。`short-video-generate` 是 Claude Skill 名称，不是 MCP 服务器名。

如果项目级 `.mcp.json` 没有自动启用，可以手动注册：

```powershell
claude mcp add short-video-agent -s user -- E:\Anaconda\python.exe E:\光庭实训\short-video-agent\mcp_server.py
```

## Skills

已安装到：

```text
C:\Users\吣厸\.claude\skills\short-video-plan
C:\Users\吣厸\.claude\skills\short-video-generate
C:\Users\吣厸\.claude\skills\short-video-knowledge
```

对应能力：

- `short-video-plan`：一句话生成 60 秒、15 分镜方案预览。
- `short-video-generate`：一句话完整生成 MP4、参考图、分镜视频片段、配音和字幕。
- `short-video-knowledge`：管理和检索本地 RAG 知识库，仅作展示和问答，不参与默认视频生成流程。

模型 API 配置继续读取项目 SQLite：

```text
E:\光庭实训\short-video-agent\config\model_config.db
```

Claude 通过 MCP 调用时不需要重新输入 API Key。
