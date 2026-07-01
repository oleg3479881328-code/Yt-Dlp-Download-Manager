from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from .asset_scan import stable_id
from .models import Asset, Clip, MediaType, SegmenterName

VM_TAKE_BREAK_MARKER = "VM_TAKE_BREAK_V1"
DEFAULT_TAKE_MARKER_COLOR = "#ff00ff"


class Segmenter(Protocol):
    name: SegmenterName

    def plan(self, asset: Asset, output_dir: Path) -> list[Clip]:
        """Return planned clips without rendering them."""


def parse_hex_rgb(hex_color: str) -> tuple[int, int, int]:
    normalized = hex_color.strip().lower().removeprefix("#")
    if len(normalized) != 6:
        raise ValueError(f"Expected a 6-digit RGB hex color, got: {hex_color}")
    return (int(normalized[0:2], 16), int(normalized[2:4], 16), int(normalized[4:6], 16))


def rgb_distance(left: tuple[int, ...], right: tuple[int, int, int]) -> int:
    return sum(abs(left[index] - right[index]) for index in range(3))


def group_marker_sample_times(
    marker_sample_times_ms: list[int],
    *,
    sample_interval_ms: int,
    min_marker_ms: int,
) -> list[tuple[int, int]]:
    if not marker_sample_times_ms:
        return []

    grouped: list[tuple[int, int]] = []
    current_start = marker_sample_times_ms[0]
    current_last = marker_sample_times_ms[0]
    max_gap_ms = int(sample_interval_ms * 1.5)

    for marker_time_ms in marker_sample_times_ms[1:]:
        if marker_time_ms - current_last <= max_gap_ms:
            current_last = marker_time_ms
            continue
        interval_end = current_last + sample_interval_ms
        if interval_end - current_start >= min_marker_ms:
            grouped.append((current_start, interval_end))
        current_start = marker_time_ms
        current_last = marker_time_ms

    interval_end = current_last + sample_interval_ms
    if interval_end - current_start >= min_marker_ms:
        grouped.append((current_start, interval_end))
    return grouped


def detect_take_marker_intervals(
    video_path: Path,
    *,
    ffmpeg_path: str = "ffmpeg",
    marker_hex_color: str = DEFAULT_TAKE_MARKER_COLOR,
    sample_fps: float = 4.0,
    color_distance_threshold: int = 90,
    min_marker_ms: int = 250,
) -> list[tuple[int, int]]:
    """Detect full-frame technical color markers and return marker intervals in ms.

    The detector samples the video at a low frame rate, scales every sampled frame to 1x1,
    and compares the average RGB color against the configured marker color. A short
    magenta full-screen card is therefore machine-readable, while normal footage falls
    through to the next segmenter.
    """
    if sample_fps <= 0:
        raise ValueError("sample_fps must be greater than 0")

    sample_interval_ms = max(1, int(round(1000 / sample_fps)))
    target_rgb = parse_hex_rgb(marker_hex_color)
    command = [
        ffmpeg_path,
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vf",
        f"fps={sample_fps},scale=1:1:flags=area",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, check=False)
    except FileNotFoundError:
        return []
    if result.returncode != 0:
        return []

    marker_sample_times_ms: list[int] = []
    frame_size = 3
    for frame_index, offset in enumerate(range(0, len(result.stdout) - frame_size + 1, frame_size)):
        rgb = tuple(result.stdout[offset : offset + frame_size])
        if rgb_distance(rgb, target_rgb) <= color_distance_threshold:
            marker_sample_times_ms.append(frame_index * sample_interval_ms)

    return group_marker_sample_times(
        marker_sample_times_ms,
        sample_interval_ms=sample_interval_ms,
        min_marker_ms=min_marker_ms,
    )


def build_take_marker_clips(
    asset: Asset,
    output_dir: Path,
    marker_intervals_ms: list[tuple[int, int]],
    *,
    marker_hex_color: str = DEFAULT_TAKE_MARKER_COLOR,
    marker_trim_padding_ms: int = 100,
    min_take_ms: int = 500,
) -> list[Clip]:
    if not asset.duration_ms:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    clips: list[Clip] = []
    cursor_ms = 0
    normalized_intervals = sorted(
        (max(0, start_ms), max(0, end_ms))
        for start_ms, end_ms in marker_intervals_ms
        if end_ms > start_ms
    )

    def append_take(start_ms: int, end_ms: int) -> None:
        if end_ms - start_ms < min_take_ms:
            return
        take_index = len(clips) + 1
        clip_id = stable_id("clip", f"{asset.asset_id}:{SegmenterName.TAKE_MARKER.value}:{take_index}:{start_ms}:{end_ms}")
        clips.append(
            Clip(
                clip_id=clip_id,
                project_id=asset.project_id,
                asset_id=asset.asset_id,
                source_path=asset.path,
                source_start_ms=start_ms,
                source_end_ms=end_ms,
                segmenter=SegmenterName.TAKE_MARKER,
                working_path=output_dir / f"{clip_id}.mp4",
                tags=["take"],
                metadata={
                    "take_index": take_index,
                    "take_marker": VM_TAKE_BREAK_MARKER,
                    "take_marker_color": marker_hex_color,
                    "take_marker_count": len(normalized_intervals),
                    "take_marker_trim_padding_ms": marker_trim_padding_ms,
                },
            )
        )

    for marker_start_ms, marker_end_ms in normalized_intervals:
        marker_start_ms = min(marker_start_ms, asset.duration_ms)
        marker_end_ms = min(max(marker_end_ms, marker_start_ms), asset.duration_ms)
        take_end_ms = max(cursor_ms, marker_start_ms - marker_trim_padding_ms)
        append_take(cursor_ms, take_end_ms)
        cursor_ms = min(asset.duration_ms, marker_end_ms + marker_trim_padding_ms)

    append_take(cursor_ms, asset.duration_ms)
    return clips


class TakeMarkerSegmenter:
    name = SegmenterName.TAKE_MARKER

    def __init__(
        self,
        *,
        ffmpeg_path: str = "ffmpeg",
        marker_hex_color: str = DEFAULT_TAKE_MARKER_COLOR,
        sample_fps: float = 4.0,
        color_distance_threshold: int = 90,
        min_marker_ms: int = 250,
        marker_trim_padding_ms: int = 100,
        min_take_ms: int = 500,
    ) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.marker_hex_color = marker_hex_color
        self.sample_fps = sample_fps
        self.color_distance_threshold = color_distance_threshold
        self.min_marker_ms = min_marker_ms
        self.marker_trim_padding_ms = marker_trim_padding_ms
        self.min_take_ms = min_take_ms

    def _detect_marker_intervals(self, asset: Asset) -> list[tuple[int, int]]:
        return detect_take_marker_intervals(
            asset.path,
            ffmpeg_path=self.ffmpeg_path,
            marker_hex_color=self.marker_hex_color,
            sample_fps=self.sample_fps,
            color_distance_threshold=self.color_distance_threshold,
            min_marker_ms=self.min_marker_ms,
        )

    def plan(self, asset: Asset, output_dir: Path) -> list[Clip]:
        if asset.media_type != MediaType.VIDEO or not asset.duration_ms or asset.duration_ms < self.min_take_ms:
            return []

        marker_intervals = self._detect_marker_intervals(asset)
        if not marker_intervals:
            return []

        return build_take_marker_clips(
            asset,
            output_dir,
            marker_intervals,
            marker_hex_color=self.marker_hex_color,
            marker_trim_padding_ms=self.marker_trim_padding_ms,
            min_take_ms=self.min_take_ms,
        )


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

    def __init__(self, scenedetect_path: str = "scenedetect") -> None:
        self.scenedetect_path = scenedetect_path

    def is_available(self) -> bool:
        result = subprocess.run(
            [self.scenedetect_path, "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def plan(self, asset: Asset, output_dir: Path) -> list[Clip]:
        if not self.is_available():
            return []
        return []


def ensure_take_marker_segmenter(segmenters: list[Segmenter]) -> list[Segmenter]:
    if any(segmenter.name == SegmenterName.TAKE_MARKER for segmenter in segmenters):
        return segmenters
    return [TakeMarkerSegmenter(), *segmenters]


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
    chosen_segmenters = ensure_take_marker_segmenter(list(segmenters)) if segmenters is not None else [TakeMarkerSegmenter(), FixedIntervalSegmenter()]
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
