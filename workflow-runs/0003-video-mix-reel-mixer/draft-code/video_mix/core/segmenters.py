"""Draft pluggable segmentation layer for VIDEO MIX.

Stage 1 should not hardcode only fixed 3-second cuts.
This draft keeps fixed interval as fallback and leaves a PySceneDetect adapter slot.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from .asset_scan import stable_id
from .models import Asset, Clip, MediaType, SegmenterName


class Segmenter(Protocol):
    name: SegmenterName

    def plan(self, asset: Asset, output_dir: Path) -> list[Clip]:
        """Return planned clips without necessarily rendering them."""


class FixedIntervalSegmenter:
    name = SegmenterName.FIXED_INTERVAL

    def __init__(self, clip_ms: int = 3000, max_clips_per_asset: int = 12) -> None:
        self.clip_ms = clip_ms
        self.max_clips_per_asset = max_clips_per_asset

    def plan(self, asset: Asset, output_dir: Path) -> list[Clip]:
        if asset.media_type != MediaType.VIDEO:
            return []
        if not asset.duration_ms or asset.duration_ms < 1000:
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        clips: list[Clip] = []
        cursor = 0

        while cursor + 1000 <= asset.duration_ms and len(clips) < self.max_clips_per_asset:
            end_ms = min(cursor + self.clip_ms, asset.duration_ms)
            clip_id = stable_id("clip", f"{asset.asset_id}:{self.name.value}:{cursor}:{end_ms}")
            clips.append(
                Clip(
                    clip_id=clip_id,
                    project_id=asset.project_id,
                    asset_id=asset.asset_id,
                    source_path=asset.path,
                    source_start_ms=cursor,
                    source_end_ms=end_ms,
                    segmenter=self.name,
                    working_path=output_dir / f"{clip_id}.mp4",
                )
            )
            cursor += self.clip_ms

        return clips


class PySceneDetectSegmenter:
    """Draft adapter placeholder.

    Codex should replace this with a real PySceneDetect integration after
    dependency and Windows validation. For now this returns no clips unless
    a future parser is implemented.
    """

    name = SegmenterName.PYSCENEDETECT

    def __init__(self, scenedetect_path: str = "scenedetect") -> None:
        self.scenedetect_path = scenedetect_path

    def build_detect_command(self, asset: Asset) -> list[str]:
        return [
            self.scenedetect_path,
            "-i",
            str(asset.path),
            "detect-content",
            "list-scenes",
        ]

    def plan(self, asset: Asset, output_dir: Path) -> list[Clip]:
        # Placeholder by design. Stage 1 can start with FixedIntervalSegmenter.
        # Stage 1.5 should parse PySceneDetect scene CSV/list output here.
        return []


def plan_asset_segments(asset: Asset, output_dir: Path, segmenters: list[Segmenter]) -> list[Clip]:
    for segmenter in segmenters:
        clips = segmenter.plan(asset, output_dir / segmenter.name.value / asset.asset_id)
        if clips:
            return clips
    return []


def plan_segments_for_assets(assets: list[Asset], output_dir: Path, segmenters: list[Segmenter] | None = None) -> list[Clip]:
    chosen_segmenters = segmenters or [FixedIntervalSegmenter()]
    clips: list[Clip] = []
    for asset in assets:
        clips.extend(plan_asset_segments(asset, output_dir, chosen_segmenters))
    return clips


def build_ffmpeg_cut_command(clip: Clip, ffmpeg_path: str = "ffmpeg") -> list[str]:
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
    command = build_ffmpeg_cut_command(clip, ffmpeg_path=ffmpeg_path)
    if dry_run:
        return command
    if clip.working_path:
        clip.working_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(command, check=True)
    return command
