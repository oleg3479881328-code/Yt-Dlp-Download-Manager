from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .segment_utils import build_clip_output_template


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def format_eta(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    minutes, sec = divmod(max(seconds, 0), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def format_speed(speed: float | None) -> str | None:
    if not speed:
        return None
    value = float(speed)
    for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
        if value < 1024 or unit == "GB/s":
            return f"{value:.1f} {unit}"
        value /= 1024
    return None


def build_ydl_options(
    output_dir: Path,
    mode: str,
    quality: str,
    progress_hook,
    segment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    options = {
        "outtmpl": str(output_dir / "%(title).180s [%(id)s].%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
        "ignoreerrors": False,
    }
    if segment:
        options["outtmpl"] = build_clip_output_template(output_dir, label=segment.get("label") or "clip")
        options["download_ranges"] = lambda *_: [
            {
                "start_time": segment["start"],
                "end_time": segment["end"],
                "title": segment.get("label") or "clip",
                "index": 1,
            }
        ]
        options["force_keyframes_at_cuts"] = True
    if mode == "audio":
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    else:
        options["format"] = quality or "bestvideo*+bestaudio/best"
        options["merge_output_format"] = "mp4"
    return options


def _require_youtube_dl():
    try:
        from yt_dlp import YoutubeDL
    except ModuleNotFoundError as exc:
        raise RuntimeError("yt_dlp is not installed. Install project requirements to use downloader analysis.") from exc
    return YoutubeDL


def analyze_url(url: str) -> dict[str, Any]:
    YoutubeDL = _require_youtube_dl()
    with YoutubeDL(
        {
            "quiet": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
            "no_warnings": True,
        }
    ) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = info.get("entries") or []
    is_playlist = info.get("_type") == "playlist" or len(entries) > 1
    normalized_entries = []

    if is_playlist:
        for index, entry in enumerate(entries, start=1):
            if not entry:
                continue
            entry_url = entry.get("url") or entry.get("webpage_url")
            if entry_url and not str(entry_url).startswith("http"):
                entry_url = f"https://www.youtube.com/watch?v={entry_url}"
            normalized_entries.append(
                {
                    "index": index,
                    "title": entry.get("title") or f"Item {index}",
                    "url": entry_url,
                    "duration": entry.get("duration"),
                }
            )

    return {
        "url": url,
        "title": info.get("title") or url,
        "type": "playlist" if is_playlist else "single",
        "extractor": info.get("extractor_key"),
        "item_count": len(normalized_entries) if is_playlist else 1,
        "duration": info.get("duration"),
        "entries": normalized_entries,
        "thumbnail": info.get("thumbnail"),
    }
