from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class VideoGenerationError(RuntimeError):
    pass


def image_to_data_url(image_path: str | Path) -> str:
    image_path = Path(image_path)
    suffix = image_path.suffix.lower().lstrip(".") or "png"
    mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{encoded}"


def scene_to_video_prompt(scene: dict, plan: dict) -> str:
    if scene.get("video_prompt"):
        return str(scene["video_prompt"])
    return (
        "竖屏 9:16，真实短视频风格，无字幕，无水印，无屏幕文字。"
        f"主题：{plan.get('topic', '')}。"
        f"镜头内容：{scene.get('visual', '')}。"
        f"旁白语义：{scene.get('narration', '')}。"
        "镜头运动自然，光线清晰，人物动作真实，适合校园科普短视频。"
    )


def submit_video_task(
    prompt: str,
    config: dict[str, Any],
    image_path: str | Path | None = None,
    image_size: str = "720x1280",
    timeout: int = 120,
) -> str:
    payload: dict[str, Any] = {
        "model": config.get("model") or "Wan-AI/Wan2.2-T2V-A14B",
        "prompt": prompt,
        "negative_prompt": "字幕，水印，logo，乱码文字，低清晰度，畸形人物，过曝，模糊",
        "image_size": image_size,
    }
    if image_path:
        payload["image"] = image_to_data_url(image_path)

    request = urllib.request.Request(
        (config.get("base_url") or "https://api.siliconflow.cn/v1").rstrip("/")
        + (config.get("endpoint") or "/video/submit"),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.get('api_key', '')}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise VideoGenerationError(f"视频提交失败：HTTP {exc.code} {body}") from exc
    except Exception as exc:
        raise VideoGenerationError(f"视频提交失败：{exc}") from exc

    request_id = data.get("requestId")
    if not request_id:
        raise VideoGenerationError(f"视频提交返回缺少 requestId：{data}")
    return request_id


def check_video_status(request_id: str, config: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    payload = {"requestId": request_id}
    request = urllib.request.Request(
        (config.get("base_url") or "https://api.siliconflow.cn/v1").rstrip("/")
        + (config.get("status_endpoint") or "/video/status"),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.get('api_key', '')}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise VideoGenerationError(f"视频状态查询失败：HTTP {exc.code} {body}") from exc
    except Exception as exc:
        raise VideoGenerationError(f"视频状态查询失败：{exc}") from exc


def poll_video_result(
    request_id: str,
    config: dict[str, Any],
    poll_interval: int = 12,
    max_wait_seconds: int = 600,
) -> dict[str, Any]:
    deadline = time.time() + max_wait_seconds
    last_status: dict[str, Any] = {}
    while time.time() < deadline:
        last_status = check_video_status(request_id, config)
        status = last_status.get("status")
        if status == "Succeed":
            return last_status
        if status == "Failed":
            raise VideoGenerationError(f"视频生成失败：{last_status.get('reason', last_status)}")
        time.sleep(poll_interval)
    raise VideoGenerationError(f"视频生成超时，最后状态：{last_status}")


def download_video(url: str, output_path: str | Path, timeout: int = 180) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            output_path.write_bytes(response.read())
    except Exception as exc:
        raise VideoGenerationError(f"视频下载失败：{exc}") from exc
    return output_path


def generate_scene_video(
    scene: dict,
    plan: dict,
    image_path: str | Path,
    output_path: str | Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    prompt = scene_to_video_prompt(scene, plan)
    request_id = submit_video_task(prompt, config, image_path=image_path)
    status = poll_video_result(
        request_id,
        config,
        poll_interval=int(config.get("poll_interval", 12) or 12),
        max_wait_seconds=int(config.get("max_wait_seconds", 600) or 600),
    )
    videos = (status.get("results") or {}).get("videos") or []
    if not videos or not videos[0].get("url"):
        raise VideoGenerationError(f"视频生成成功但没有返回 URL：{status}")
    path = download_video(videos[0]["url"], output_path)
    return {
        "request_id": request_id,
        "prompt": prompt,
        "status": status,
        "path": str(path.resolve()),
    }
