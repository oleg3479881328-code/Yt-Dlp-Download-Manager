"""Draft micro-clip extraction for VIDEO MIX."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .asset_scan import stable_id
from .models import Asset, Clip, MediaType


DEFAULT_MIN_CLIP_MS = 1500
DEFAULT_MAX_CLIP_MS = 5000


def plan_micro_clips(
    asset: Asset,
    output_dir: Path,
    clip_ms: int = 3000,
    max_clips_per_asset: int = 12,
) -> list[Clip]:
    """Create draft clip records for an asset without running ffmpeg."""
    if asset.media_type != MediaType.VIDEO:
        return []
    if not asset.duration_ms or asset.duration_ms < DEFAULT_MIN_CLIP_MS:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    clips: list[Clip] = []
    cursor = 0
    index = 1

    while cursor + DEFAULT_MIN_CLIP_MS <= asset.duration_ms and len(clips) < max_clips_per_asset:
        end_ms = min(cursor + clip_ms, asset.duration_ms)
        clip_id = stable_id("clip", f"{asset.asset_id}:{cursor}:{end_ms}")
        out_path = output_dir / f"{clip_id}.mp4"
        clips.append(
            Clip(
                clip_id=clip_id,
                project_id=asset.project_id,
                asset_id=asset.asset_id,
                source_path=asset.path,
                source_start_ms=cursor,
                source_end_ms=end_ms,
                working_path=out_path,
            )
        )
        cursor += clip_ms
        index += 1

    return clips


def build_ffmpeg_cut_command(
    clip: Clip,
    ffmpeg_path: str = "ffmpeg",
) -> list[str]:
    if clip.working_path is None:
        raise ValueError("clip.working_path is required")

    start_seconds = clip.source_start_ms / 1000
    duration_seconds = clip.duration_ms / 1000

    return [
        ffmpeg_path,
        "-y",
        "-ss",
        f"{start_seconds:.3f}",
        "-i",
        str(clip.source_path),
        "-t",
        f"{duration_seconds:.3f}",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-shortest",
        str(clip.working_path),
    ]


def extract_clip(clip: Clip, ffmpeg_path: str = "ffmpeg", dry_run: bool = False) -> list[str]:
    """Build or run the ffmpeg command for a planned clip."""
    command = build_ffmpeg_cut_command(clip, ffmpeg_path=ffmpeg_path)
    if dry_run:
        return command
    if clip.working_path:
        clip.working_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(command, check=True)
    return command


def plan_all_micro_clips(assets: list[Asset], output_dir: Path) -> list[Clip]:
    clips: list[Clip] = []
    for asset in assets:
        clips.extend(plan_micro_clips(asset, output_dir=output_dir / asset.asset_id))
    return clips
