from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .script_generator import generate_plan, generate_plan_with_llm, plan_to_markdown
from .subtitle_generator import write_srt
from .video_editor import build_silent_video, mux_audio
from .visual_generator import render_all_scene_images
from .voice_generator import synthesize_voice
from .vector_store import VectorStore
from .config_store import embedding_model_config, load_config


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text, flags=re.UNICODE).strip("-")
    return cleaned[:32] or "short-video"


def create_project(
    topic: str,
    title: str = "",
    custom_prompt: str = "",
    audience: str = "大学生",
    style: str = "科技感",
    duration_seconds: int = 60,
    scene_count: int | None = None,
    output_root: str | Path = "outputs",
    use_llm: bool = False,
    use_rag: bool = True,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: int = 180,
    embedding_config: dict[str, Any] | None = None,
    use_langgraph: bool = True,
) -> dict[str, Any]:
    if use_langgraph:
        from .agent_graph import run_short_video_agent

        return run_short_video_agent(
            {
                "topic": topic,
                "title": title,
                "custom_prompt": custom_prompt,
                "audience": audience,
                "style": style,
                "duration_seconds": duration_seconds,
                "scene_count": scene_count or 15,
                "output_root": str(output_root),
                "use_llm": use_llm,
                "use_rag": use_rag,
                "api_key": api_key,
                "base_url": base_url,
                "model": model,
                "timeout": timeout,
                "embedding_config": embedding_config,
            }
        )

    rag_context = ""
    rag_sources: list[dict[str, Any]] = []
    if use_rag:
        embedding_config = embedding_config if embedding_config is not None else embedding_model_config(load_config())
        store = VectorStore()
        if not store.documents and Path("knowledge/short_video_basics.md").exists():
            store.add_file("knowledge/short_video_basics.md", embedding_config)
        rag_context, rag_sources = store.context_for(
            f"{topic} {title} {custom_prompt} {audience} {style}",
            top_k=4,
            embedding_config=embedding_config,
        )

    if use_llm:
        plan = generate_plan_with_llm(
            topic=topic,
            title=title,
            custom_prompt=custom_prompt,
            audience=audience,
            style=style,
            duration_seconds=duration_seconds,
            scene_count=scene_count,
            rag_context=rag_context,
            rag_sources=rag_sources,
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
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
        plan["rag_sources"] = rag_sources
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_dir = Path(output_root) / f"{stamp}_{_slug(topic)}"
    project_dir.mkdir(parents=True, exist_ok=True)

    plan_path = project_dir / "plan.json"
    md_path = project_dir / "video_plan.md"
    srt_path = project_dir / "subtitles.srt"
    audio_path = project_dir / "voiceover.wav"
    silent_video_path = project_dir / "silent_video.mp4"
    final_video_path = project_dir / "final_video.mp4"
    scenes_dir = project_dir / "scenes"

    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(plan_to_markdown(plan), encoding="utf-8")
    write_srt(plan, srt_path)
    images = render_all_scene_images(plan, scenes_dir)
    synthesize_voice(plan["voiceover"], audio_path, plan["duration_seconds"])
    build_silent_video(plan, images, silent_video_path)
    final_video, audio_muxed = mux_audio(silent_video_path, audio_path, final_video_path)

    return {
        "project_dir": str(project_dir.resolve()),
        "plan": plan,
        "files": {
            "plan_json": str(plan_path.resolve()),
            "markdown": str(md_path.resolve()),
            "subtitles": str(srt_path.resolve()),
            "voiceover": str(audio_path.resolve()),
            "silent_video": str(silent_video_path.resolve()),
            "final_video": str(final_video.resolve()),
            "scene_images_dir": str(scenes_dir.resolve()),
        },
        "audio_muxed": audio_muxed,
        "generation_mode": plan.get("generation_mode", "unknown"),
        "rag_hit_count": len(rag_sources),
    }


def generate_preview_plan(
    topic: str,
    title: str = "",
    custom_prompt: str = "",
    audience: str = "大学生",
    style: str = "科技感",
    duration_seconds: int = 60,
    scene_count: int | None = None,
    use_llm: bool = False,
    use_rag: bool = True,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: int = 180,
    embedding_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rag_context = ""
    rag_sources: list[dict[str, Any]] = []
    if use_rag:
        embedding_config = embedding_config if embedding_config is not None else embedding_model_config(load_config())
        store = VectorStore()
        if not store.documents and Path("knowledge/short_video_basics.md").exists():
            store.add_file("knowledge/short_video_basics.md", embedding_config)
        rag_context, rag_sources = store.context_for(
            f"{topic} {title} {custom_prompt} {audience} {style}",
            top_k=4,
            embedding_config=embedding_config,
        )
    if use_llm:
        return generate_plan_with_llm(
            topic=topic,
            title=title,
            custom_prompt=custom_prompt,
            audience=audience,
            style=style,
            duration_seconds=duration_seconds,
            scene_count=scene_count,
            rag_context=rag_context,
            rag_sources=rag_sources,
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
        )
    plan = generate_plan(
        topic=topic,
        title=title,
        custom_prompt=custom_prompt,
        audience=audience,
        style=style,
        duration_seconds=duration_seconds,
        scene_count=scene_count,
    )
    plan["rag_sources"] = rag_sources
    return plan
