from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class LLMError(RuntimeError):
    pass


def get_api_config(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> dict[str, str]:
    return {
        "api_key": api_key or os.getenv("OPENAI_API_KEY", ""),
        "base_url": (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/"),
        "model": model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    }


def chat_completion(
    messages: list[dict[str, str]],
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    timeout: int = 90,
) -> str:
    config = get_api_config(api_key, base_url, model)
    if not config["api_key"]:
        raise LLMError("未配置 OPENAI_API_KEY，无法调用大模型。")

    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
    }
    request = urllib.request.Request(
        f"{config['base_url']}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise LLMError(f"模型接口调用失败：HTTP {exc.code} {body}") from exc
    except Exception as exc:
        raise LLMError(f"模型接口调用失败：{exc}") from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"模型接口返回格式异常：{data}") from exc


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError("模型输出中没有找到 JSON 对象。")
    return json.loads(text[start : end + 1])

