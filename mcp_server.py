from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from modules.config_store import (
    DB_PATH,
    embedding_model_config,
    load_config,
    text_model_kwargs,
)
from modules.pipeline import create_project, generate_preview_plan
from modules.script_generator import generate_plan, plan_to_markdown
from modules.subtitle_generator import write_srt
from modules.vector_store import VectorStore


try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover
    FastMCP = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


if FastMCP is None:  # pragma: no cover
    raise RuntimeError("缺少 mcp 依赖。请先安装：pip install mcp") from IMPORT_ERROR


mcp = FastMCP("short-video-agent")

DEFAULT_AUDIENCE = "短视频观众"
DEFAULT_STYLE = "真实竖屏短视频，画面自然，节奏清晰，适合中文平台"
DEFAULT_DURATION_SECONDS = 60
DEFAULT_SCENE_COUNT = 15
ONE_SENTENCE_PROMPT = (
    "你将根据用户的一句话主题，自动生成一个 60 秒中文竖屏短视频方案。"
    "必须生成 15 个分镜，每个分镜都要有 narration、subtitle、image_prompt、video_prompt。"
    "image_prompt 用于生图模型生成 I2V 参考图，必须是中文详细画面描述，真实摄影风格，无文字、无水印、无 logo。"
    "video_prompt 用于视频模型基于参考图生成动态片段，必须描述镜头运动、人物动作和氛围，无字幕、无水印、无乱码文字。"
    "voiceover 要适合 TTS 配音，中文口语化，整体时长约 60 秒。"
)


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _text_kwargs(overrides: dict[str, str] | None = None) -> dict[str, Any]:
    kwargs = text_model_kwargs(load_config())
    overrides = overrides or {}
    for key in ("api_key", "base_url", "model"):
        if overrides.get(key):
            kwargs[key] = overrides[key]
    return kwargs


@mcp.tool()
def get_agent_config_status() -> str:
    """查看短视频 Agent 的模型配置状态，不返回任何完整 API Key。"""
    config = load_config()
    sections = ["text_model", "embedding_model", "image_model", "video_model", "tts_model", "render_engine"]
    status: dict[str, Any] = {
        "config_db": str(DB_PATH.resolve()),
        "workflow": "topic -> LLM plan -> image references -> I2V clips -> TTS -> UTF-8 ASS subtitles -> MP4",
        "defaults": {
            "duration_seconds": DEFAULT_DURATION_SECONDS,
            "scene_count": DEFAULT_SCENE_COUNT,
            "use_llm": True,
            "use_rag_in_main_flow": False,
        },
        "models": {},
    }
    for section in sections:
        item = config.get(section, {})
        api_key = str(item.get("api_key") or "")
        status["models"][section] = {
            "enabled": bool(item.get("enabled")),
            "provider": item.get("provider"),
            "base_url": item.get("base_url"),
            "endpoint": item.get("endpoint") or item.get("status_endpoint") or "",
            "model": item.get("model"),
            "key_saved": bool(api_key),
            "key_preview": f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) >= 12 else "",
        }
    return _json(status)


@mcp.tool()
def generate_short_video_plan(topic: str) -> str:
    """根据一句话主题生成 60 秒、15 分镜短视频方案预览；不生成视频文件，不调用 RAG。"""
    kwargs = _text_kwargs()
    plan = generate_preview_plan(
        topic=topic,
        title="",
        custom_prompt=ONE_SENTENCE_PROMPT,
        audience=DEFAULT_AUDIENCE,
        style=DEFAULT_STYLE,
        duration_seconds=DEFAULT_DURATION_SECONDS,
        scene_count=DEFAULT_SCENE_COUNT,
        use_llm=True,
        use_rag=False,
        api_key=kwargs.get("api_key"),
        base_url=kwargs.get("base_url"),
        model=kwargs.get("model"),
        timeout=int(kwargs.get("timeout", 180) or 180),
        embedding_config=embedding_model_config(load_config()),
    )
    return _json(plan)


@mcp.tool()
def create_short_video_from_topic(topic: str) -> str:
    """根据一句话主题完整生成短视频，输出脚本、参考图、视频片段、配音、字幕和 MP4。"""
    kwargs = _text_kwargs()
    result = create_project(
        topic=topic,
        title="",
        custom_prompt=ONE_SENTENCE_PROMPT,
        audience=DEFAULT_AUDIENCE,
        style=DEFAULT_STYLE,
        duration_seconds=DEFAULT_DURATION_SECONDS,
        scene_count=DEFAULT_SCENE_COUNT,
        use_llm=True,
        use_rag=False,
        api_key=kwargs.get("api_key"),
        base_url=kwargs.get("base_url"),
        model=kwargs.get("model"),
        timeout=int(kwargs.get("timeout", 180) or 180),
        embedding_config=embedding_model_config(load_config()),
    )
    return _json(result)


@mcp.tool()
def generate_video_plan(
    topic: str,
    title: str = "",
    custom_prompt: str = "",
    audience: str = DEFAULT_AUDIENCE,
    style: str = DEFAULT_STYLE,
    duration_seconds: int = DEFAULT_DURATION_SECONDS,
    scene_count: int = DEFAULT_SCENE_COUNT,
    use_llm: bool = True,
    use_rag: bool = False,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> str:
    """生成短视频 JSON 方案。默认走 LLM、60 秒、15 分镜，RAG 默认关闭。"""
    if use_llm:
        kwargs = _text_kwargs({"api_key": api_key, "base_url": base_url, "model": model})
        plan = generate_preview_plan(
            topic=topic,
            title=title,
            custom_prompt=custom_prompt or ONE_SENTENCE_PROMPT,
            audience=audience,
            style=style,
            duration_seconds=duration_seconds,
            scene_count=scene_count,
            use_llm=True,
            use_rag=use_rag,
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url"),
            model=kwargs.get("model"),
            timeout=int(kwargs.get("timeout", 180) or 180),
            embedding_config=embedding_model_config(load_config()),
        )
    else:
        plan = generate_plan(
            topic=topic,
            title=title,
            custom_prompt=custom_prompt,
            audience=audience,
            style=style,
            duration_seconds=duration_seconds,
            scene_count=scene_count,
        )
    return _json(plan)


@mcp.tool()
def generate_video_report(topic: str) -> str:
    """根据一句话主题生成 Markdown 格式短视频策划报告；不生成视频文件。"""
    plan = json.loads(generate_short_video_plan(topic))
    return plan_to_markdown(plan)


@mcp.tool()
def export_subtitles(topic: str, output_path: str) -> str:
    """根据一句话主题导出 SRT 字幕文件。"""
    plan = json.loads(generate_short_video_plan(topic))
    path = write_srt(plan, output_path)
    return str(path.resolve())


@mcp.tool()
def create_short_video(
    topic: str,
    title: str = "",
    custom_prompt: str = "",
    audience: str = DEFAULT_AUDIENCE,
    style: str = DEFAULT_STYLE,
    duration_seconds: int = DEFAULT_DURATION_SECONDS,
    scene_count: int = DEFAULT_SCENE_COUNT,
    use_llm: bool = True,
    use_rag: bool = False,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> str:
    """兼容旧调用方式的一键生成工具；默认与网页的一句话生成流程一致。"""
    kwargs = _text_kwargs({"api_key": api_key, "base_url": base_url, "model": model})
    result = create_project(
        topic=topic,
        title=title,
        custom_prompt=custom_prompt or ONE_SENTENCE_PROMPT,
        audience=audience,
        style=style,
        duration_seconds=duration_seconds,
        scene_count=scene_count,
        use_llm=use_llm,
        use_rag=use_rag,
        api_key=kwargs.get("api_key"),
        base_url=kwargs.get("base_url"),
        model=kwargs.get("model"),
        timeout=int(kwargs.get("timeout", 180) or 180),
        embedding_config=embedding_model_config(load_config()),
    )
    return _json(result)


@mcp.tool()
def add_knowledge_text(text: str, source: str = "manual") -> str:
    """向本地 RAG 知识库写入文本资料，仅用于展示或问答，不参与默认视频生成。"""
    count = VectorStore().add_text(text, source, embedding_model_config(load_config()))
    return f"已写入 {count} 个文本块，来源：{source}"


@mcp.tool()
def add_knowledge_file(path: str) -> str:
    """向本地 RAG 知识库写入 TXT/MD 文件，仅用于展示或问答。"""
    file_path = Path(path)
    count = VectorStore().add_file(file_path, embedding_model_config(load_config()))
    return f"已写入 {count} 个文本块，来源：{file_path.resolve()}"


@mcp.tool()
def search_knowledge(query: str, top_k: int = 4) -> str:
    """检索本地 RAG 知识库，返回相关上下文。"""
    hits = VectorStore().search(query, top_k, embedding_model_config(load_config()))
    return _json(hits)


@mcp.tool()
def rebuild_knowledge_embeddings() -> str:
    """使用当前 Embedding API 配置重建本地 RAG 知识库向量索引。"""
    result = VectorStore().rebuild_embeddings(embedding_model_config(load_config()))
    return _json(result)


if __name__ == "__main__":
    mcp.run()
