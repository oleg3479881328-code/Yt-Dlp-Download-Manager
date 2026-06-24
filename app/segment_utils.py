from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TIME_RE = re.compile(
    r"^\s*(?:(?P<hours>\d+):)?(?P<minutes>\d{1,2}):(?P<seconds>\d{1,2}(?:\.\d+)?)\s*$"
)
_SAFE_LABEL_RE = re.compile(r"[^A-Za-z0-9._ -]+")


class SegmentValidationError(ValueError):
    """Raised when a selected media segment is invalid."""


@dataclass(frozen=True)
class SegmentRange:
    """Normalized selected time range for a short clip job."""

    start: float
    end: float
    label: str = "clip"

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)

    @property
    def section_expression(self) -> str:
        return f"*{format_seconds_for_section(self.start)}-{format_seconds_for_section(self.end)}"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "label": self.label,
            "section_expression": self.section_expression,
        }


def parse_time_value(value: str | int | float, *, field_name: str = "time") -> float:
    """Parse either numeric seconds or HH:MM:SS(.ms) / MM:SS(.ms)."""

    if isinstance(value, bool):
        raise SegmentValidationError(f"{field_name} must be a time value, not boolean")

    if isinstance(value, int | float):
        seconds = float(value)
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise SegmentValidationError(f"{field_name} is required")
        try:
            seconds = float(raw)
        except ValueError:
            match = _TIME_RE.match(raw)
            if not match:
                raise SegmentValidationError(
                    f"{field_name} must be seconds or MM:SS / HH:MM:SS format"
                ) from None
            hours = int(match.group("hours") or 0)
            minutes = int(match.group("minutes"))
            secs = float(match.group("seconds"))
            if minutes >= 60 or secs >= 60:
                raise SegmentValidationError(
                    f"{field_name} has invalid minute/second values"
                ) from None
            seconds = hours * 3600 + minutes * 60 + secs
    else:
        raise SegmentValidationError(f"{field_name} must be seconds or timestamp string")

    if seconds < 0:
        raise SegmentValidationError(f"{field_name} must be >= 0")
    return round(seconds, 3)


def sanitize_segment_label(label: str | None) -> str:
    """Return a compact Windows-friendly filename label."""

    cleaned = _SAFE_LABEL_RE.sub("_", str(label or "clip"))
    cleaned = re.sub(r"^[\s._-]+|[\s._-]+$", "", cleaned)
    cleaned = re.sub(r"\s+", "_", cleaned)
    return (cleaned or "clip")[:60]


def normalize_segment_payload(payload: dict[str, Any]) -> SegmentRange:
    """Validate and normalize API/UI payload into a SegmentRange."""

    if "start" not in payload:
        raise SegmentValidationError("start is required")

    start = parse_time_value(payload["start"], field_name="start")

    has_end = payload.get("end") not in {None, ""}
    has_duration = payload.get("duration") not in {None, ""}
    if has_end and has_duration:
        raise SegmentValidationError("Provide either end or duration, not both")
    if not has_end and not has_duration:
        raise SegmentValidationError("end or duration is required")

    if has_end:
        end = parse_time_value(payload["end"], field_name="end")
    else:
        duration = parse_time_value(payload["duration"], field_name="duration")
        if duration <= 0:
            raise SegmentValidationError("duration must be > 0")
        end = round(start + duration, 3)

    if end <= start:
        raise SegmentValidationError("end must be greater than start")

    return SegmentRange(start=start, end=end, label=sanitize_segment_label(payload.get("label")))


def format_seconds_for_section(seconds: float) -> str:
    """Format seconds compactly for a yt-dlp section expression."""

    value = round(float(seconds), 3)
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def build_clip_output_template(output_dir: Path, *, label: str) -> str:
    """Build an output template for segment clips under the output root."""

    safe_label = sanitize_segment_label(label)
    return str(output_dir / "clips" / "%(title).160s [%(id)s]" / f"clip_{safe_label}.%(ext)s")
