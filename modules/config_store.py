from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "model_config.json"
DB_PATH = PROJECT_ROOT / "config" / "model_config.db"


DEFAULT_CONFIG: dict[str, Any] = {
    "provider_profile": {
        "provider": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": "",
        "usage": "统一供应商配置。点击页面中的同步按钮后，可写入所有模型配置。",
    },
    "text_model": {
        "enabled": False,
        "provider": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "endpoint": "/chat/completions",
        "api_key": "",
        "model": "Qwen/Qwen3-8B",
        "timeout": 180,
        "usage": "生成标题、脚本、分镜、字幕文案。硅基流动接口兼容 OpenAI Chat Completions。",
    },
    "embedding_model": {
        "enabled": False,
        "provider": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "endpoint": "/embeddings",
        "api_key": "",
        "model": "Qwen/Qwen3-Embedding-8B",
        "encoding_format": "float",
        "batch_size": 16,
        "usage": "RAG 知识库向量化与语义检索。未启用或调用失败时降级为本地 TF-IDF。",
    },
    "tts_model": {
        "enabled": False,
        "provider": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "endpoint": "/audio/speech",
        "api_key": "",
        "model": "FunAudioLLM/CosyVoice2-0.5B",
        "voice": "FunAudioLLM/CosyVoice2-0.5B:alex",
        "usage": "把配音文案合成为音频。当前流水线保留 Windows SAPI 回退，后续可直接调用该 API。",
    },
    "image_model": {
        "enabled": False,
        "provider": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "endpoint": "/images/generations",
        "api_key": "",
        "model": "Kwai-Kolors/Kolors",
        "image_size": "720x1280",
        "batch_size": 1,
        "usage": "根据 LLM 生成的 image_prompt 生成 I2V 视频模型参考图。",
    },
    "video_model": {
        "enabled": False,
        "provider": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "endpoint": "/video/submit",
        "status_endpoint": "/video/status",
        "api_key": "",
        "model": "Wan-AI/Wan2.2-T2V-A14B",
        "max_scene_videos": 15,
        "poll_interval": 12,
        "max_wait_seconds": 600,
        "usage": "预留视频生成模型位置。可用于按分镜生成短视频素材，不直接替代最终合成流程。",
    },
    "render_engine": {
        "enabled": True,
        "provider": "OpenCV + imageio-ffmpeg",
        "base_url": "",
        "api_key": "",
        "model": "local-render",
        "usage": "本地合成工具：统一控制字幕、配音、时长并导出 MP4。",
    },
}


def load_config() -> dict[str, Any]:
    if DB_PATH.exists():
        return _load_from_db()
    if not CONFIG_PATH.exists():
        config = json.loads(json.dumps(DEFAULT_CONFIG, ensure_ascii=False))
        save_config(config)
        return config
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    merged = json.loads(json.dumps(DEFAULT_CONFIG, ensure_ascii=False))
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    save_config(merged)
    return merged


def save_config(config: dict[str, Any]) -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_config (
                section TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for section, payload in config.items():
            conn.execute(
                """
                INSERT INTO model_config(section, payload, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(section) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (section, json.dumps(payload, ensure_ascii=False)),
            )
        conn.commit()
    return DB_PATH


def _load_from_db() -> dict[str, Any]:
    merged = json.loads(json.dumps(DEFAULT_CONFIG, ensure_ascii=False))
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_config (
                section TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        rows = conn.execute("SELECT section, payload FROM model_config").fetchall()
    for section, payload_text in rows:
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(merged.get(section), dict):
            merged[section].update(payload)
        else:
            merged[section] = payload
    return merged


def text_model_kwargs(config: dict[str, Any]) -> dict[str, str | None]:
    text_model = config.get("text_model", {})
    return {
        "api_key": text_model.get("api_key") or None,
        "base_url": text_model.get("base_url") or None,
        "model": text_model.get("model") or None,
        "timeout": int(text_model.get("timeout", 180) or 180),
    }


def embedding_model_config(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("embedding_model", {})


def apply_provider_profile(config: dict[str, Any]) -> dict[str, Any]:
    profile = config.get("provider_profile", {})
    provider = profile.get("provider", "SiliconFlow")
    base_url = profile.get("base_url", "https://api.siliconflow.cn/v1")
    api_key = profile.get("api_key", "")
    for key in ("text_model", "embedding_model", "tts_model", "image_model", "video_model"):
        section = config.get(key, {})
        section["provider"] = provider
        section["base_url"] = base_url
        if api_key:
            section["api_key"] = api_key
    return config


def image_model_config(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("image_model", {})


def tts_model_config(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("tts_model", {})


def video_model_config(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("video_model", {})
