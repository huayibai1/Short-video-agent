from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .config_store import PROJECT_ROOT, embedding_model_config, image_model_config, load_config
from .image_generation import ImageGenerationError, generate_image
from .pipeline import _slug
from .script_generator import generate_plan, generate_plan_with_llm, plan_to_markdown
from .subtitle_generator import write_ass, write_srt
from .tts_client import TTSError, synthesize_siliconflow_speech
from .vector_store import VectorStore
from .video_editor import build_video_from_mixed_assets, mux_audio
from .video_generation import VideoGenerationError, generate_scene_video
from .voice_generator import synthesize_voice


class ShortVideoState(TypedDict, total=False):
    topic: str
    title: str
    custom_prompt: str
    audience: str
    style: str
    duration_seconds: int
    scene_count: int
    output_root: str
    use_llm: bool
    use_rag: bool
    api_key: str | None
    base_url: str | None
    model: str | None
    timeout: int
    embedding_config: dict[str, Any] | None
    rag_context: str
    rag_sources: list[dict[str, Any]]
    plan: dict[str, Any]
    project_dir: str
    files: dict[str, str]
    audio_muxed: bool
    generation_mode: str
    rag_hit_count: int
    graph_steps: list[str]
    api_status: dict[str, Any]


def _step(state: ShortVideoState, name: str) -> None:
    state.setdefault("graph_steps", []).append(name)


def retrieve_context(state: ShortVideoState) -> ShortVideoState:
    _step(state, "retrieve_context")
    state["rag_context"] = ""
    state["rag_sources"] = []
    if not state.get("use_rag"):
        return state

    config = state.get("embedding_config") or embedding_model_config(load_config())
    store = VectorStore()
    default_doc = PROJECT_ROOT / "knowledge" / "short_video_basics.md"
    if not store.documents and default_doc.exists():
        store.add_file(default_doc, config)
    query = " ".join(
        [
            state.get("topic", ""),
            state.get("title", ""),
            state.get("custom_prompt", ""),
            state.get("audience", ""),
            state.get("style", ""),
        ]
    )
    context, sources = store.context_for(query, top_k=4, embedding_config=config)
    state["rag_context"] = context
    state["rag_sources"] = sources
    return state


def generate_script_plan(state: ShortVideoState) -> ShortVideoState:
    _step(state, "generate_script_plan")
    if state.get("use_llm"):
        plan = generate_plan_with_llm(
            topic=state.get("topic", ""),
            title=state.get("title", ""),
            custom_prompt=state.get("custom_prompt", ""),
            audience=state.get("audience", "大学生"),
            style=state.get("style", "科技感"),
            duration_seconds=int(state.get("duration_seconds", 60)),
            scene_count=int(state.get("scene_count", 16)),
            rag_context=state.get("rag_context", ""),
            rag_sources=state.get("rag_sources", []),
            api_key=state.get("api_key"),
            base_url=state.get("base_url"),
            model=state.get("model"),
            timeout=int(state.get("timeout", 180)),
        )
    else:
        plan = generate_plan(
            topic=state.get("topic", ""),
            title=state.get("title", ""),
            custom_prompt=state.get("custom_prompt", ""),
            audience=state.get("audience", "大学生"),
            style=state.get("style", "科技感"),
            duration_seconds=int(state.get("duration_seconds", 60)),
            scene_count=int(state.get("scene_count", 16)),
        )
        plan["rag_sources"] = state.get("rag_sources", [])
    # Keep TTS narration aligned with burned subtitles.
    plan["voiceover"] = "\n".join(
        (scene.get("subtitle") or scene.get("narration") or "").strip()
        for scene in plan.get("scenes", [])
        if (scene.get("subtitle") or scene.get("narration") or "").strip()
    )
    state["plan"] = plan
    return state


def prepare_output_dir(state: ShortVideoState) -> ShortVideoState:
    _step(state, "prepare_output_dir")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = Path(state.get("output_root") or PROJECT_ROOT / "outputs")
    project_dir = output_root / f"{stamp}_{_slug(state.get('topic', 'short-video'))}"
    project_dir.mkdir(parents=True, exist_ok=True)
    state["project_dir"] = str(project_dir.resolve())
    return state


def write_artifacts(state: ShortVideoState) -> ShortVideoState:
    _step(state, "write_artifacts")
    project_dir = Path(state["project_dir"])
    plan = state["plan"]
    plan_path = project_dir / "plan.json"
    md_path = project_dir / "video_plan.md"
    srt_path = project_dir / "subtitles.srt"
    ass_path = project_dir / "subtitles.ass"
    audio_path = project_dir / "voiceover.wav"
    silent_video_path = project_dir / "silent_video.mp4"
    final_video_path = project_dir / "final_video.mp4"
    reference_dir = project_dir / "image"
    clips_dir = project_dir / "generated_clips"

    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(plan_to_markdown(plan), encoding="utf-8")
    write_srt(plan, srt_path)
    write_ass(plan, ass_path)
    config = load_config()
    api_status = {}
    image_config = config.get("image_model", {})
    image_results = []
    if not image_config.get("enabled"):
        raise RuntimeError("Image generation model is disabled; video composition now requires model-generated images.")

    images = []
    for scene in plan["scenes"]:
        out_img = reference_dir / f"scene_{scene['index']:02d}.png"
        try:
            img = generate_image(scene.get("image_prompt") or scene.get("visual", ""), out_img, image_config)
            scene["reference_image"] = str(img.resolve())
            images.append(img)
            image_results.append({"scene": scene["index"], "status": "ok", "path": str(img.resolve())})
        except ImageGenerationError as exc:
            image_results.append({"scene": scene["index"], "status": "failed", "error": str(exc)})
            api_status["image_generation"] = image_results
            raise RuntimeError(f"Image generation failed for scene {scene['index']}; local visual fallback is disabled.") from exc
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    api_status["image_generation"] = image_results
    tts_config = config.get("tts_model", {})
    if tts_config.get("enabled"):
        try:
            synthesize_siliconflow_speech(plan["voiceover"], audio_path, tts_config)
            api_status["tts"] = "api"
        except TTSError as exc:
            api_status["tts"] = f"fallback: {exc}"
            synthesize_voice(plan["voiceover"], audio_path, plan["duration_seconds"])
    else:
        api_status["tts"] = "windows_sapi"
        synthesize_voice(plan["voiceover"], audio_path, plan["duration_seconds"])

    scene_videos: dict[int, Path] = {}
    video_config = config.get("video_model", {})
    if video_config.get("enabled"):
        max_scene_videos = int(video_config.get("max_scene_videos", 1) or 1)
        video_results = []
        for scene, image_path in zip(plan["scenes"][:max_scene_videos], images[:max_scene_videos]):
            try:
                output_clip = clips_dir / f"scene_{scene['index']:02d}.mp4"
                scene["video_prompt_used"] = scene.get("video_prompt") or scene.get("visual", "")
                result = generate_scene_video(scene, plan, image_path, output_clip, video_config)
                scene_videos[int(scene["index"])] = output_clip
                scene["generated_video"] = str(output_clip.resolve())
                scene["video_prompt"] = result["prompt"]
                video_results.append({"scene": scene["index"], "status": "ok", "path": str(output_clip.resolve())})
            except VideoGenerationError as exc:
                video_results.append({"scene": scene["index"], "status": "failed", "error": str(exc)})
                break
        api_status["video_generation"] = video_results
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        api_status["video_generation"] = "disabled"

    build_video_from_mixed_assets(plan, images, scene_videos, silent_video_path)
    final_video, audio_muxed = mux_audio(silent_video_path, audio_path, final_video_path, subtitle_path=ass_path)

    state["files"] = {
        "plan_json": str(plan_path.resolve()),
        "markdown": str(md_path.resolve()),
        "subtitles": str(srt_path.resolve()),
        "subtitles_ass": str(ass_path.resolve()),
        "voiceover": str(audio_path.resolve()),
        "silent_video": str(silent_video_path.resolve()),
        "final_video": str(final_video.resolve()),
            "reference_images_dir": str(reference_dir.resolve()),
            "generated_clips_dir": str(clips_dir.resolve()),
        }
    state["audio_muxed"] = audio_muxed
    state["api_status"] = api_status
    return state


def finalize(state: ShortVideoState) -> ShortVideoState:
    _step(state, "finalize")
    plan = state["plan"]
    state["generation_mode"] = plan.get("generation_mode", "unknown")
    state["rag_hit_count"] = len(state.get("rag_sources", []))
    return state


def build_short_video_graph():
    graph = StateGraph(ShortVideoState)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_script_plan", generate_script_plan)
    graph.add_node("prepare_output_dir", prepare_output_dir)
    graph.add_node("write_artifacts", write_artifacts)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("retrieve_context")
    graph.add_edge("retrieve_context", "generate_script_plan")
    graph.add_edge("generate_script_plan", "prepare_output_dir")
    graph.add_edge("prepare_output_dir", "write_artifacts")
    graph.add_edge("write_artifacts", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def run_short_video_agent(initial_state: ShortVideoState) -> dict[str, Any]:
    app = build_short_video_graph()
    state = app.invoke(initial_state)
    return {
        "project_dir": state["project_dir"],
        "plan": state["plan"],
        "files": state["files"],
        "audio_muxed": state["audio_muxed"],
        "generation_mode": state["generation_mode"],
        "rag_hit_count": state["rag_hit_count"],
        "graph_steps": state.get("graph_steps", []),
        "agent_framework": "LangGraph",
        "api_status": state.get("api_status", {}),
    }
