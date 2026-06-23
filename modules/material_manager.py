from __future__ import annotations

import hashlib
from pathlib import Path

from .config_store import PROJECT_ROOT


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _score_asset(path: Path, keywords: str) -> int:
    tokens = [token.lower() for token in keywords.replace("_", " ").replace("-", " ").split() if token.strip()]
    name = path.stem.lower()
    score = sum(1 for token in tokens if token in name)
    if score:
        return score
    digest = hashlib.md5((keywords + str(path)).encode("utf-8")).hexdigest()
    return int(digest[:4], 16) % 3


def find_local_video_assets(keywords: str, limit: int = 1) -> list[Path]:
    roots = [PROJECT_ROOT / "assets" / "videos", PROJECT_ROOT / "assets"]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.suffix.lower() in VIDEO_EXTS)
    ranked = sorted(files, key=lambda path: _score_asset(path, keywords), reverse=True)
    return ranked[:limit]

