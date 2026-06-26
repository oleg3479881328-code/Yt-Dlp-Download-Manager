"""Draft local media scanner for VIDEO MIX."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .models import Asset, MediaType, Project

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


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
    """Scan a local project folder and return draft Asset records.

    This function does not copy or modify source files.
    """
    if not project.root_path.exists():
        raise FileNotFoundError(f"Project folder does not exist: {project.root_path}")

    assets: list[Asset] = []
    for path in sorted(project.root_path.rglob("*")):
        if not path.is_file():
            continue
        media_type = detect_media_type(path)
        if media_type is None:
            continue
        asset_id = stable_id("asset", str(path.resolve()))
        assets.append(
            Asset(
                asset_id=asset_id,
                project_id=project.project_id,
                path=path,
                media_type=media_type,
            )
        )
    return assets
