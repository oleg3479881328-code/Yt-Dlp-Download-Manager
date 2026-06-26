from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .models import (
    Asset,
    CandidateReel,
    CandidateStatus,
    Clip,
    MediaType,
    Orientation,
    OverlayRule,
    PlatformPreset,
    Project,
    SegmenterName,
    TimelineClip,
    TimelineTrack,
    TrackType,
)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {key: to_jsonable(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [to_jsonable(inner) for inner in value]
    if hasattr(value, "value"):
        return value.value
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def work_file(work_dir: Path, name: str) -> Path:
    return work_dir / "reports" / name


def build_project(payload: dict[str, Any]) -> Project:
    return Project(
        project_id=payload["project_id"],
        name=payload["name"],
        root_path=Path(payload["root_path"]),
        industry_pack=payload["industry_pack"],
    )


def build_asset(payload: dict[str, Any]) -> Asset:
    return Asset(
        asset_id=payload["asset_id"],
        project_id=payload["project_id"],
        path=Path(payload["path"]),
        media_type=MediaType(payload["media_type"]),
        duration_ms=payload.get("duration_ms"),
        width=payload.get("width"),
        height=payload.get("height"),
        fps=payload.get("fps"),
        orientation=Orientation(payload.get("orientation", Orientation.UNKNOWN.value)),
        has_audio=payload.get("has_audio", False),
        probe_status=payload.get("probe_status", "pending"),
        quality_score=payload.get("quality_score", 0.0),
        metadata=payload.get("metadata", {}),
    )


def build_clip(payload: dict[str, Any]) -> Clip:
    return Clip(
        clip_id=payload["clip_id"],
        project_id=payload["project_id"],
        asset_id=payload["asset_id"],
        source_path=Path(payload["source_path"]),
        source_start_ms=payload["source_start_ms"],
        source_end_ms=payload["source_end_ms"],
        segmenter=SegmenterName(payload.get("segmenter", SegmenterName.FIXED_INTERVAL.value)),
        working_path=Path(payload["working_path"]) if payload.get("working_path") else None,
        tags=payload.get("tags", []),
        quality_score=payload.get("quality_score", 0.0),
        duplicate_group_id=payload.get("duplicate_group_id"),
        usable=payload.get("usable", True),
        reject_reason=payload.get("reject_reason"),
        metadata=payload.get("metadata", {}),
    )


def build_overlay(payload: dict[str, Any]) -> OverlayRule:
    return OverlayRule(
        overlay_id=payload["overlay_id"],
        text=payload["text"],
        start_ms=payload["start_ms"],
        end_ms=payload["end_ms"],
        placement=payload.get("placement", "safe_center_lower"),
        style_id=payload.get("style_id", "default"),
    )


def build_timeline_clip(payload: dict[str, Any]) -> TimelineClip:
    return TimelineClip(
        clip_id=payload["clip_id"],
        slot_id=payload["slot_id"],
        source_asset_id=payload["source_asset_id"],
        source_start_ms=payload["source_start_ms"],
        source_end_ms=payload["source_end_ms"],
        timeline_start_ms=payload["timeline_start_ms"],
        timeline_end_ms=payload["timeline_end_ms"],
        crop_mode=payload.get("crop_mode", "fill_9_16"),
        speed=payload.get("speed", 1.0),
        metadata=payload.get("metadata", {}),
    )


def build_track(payload: dict[str, Any]) -> TimelineTrack:
    return TimelineTrack(
        track_id=payload["track_id"],
        track_type=TrackType(payload["track_type"]),
        clips=[build_timeline_clip(clip) for clip in payload.get("clips", [])],
        overlays=[build_overlay(overlay) for overlay in payload.get("overlays", [])],
    )


def build_platform_preset(payload: dict[str, Any]) -> PlatformPreset:
    return PlatformPreset(
        preset_id=payload.get("preset_id", "vertical_social"),
        width=payload.get("width", 1080),
        height=payload.get("height", 1920),
        fps=payload.get("fps", 30),
        max_duration_ms=payload.get("max_duration_ms", 180_000),
        format=payload.get("format", "mp4"),
    )


def build_candidate(payload: dict[str, Any]) -> CandidateReel:
    return CandidateReel(
        candidate_id=payload["candidate_id"],
        project_id=payload["project_id"],
        pack_id=payload["pack_id"],
        template_id=payload["template_id"],
        status=CandidateStatus(payload["status"]),
        score=payload["score"],
        duration_ms=payload["duration_ms"],
        tracks=[build_track(track) for track in payload.get("tracks", [])],
        platform_preset=build_platform_preset(payload.get("platform_preset", {})),
        warnings=payload.get("warnings", []),
        review_notes=payload.get("review_notes", ""),
    )


def save_project(work_dir: Path, project: Project) -> None:
    write_json(work_file(work_dir, "project.json"), project)


def save_assets(work_dir: Path, assets: list[Asset]) -> None:
    write_json(work_file(work_dir, "assets.json"), assets)


def save_clips(work_dir: Path, clips: list[Clip]) -> None:
    write_json(work_file(work_dir, "clips.json"), clips)


def save_candidates(work_dir: Path, candidates: list[CandidateReel]) -> None:
    write_json(work_file(work_dir, "candidates.json"), candidates)


def save_summary(work_dir: Path, summary: dict[str, Any]) -> None:
    write_json(work_file(work_dir, "summary.json"), summary)


def load_project(work_dir: Path) -> Project:
    return build_project(read_json(work_file(work_dir, "project.json")))


def load_assets(work_dir: Path) -> list[Asset]:
    return [build_asset(item) for item in read_json(work_file(work_dir, "assets.json"))]


def load_clips(work_dir: Path) -> list[Clip]:
    return [build_clip(item) for item in read_json(work_file(work_dir, "clips.json"))]


def load_candidates(work_dir: Path) -> list[CandidateReel]:
    return [build_candidate(item) for item in read_json(work_file(work_dir, "candidates.json"))]


def build_summary(project: Project, assets: list[Asset], clips: list[Clip], candidates: list[CandidateReel]) -> dict[str, Any]:
    return {
        "project_id": project.project_id,
        "project_name": project.name,
        "pack_id": project.industry_pack,
        "asset_count": len(assets),
        "clip_count": len(clips),
        "candidate_count": len(candidates),
        "approved_candidate_count": sum(candidate.status == CandidateStatus.APPROVED for candidate in candidates),
        "exported_candidate_count": sum(candidate.status == CandidateStatus.EXPORTED for candidate in candidates),
        "generated_candidate_ids": [candidate.candidate_id for candidate in candidates],
    }
