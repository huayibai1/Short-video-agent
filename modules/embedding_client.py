from __future__ import annotations

import json
import urllib.error
import urllib.request


class EmbeddingError(RuntimeError):
    pass


def create_embeddings(
    texts: list[str],
    api_key: str,
    base_url: str,
    model: str,
    encoding_format: str = "float",
    timeout: int = 90,
) -> list[list[float]]:
    if not api_key:
        raise EmbeddingError("未配置 Embedding API Key。")
    if not texts:
        return []

    payload = {
        "model": model,
        "input": texts,
    }
    if encoding_format:
        payload["encoding_format"] = encoding_format
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/embeddings",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise EmbeddingError(f"Embedding 接口调用失败：HTTP {exc.code} {body}") from exc
    except Exception as exc:
        raise EmbeddingError(f"Embedding 接口调用失败：{exc}") from exc

    try:
        ordered = sorted(data["data"], key=lambda item: item.get("index", 0))
        return [item["embedding"] for item in ordered]
    except (KeyError, TypeError) as exc:
        raise EmbeddingError(f"Embedding 接口返回格式异常：{data}") from exc


def create_embeddings_batched(
    texts: list[str],
    api_key: str,
    base_url: str,
    model: str,
    encoding_format: str = "float",
    batch_size: int = 16,
    timeout: int = 90,
) -> list[list[float]]:
    embeddings: list[list[float]] = []
    batch_size = max(1, int(batch_size or 16))
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        embeddings.extend(
            create_embeddings(
                batch,
                api_key=api_key,
                base_url=base_url,
                model=model,
                encoding_format=encoding_format,
                timeout=timeout,
            )
        )
    return embeddings
