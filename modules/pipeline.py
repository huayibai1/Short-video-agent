from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .script_generator import generate_plan, generate_plan_with_llm
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

    raise RuntimeError(
        "The legacy local-render pipeline is disabled. Use the LangGraph workflow so video visuals come from model-generated assets."
    )


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
