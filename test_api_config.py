from __future__ import annotations

import json
from pathlib import Path

from modules.config_store import load_config, text_model_kwargs, embedding_model_config
from modules.embedding_client import create_embeddings
from modules.llm_client import chat_completion
from modules.tts_client import synthesize_siliconflow_speech
from modules.video_generation import submit_video_task


def main() -> None:
    config = load_config()
    out = Path("outputs/api_tests")
    out.mkdir(parents=True, exist_ok=True)

    results = {}
    text = config["text_model"]
    try:
        reply = chat_completion(
            [{"role": "user", "content": "只回复 OK"}],
            api_key=text.get("api_key"),
            base_url=text.get("base_url"),
            model=text.get("model"),
            timeout=int(text.get("timeout", 180) or 180),
        )
        results["text_model"] = {"ok": True, "reply": reply[:120]}
    except Exception as exc:
        results["text_model"] = {"ok": False, "error": str(exc)}

    emb = embedding_model_config(config)
    try:
        vectors = create_embeddings(
            ["短视频脚本生成测试"],
            api_key=emb.get("api_key", ""),
            base_url=emb.get("base_url", ""),
            model=emb.get("model", ""),
            encoding_format=emb.get("encoding_format", "float"),
        )
        results["embedding_model"] = {"ok": True, "dimension": len(vectors[0])}
    except Exception as exc:
        results["embedding_model"] = {"ok": False, "error": str(exc)}

    tts = config["tts_model"]
    try:
        audio = synthesize_siliconflow_speech("这是语音合成测试。", out / "tts_test.wav", tts)
        results["tts_model"] = {"ok": True, "path": str(audio.resolve()), "bytes": audio.stat().st_size}
    except Exception as exc:
        results["tts_model"] = {"ok": False, "error": str(exc)}

    video = config["video_model"]
    try:
        request_id = submit_video_task(
            "竖屏9:16，真实校园短视频风格，一名大学生在图书馆使用AI学习助手，无字幕，无水印。",
            video,
        )
        results["video_model_submit"] = {"ok": True, "request_id": request_id}
    except Exception as exc:
        results["video_model_submit"] = {"ok": False, "error": str(exc)}

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

