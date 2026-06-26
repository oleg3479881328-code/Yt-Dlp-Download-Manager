from __future__ import annotations

from .models import Clip

KEYWORD_TAGS: dict[str, list[str]] = {
    "bride": ["bride"],
    "groom": ["groom"],
    "ring": ["rings", "details"],
    "rings": ["rings", "details"],
    "dress": ["dress", "bride"],
    "dance": ["dance", "party"],
    "venue": ["venue"],
    "kiss": ["kiss", "couple", "emotion"],
    "couple": ["couple", "emotion"],
    "prep": ["preparation"],
    "makeup": ["preparation", "bride"],
    "guest": ["guests"],
    "guests": ["guests"],
    "bts": ["backstage", "photographer"],
    "backstage": ["backstage", "photographer"],
    "detail": ["details"],
    "details": ["details"],
}


def infer_tags_from_path(path_text: str) -> list[str]:
    lower = path_text.lower()
    tags: set[str] = set()
    for keyword, mapped_tags in KEYWORD_TAGS.items():
        if keyword in lower:
            tags.update(mapped_tags)
    return sorted(tags)


def apply_filename_tags(clips: list[Clip]) -> list[Clip]:
    for clip in clips:
        tags = set(clip.tags)
        tags.update(infer_tags_from_path(str(clip.source_path)))
        clip.tags = sorted(tags)
    return clips
