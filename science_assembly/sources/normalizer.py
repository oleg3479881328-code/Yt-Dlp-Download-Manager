from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, List, Optional

JsonDict = Dict[str, Any]


def new_candidate_id(provider: str, beat_index: int, result_index: int) -> str:
    safe_provider = "".join(ch for ch in provider.lower() if ch.isalnum()) or "src"
    return f"{safe_provider}_b{beat_index:03d}_c{result_index:03d}"


def orientation_from_dimensions(width: Optional[int], height: Optional[int]) -> str:
    if not width or not height:
        return "unknown"
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def pick_best_pexels_video_file(video_files: Iterable[JsonDict]) -> Optional[JsonDict]:
    files = [file for file in video_files if isinstance(file, dict)]
    if not files:
        return None
    mp4_files = [file for file in files if str(file.get("file_type", "")).lower() == "video/mp4"] or files
    return sorted(
        mp4_files,
        key=lambda item: (int(item.get("width") or 0) * int(item.get("height") or 0), int(item.get("fps") or 0)),
        reverse=True,
    )[0]


def normalize_pexels_video(
    *,
    raw: JsonDict,
    beat_id: str,
    beat_index: int,
    result_index: int,
    query: str,
) -> JsonDict:
    best_file = pick_best_pexels_video_file(raw.get("video_files", []))
    width = int(raw.get("width") or (best_file or {}).get("width") or 0) or None
    height = int(raw.get("height") or (best_file or {}).get("height") or 0) or None
    user = raw.get("user") or {}
    return {
        "candidate_id": new_candidate_id("pexels", beat_index, result_index),
        "beat_id": beat_id,
        "provider": "pexels",
        "source_url": raw.get("url"),
        "asset_url": (best_file or {}).get("link"),
        "thumbnail_url": raw.get("image"),
        "creator_name": user.get("name"),
        "creator_url": user.get("url"),
        "license_name": "Pexels License / provider terms",
        "license_url": "https://www.pexels.com/license/",
        "query": query,
        "duration_seconds": raw.get("duration"),
        "width": width,
        "height": height,
        "orientation": orientation_from_dimensions(width, height),
        "tags": [],
        "rights_status": "provider_terms_review_needed",
        "download_allowed": "unknown",
        "date_accessed": date.today().isoformat(),
        "raw_provider": raw,
    }


def normalize_pixabay_video(
    *,
    raw: JsonDict,
    beat_id: str,
    beat_index: int,
    result_index: int,
    query: str,
) -> JsonDict:
    videos = raw.get("videos") or {}
    best = videos.get("large") or videos.get("medium") or videos.get("small") or videos.get("tiny") or {}
    width = int(best.get("width") or 0) or None
    height = int(best.get("height") or 0) or None
    page_url = raw.get("pageURL") or raw.get("pageUrl")
    return {
        "candidate_id": new_candidate_id("pixabay", beat_index, result_index),
        "beat_id": beat_id,
        "provider": "pixabay",
        "source_url": page_url,
        "asset_url": best.get("url"),
        "thumbnail_url": raw.get("picture_id"),
        "creator_name": raw.get("user"),
        "creator_url": None,
        "license_name": "Pixabay Content License / provider terms",
        "license_url": "https://pixabay.com/service/license-summary/",
        "query": query,
        "duration_seconds": raw.get("duration"),
        "width": width,
        "height": height,
        "orientation": orientation_from_dimensions(width, height),
        "tags": [tag.strip() for tag in str(raw.get("tags") or "").split(",") if tag.strip()],
        "rights_status": "provider_terms_review_needed",
        "download_allowed": "unknown",
        "date_accessed": date.today().isoformat(),
        "raw_provider": raw,
    }


def flatten_candidates(project_id: str, groups: List[List[JsonDict]]) -> JsonDict:
    candidates: List[JsonDict] = []
    for group in groups:
        candidates.extend(group)
    return {"project_id": project_id, "candidates": candidates}
