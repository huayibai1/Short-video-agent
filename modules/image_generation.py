from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class ImageGenerationError(RuntimeError):
    pass


def generate_image(prompt: str, output_path: str | Path, config: dict[str, Any], timeout: int = 180) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": config.get("model") or "Kwai-Kolors/Kolors",
        "prompt": prompt,
        "image_size": config.get("image_size") or "720x1280",
        "batch_size": int(config.get("batch_size", 1) or 1),
    }
    request = urllib.request.Request(
        (config.get("base_url") or "https://api.siliconflow.cn/v1").rstrip("/")
        + (config.get("endpoint") or "/images/generations"),
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
        raise ImageGenerationError(f"生图接口调用失败：HTTP {exc.code} {body}") from exc
    except Exception as exc:
        raise ImageGenerationError(f"生图接口调用失败：{exc}") from exc

    images = data.get("images") or data.get("data") or []
    if not images:
        raise ImageGenerationError(f"生图接口没有返回图片：{data}")
    first = images[0]
    url = first.get("url") if isinstance(first, dict) else None
    b64 = first.get("b64_json") if isinstance(first, dict) else None
    if url:
        with urllib.request.urlopen(url, timeout=timeout) as image_response:
            output_path.write_bytes(image_response.read())
        return output_path
    if b64:
        output_path.write_bytes(base64.b64decode(b64))
        return output_path
    raise ImageGenerationError(f"无法识别图片返回格式：{data}")

