from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class MediaType(StrEnum):
    VIDEO = "video"
    PHOTO = "photo"


class Orientation(StrEnum):
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    SQUARE = "square"
    UNKNOWN = "unknown"


class CandidateStatus(StrEnum):
    GENERATED = "generated"
    PREVIEWED = "previewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPORTED = "exported"


class TrackType(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
    OVERLAY = "overlay"
    CAPTION = "caption"


class SegmenterName(StrEnum):
    TAKE_MARKER = "take_marker"
    FIXED_INTERVAL = "fixed_interval"
    PYSCENEDETECT = "pyscenedetect"


@dataclass(slots=True)
class Project:
    project_id: str
    name: str
    root_path: Path
    industry_pack: str = "wedding"


@dataclass(slots=True)
class PlatformPreset:
    preset_id: str = "vertical_social"
    width: int = 1080
    height: int = 1920
    fps: int = 30
    max_duration_ms: int = 180_000
    format: str = "mp4"


@dataclass(slots=True)
class Asset:
    asset_id: str
    project_id: str
    path: Path
    media_type: MediaType
    duration_ms: int | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    orientation: Orientation = Orientation.UNKNOWN
    has_audio: bool = False
    probe_status: str = "pending"
    quality_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Clip:
    clip_id: str
    project_id: str
    asset_id: str
    source_path: Path
    source_start_ms: int
    source_end_ms: int
    segmenter: SegmenterName = SegmenterName.FIXED_INTERVAL
    working_path: Path | None = None
    tags: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    duplicate_group_id: str | None = None
    usable: bool = True
    reject_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> int:
        return max(0, self.source_end_ms - self.source_start_ms)


@dataclass(slots=True)
class TemplateSlot:
    slot_id: str
    min_duration_ms: int
    max_duration_ms: int
    required_tags: list[str] = field(default_factory=list)
    preferred_tags: list[str] = field(default_factory=list)
    forbidden_tags: list[str] = field(default_factory=list)
    allowed_track_type: TrackType = TrackType.VIDEO


@dataclass(slots=True)
class OverlayRule:
    overlay_id: str
    text: str
    start_ms: int
    end_ms: int
    placement: str = "safe_center_lower"
    style_id: str = "default"


@dataclass(slots=True)
class ReelTemplate:
    template_id: str
    pack_id: str
    name: str
    target_duration_ms: int
    pacing: str
    slots: list[TemplateSlot]
    overlays: list[OverlayRule] = field(default_factory=list)
    platform_preset: PlatformPreset = field(default_factory=PlatformPreset)


@dataclass(slots=True)
class TimelineClip:
    clip_id: str
    slot_id: str
    source_asset_id: str
    source_start_ms: int
    source_end_ms: int
    timeline_start_ms: int
    timeline_end_ms: int
    crop_mode: str = "fill_9_16"
    speed: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TimelineTrack:
    track_id: str
    track_type: TrackType
    clips: list[TimelineClip] = field(default_factory=list)
    overlays: list[OverlayRule] = field(default_factory=list)


@dataclass(slots=True)
class CandidateReel:
    candidate_id: str
    project_id: str
    pack_id: str
    template_id: str
    status: CandidateStatus
    score: float
    duration_ms: int
    tracks: list[TimelineTrack]
    platform_preset: PlatformPreset = field(default_factory=PlatformPreset)
    warnings: list[str] = field(default_factory=list)
    review_notes: str = ""

    @property
    def video_clips(self) -> list[TimelineClip]:
        return [clip for track in self.tracks if track.track_type == TrackType.VIDEO for clip in track.clips]


@dataclass(slots=True)
class ExportPlan:
    candidate_id: str
    output_path: Path
    width: int = 1080
    height: int = 1920
    fps: int = 30
    format: str = "mp4"
    renderer: str = "ffmpeg"
