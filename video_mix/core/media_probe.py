from __future__ import annotations

import json
import subprocess

from .models import Asset, MediaType, Orientation


def get_orientation(width: int | None, height: int | None) -> Orientation:
    if not width or not height:
        return Orientation.UNKNOWN
    if width == height:
        return Orientation.SQUARE
    if height > width:
        return Orientation.VERTICAL
    return Orientation.HORIZONTAL


def _parse_fps(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    if "/" in value:
        left, right = value.split("/", 1)
        try:
            denominator = float(right)
            return float(left) / denominator if denominator else None
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def probe_asset(asset: Asset, ffprobe_path: str = "ffprobe") -> Asset:
    if asset.media_type == MediaType.PHOTO:
        asset.probe_status = "skipped_photo"
        return asset

    command = [
        ffprobe_path,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(asset.path),
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)
    except Exception as exc:  # noqa: BLE001
        asset.probe_status = "failed"
        asset.metadata["probe_error"] = str(exc)
        return asset

    streams = payload.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    fmt = payload.get("format", {})

    if video_stream:
        asset.width = int(video_stream.get("width") or 0) or None
        asset.height = int(video_stream.get("height") or 0) or None
        asset.fps = _parse_fps(video_stream.get("avg_frame_rate"))
        asset.orientation = get_orientation(asset.width, asset.height)

    duration_seconds = fmt.get("duration")
    if duration_seconds is not None:
        try:
            asset.duration_ms = int(float(duration_seconds) * 1000)
        except ValueError:
            asset.duration_ms = None

    asset.has_audio = audio_stream is not None
    asset.probe_status = "ok" if video_stream else "warning_no_video_stream"
    asset.metadata["ffprobe"] = payload
    return asset


def probe_assets(assets: list[Asset], ffprobe_path: str = "ffprobe") -> list[Asset]:
    return [probe_asset(asset, ffprobe_path=ffprobe_path) for asset in assets]
