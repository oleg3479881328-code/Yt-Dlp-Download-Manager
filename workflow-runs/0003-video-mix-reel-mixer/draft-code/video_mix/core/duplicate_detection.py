"""Draft duplicate detection for VIDEO MIX.

Stage 1 can keep this lightweight. Stage 1.5 should add real frame sampling
and perceptual hashing, for example with imagehash.
"""

from __future__ import annotations

from collections import defaultdict

from .models import Clip


def group_by_existing_hash(clips: list[Clip]) -> list[Clip]:
    """Assign duplicate groups when perceptual_hash is already present.

    This is a placeholder. It does not calculate hashes.
    """
    groups: dict[str, list[Clip]] = defaultdict(list)
    for clip in clips:
        if clip.perceptual_hash:
            groups[clip.perceptual_hash].append(clip)

    for index, group in enumerate(groups.values(), start=1):
        if len(group) < 2:
            continue
        group_id = f"dup_{index:04d}"
        for clip in group:
            clip.duplicate_group_id = group_id

    return clips


def mark_repeated_source_groups(clips: list[Clip], max_per_asset_without_penalty: int = 4) -> list[Clip]:
    """Soft duplicate grouping by source asset overuse.

    This is not true visual duplicate detection. It is a safe Stage 1 fallback
    to discourage too many clips from the same original file.
    """
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
    clips = group_by_existing_hash(clips)
    clips = mark_repeated_source_groups(clips)
    return clips
