from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class TTSError(RuntimeError):
    pass


def synthesize_siliconflow_speech(
    text: str,
    output_path: str | Path,
    config: dict[str, Any],
    timeout: int = 180,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    response_format = output_path.suffix.lstrip(".") or "wav"
    if response_format not in {"mp3", "opus", "wav", "pcm"}:
        response_format = "wav"

    payload = {
        "model": config.get("model") or "fishaudio/fish-speech-1.5",
        "input": text,
        "response_format": response_format,
        "sample_rate": int(config.get("sample_rate", 44100) or 44100),
        "stream": False,
        "speed": float(config.get("speed", 1.0) or 1.0),
    }
    if config.get("voice"):
        payload["voice"] = config["voice"]
    request = urllib.request.Request(
        (config.get("base_url") or "https://api.siliconflow.cn/v1").rstrip("/")
        + (config.get("endpoint") or "/audio/speech"),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.get('api_key', '')}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise TTSError(f"TTS 接口调用失败：HTTP {exc.code} {body}") from exc
    except Exception as exc:
        raise TTSError(f"TTS 接口调用失败：{exc}") from exc

    if not data:
        raise TTSError("TTS 接口返回空音频。")
    output_path.write_bytes(data)
    return output_path
