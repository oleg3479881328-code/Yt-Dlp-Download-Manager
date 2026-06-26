"""Draft data models for VIDEO MIX.

These models are intentionally simple dataclasses so Codex can adapt them
into the real project without adding framework dependencies too early.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class MediaType(str, Enum):
    VIDEO = "video"
    PHOTO = "photo"


class Orientation(str, Enum):
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    SQUARE = "square"
    UNKNOWN = "unknown"


class CandidateStatus(str, Enum):
    GENERATED = "generated"
    PREVIEWED = "previewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPORTED = "exported"


@dataclass(slots=True)
class Project:
    project_id: str
    name: str
    root_path: Path
    industry_pack: str = "wedding"


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
    working_path: Path | None = None
    thumbnail_path: Path | None = None
    tags: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    duplicate_group_id: str | None = None
    usable: bool = True
    reject_reason: str | None = None

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


@dataclass(slots=True)
class ReelTemplate:
    template_id: str
    pack_id: str
    name: str
    target_duration_ms: int
    pacing: str
    slots: list[TemplateSlot]


@dataclass(slots=True)
class CandidateClip:
    clip_id: str
    slot_id: str
    start_in_reel_ms: int
    end_in_reel_ms: int
    crop_mode: str = "fill_9_16"
    speed: float = 1.0


@dataclass(slots=True)
class CandidateReel:
    candidate_id: str
    project_id: str
    pack_id: str
    template_id: str
    status: CandidateStatus
    score: float
    duration_ms: int
    clips: list[CandidateClip]
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExportPlan:
    candidate_id: str
    output_path: Path
    width: int = 1080
    height: int = 1920
    fps: int = 30
    format: str = "mp4"
