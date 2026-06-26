"""Draft scoring rules for VIDEO MIX."""

from __future__ import annotations

from .models import Asset, Clip, Orientation


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def score_asset(asset: Asset) -> float:
    """Very simple metadata-based placeholder score.

    Real visual scoring should be added after the basic pipeline works.
    """
    score = 50.0

    if asset.probe_status == "ok":
        score += 15
    if asset.orientation == Orientation.VERTICAL:
        score += 15
    elif asset.orientation == Orientation.HORIZONTAL:
        score += 5
    if asset.duration_ms and 2_000 <= asset.duration_ms <= 120_000:
        score += 10
    if asset.width and asset.height and min(asset.width, asset.height) >= 720:
        score += 10

    asset.quality_score = clamp_score(score)
    return asset.quality_score


def score_clip(clip: Clip, asset_lookup: dict[str, Asset]) -> float:
    asset = asset_lookup.get(clip.asset_id)
    score = 50.0

    if asset:
        score += asset.quality_score * 0.3
        if asset.orientation == Orientation.VERTICAL:
            score += 10

    if 1500 <= clip.duration_ms <= 5000:
        score += 15
    elif clip.duration_ms < 1000:
        score -= 20

    if clip.duplicate_group_id:
        score -= 15

    clip.quality_score = clamp_score(score)
    clip.usable = clip.quality_score >= 40
    if not clip.usable:
        clip.reject_reason = "low_score"
    return clip.quality_score


def score_assets(assets: list[Asset]) -> list[Asset]:
    for asset in assets:
        score_asset(asset)
    return assets


def score_clips(clips: list[Clip], assets: list[Asset]) -> list[Clip]:
    asset_lookup = {asset.asset_id: asset for asset in assets}
    for clip in clips:
        score_clip(clip, asset_lookup)
    return clips
