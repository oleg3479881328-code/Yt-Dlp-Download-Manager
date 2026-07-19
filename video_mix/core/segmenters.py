from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Protocol

from .asset_scan import stable_id
from .models import Asset, Clip, MediaType, SegmenterName


class Segmenter(Protocol):
    name: SegmenterName

    def plan(self, asset: Asset, output_dir: Path) -> list[Clip]:
        """Return planned clips without rendering them."""


class FixedIntervalSegmenter:
    name = SegmenterName.FIXED_INTERVAL

    def __init__(self, clip_ms: int = 3000, max_clips_per_asset: int = 12) -> None:
        self.clip_ms = clip_ms
        self.max_clips_per_asset = max_clips_per_asset

    def plan(self, asset: Asset, output_dir: Path) -> list[Clip]:
        if asset.media_type != MediaType.VIDEO or not asset.duration_ms or asset.duration_ms < 1000:
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
    name = SegmenterName.PYSCENEDETECT

    def __init__(
        self,
        scenedetect_path: str = "scenedetect",
        *,
        ffmpeg_path: str = "ffmpeg",
        scene_threshold: float = 0.30,
        min_scene_ms: int = 1200,
        max_clips_per_asset: int = 18,
    ) -> None:
        self.scenedetect_path = scenedetect_path
        self.ffmpeg_path = ffmpeg_path
        self.scene_threshold = scene_threshold
        self.min_scene_ms = min_scene_ms
        self.max_clips_per_asset = max_clips_per_asset

    def is_available(self) -> bool:
        result = subprocess.run(
            [self.ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def _detect_scene_cut_points_ms(self, asset: Asset) -> list[int]:
        if asset.media_type != MediaType.VIDEO or not asset.duration_ms or asset.duration_ms < self.min_scene_ms:
            return []
        command = [
            self.ffmpeg_path,
            "-hide_banner",
            "-i",
            str(asset.path),
            "-filter:v",
            f"select='gt(scene,{self.scene_threshold})',metadata=print:file=-",
            "-an",
            "-f",
            "null",
            "-",
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            return []
        points: list[int] = []
        for match in re.finditer(r"pts_time:([0-9]+(?:\.[0-9]+)?)", completed.stdout):
            pts_ms = int(round(float(match.group(1)) * 1000))
            if pts_ms > 0:
                points.append(pts_ms)
        deduped: list[int] = []
        for point in sorted(points):
            if not deduped or point - deduped[-1] >= self.min_scene_ms:
                deduped.append(point)
        return deduped

    def plan(self, asset: Asset, output_dir: Path) -> list[Clip]:
        if not self.is_available():
            return []
        cut_points_ms = self._detect_scene_cut_points_ms(asset)
        if not cut_points_ms:
            return []
        output_dir.mkdir(parents=True, exist_ok=True)
        clips: list[Clip] = []
        boundaries = [0, *cut_points_ms, int(asset.duration_ms or 0)]
        for start_ms, end_ms in zip(boundaries, boundaries[1:], strict=False):
            if len(clips) >= self.max_clips_per_asset:
                break
            if end_ms - start_ms < self.min_scene_ms:
                continue
            clip_id = stable_id("clip", f"{asset.asset_id}:{self.name.value}:{start_ms}:{end_ms}")
            clips.append(
                Clip(
                    clip_id=clip_id,
                    project_id=asset.project_id,
                    asset_id=asset.asset_id,
                    source_path=asset.path,
                    source_start_ms=start_ms,
                    source_end_ms=end_ms,
                    segmenter=self.name,
                    working_path=output_dir / f"{clip_id}.mp4",
                    metadata={
                        "scene_threshold": self.scene_threshold,
                        "scene_detected": True,
                    },
                )
            )
        return clips


def plan_asset_segments(asset: Asset, output_dir: Path, segmenters: list[Segmenter]) -> list[Clip]:
    for segmenter in segmenters:
        clips = segmenter.plan(asset, output_dir / segmenter.name.value / asset.asset_id)
        if clips:
            for clip in clips:
                if segmenter.name == SegmenterName.FIXED_INTERVAL:
                    clip.metadata["segmenter_fallback"] = "fixed_interval"
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
        raise ValueError(f"working_path missing for clip {clip.clip_id}")

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
        "-r",
        "30",
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


def extract_clip(clip: Clip, ffmpeg_path: str = "ffmpeg") -> list[str]:
    command = build_ffmpeg_cut_command(clip, ffmpeg_path=ffmpeg_path)
    clip.working_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(command, check=True)
    return command
