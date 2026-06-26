from __future__ import annotations

from collections import defaultdict

from .models import Clip


def group_by_existing_hash(clips: list[Clip]) -> list[Clip]:
    groups: dict[str, list[Clip]] = defaultdict(list)
    for clip in clips:
        perceptual_hash = clip.metadata.get("perceptual_hash")
        if perceptual_hash:
            groups[perceptual_hash].append(clip)

    for index, group in enumerate(groups.values(), start=1):
        if len(group) < 2:
            continue
        group_id = f"dup_{index:04d}"
        for clip in group:
            clip.duplicate_group_id = group_id
    return clips


def mark_repeated_source_groups(clips: list[Clip], max_per_asset_without_penalty: int = 4) -> list[Clip]:
    by_asset: dict[str, list[Clip]] = defaultdict(list)
    for clip in clips:
        by_asset[clip.asset_id].append(clip)

    for asset_id, asset_clips in by_asset.items():
        if len(asset_clips) <= max_per_asset_without_penalty:
            continue
        for clip in asset_clips[max_per_asset_without_penalty:]:
            clip.duplicate_group_id = clip.duplicate_group_id or f"same_asset_{asset_id}"
    return clips


def apply_duplicate_detection(clips: list[Clip]) -> list[Clip]:
    return mark_repeated_source_groups(group_by_existing_hash(clips))
