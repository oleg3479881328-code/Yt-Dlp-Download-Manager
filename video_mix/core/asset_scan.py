from __future__ import annotations

import hashlib
from pathlib import Path

from .models import Asset, MediaType, Project

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
SKIP_DIR_NAMES = {"_video_mix_work", ".git", "__pycache__", ".venv", "node_modules"}


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def detect_media_type(path: Path) -> MediaType | None:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return MediaType.VIDEO
    if suffix in PHOTO_EXTENSIONS:
        return MediaType.PHOTO
    return None


def scan_project_assets(project: Project) -> list[Asset]:
    if not project.root_path.exists():
        raise FileNotFoundError(f"Project folder does not exist: {project.root_path}")

    assets: list[Asset] = []
    for path in sorted(project.root_path.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        media_type = detect_media_type(path)
        if media_type is None:
            continue
        assets.append(
            Asset(
                asset_id=stable_id("asset", str(path.resolve())),
                project_id=project.project_id,
                path=path,
                media_type=media_type,
            )
        )
    return assets
