from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from video_mix.core.media_probe import probe_assets
from video_mix.core.models import Asset, Clip, MediaType, Project
from video_mix.core.scoring import score_assets, score_clips
from video_mix.core.segmenters import (
    FixedIntervalSegmenter,
    PySceneDetectSegmenter,
    plan_segments_for_assets,
)
from video_mix.core.storage import load_assets, load_project, save_assets
from video_mix.core.store import VideoMixFoundationStore

SCENE_SCHEMA_VERSION = "scene-manifest/v1"
ANALYSIS_ALGORITHM_NAME = "bounded-scene-analysis"
ANALYSIS_ALGORITHM_VERSION = "1"


@dataclass(frozen=True, slots=True)
class SceneAnalysisResult:
    analysis_run_id: str
    scene_count: int
    scene_manifest_path: str
    scenes: list[dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _asset_from_clip(asset_lookup: dict[str, Asset], clip: Clip) -> Asset:
    asset = asset_lookup.get(clip.asset_id)
    if asset is None:
        raise KeyError(f"Asset missing for clip {clip.clip_id}: {clip.asset_id}")
    return asset


def _scene_quality_metadata(asset: Asset, clip: Clip) -> dict[str, Any]:
    ffprobe_payload = asset.metadata.get("ffprobe", {}) if isinstance(asset.metadata, dict) else {}
    bitrate = 0
    try:
        bitrate = int(float((ffprobe_payload.get("format") or {}).get("bit_rate") or 0))
    except (TypeError, ValueError):
        bitrate = 0
    return {
        "asset_quality_score": float(asset.quality_score or 0.0),
        "clip_quality_score": float(clip.quality_score or 0.0),
        "orientation": getattr(asset.orientation, "value", str(asset.orientation)),
        "has_audio": bool(asset.has_audio),
        "fps": float(asset.fps or 0.0),
        "width": int(asset.width or 0),
        "height": int(asset.height or 0),
        "bitrate": bitrate,
    }


def _scene_detector_metadata(asset: Asset, clip: Clip, segmenter_name: str) -> dict[str, Any]:
    duration_ms = max(1, clip.duration_ms)
    target_ms = 1700
    duration_penalty = abs(duration_ms - target_ms) / max(target_ms, 1)
    exposure_score = 1.0 if asset.probe_status == "ok" else 0.5
    motion_score = 1.0 if asset.media_type == MediaType.VIDEO else 0.4
    duration_score = max(0.0, 1.0 - min(duration_penalty, 1.0))
    raw_score = round(((duration_score * 0.45) + (exposure_score * 0.25) + (motion_score * 0.30)) * 100, 2)
    return {
        "segmenter": segmenter_name,
        "raw_score": raw_score,
        "duration_score": duration_score,
        "motion_score": motion_score,
        "exposure_score": exposure_score,
        "fallback_fixed_interval": segmenter_name == "fixed_interval",
    }


def analyze_project_scenes(
    work_dir: Path,
    *,
    ffprobe_path: str = "ffprobe",
    scenedetect_path: str = "scenedetect",
    prefer_pyscenedetect: bool = False,
    min_scene_ms: int = 1200,
    fixed_clip_ms: int = 1700,
    max_clips_per_asset: int = 18,
) -> SceneAnalysisResult:
    resolved_work_dir = work_dir.expanduser().resolve()
    project = load_project(resolved_work_dir)
    assets = probe_assets(load_assets(resolved_work_dir), ffprobe_path=ffprobe_path)
    assets = score_assets(assets)
    save_assets(resolved_work_dir, assets)
    asset_lookup = {asset.asset_id: asset for asset in assets}
    video_assets = [asset for asset in assets if asset.media_type == MediaType.VIDEO]
    if not video_assets:
        raise ValueError("No video assets are available for scene analysis.")

    segmenters = []
    if prefer_pyscenedetect:
        segmenters.append(PySceneDetectSegmenter(scenedetect_path))
    segmenters.append(FixedIntervalSegmenter(clip_ms=max(min_scene_ms, fixed_clip_ms), max_clips_per_asset=max_clips_per_asset))

    clips = plan_segments_for_assets(video_assets, resolved_work_dir / "analysis_runs", segmenters=segmenters)
    clips = score_clips(clips, assets)
    analysis_run_id = f"analysis_{uuid4().hex}"
    created_at = _utc_now()
    store = VideoMixFoundationStore(resolved_work_dir)

    store.upsert_analysis_run(
        project_id=project.project_id,
        analysis_run_id=analysis_run_id,
        algorithm_name=ANALYSIS_ALGORITHM_NAME,
        algorithm_version=ANALYSIS_ALGORITHM_VERSION,
        source_kind="proxy" if prefer_pyscenedetect else "original",
        settings_json={
            "min_scene_ms": min_scene_ms,
            "fixed_clip_ms": fixed_clip_ms,
            "max_clips_per_asset": max_clips_per_asset,
            "prefer_pyscenedetect": prefer_pyscenedetect,
            "scenedetect_path": scenedetect_path,
        },
        status="completed",
        created_at=created_at,
        completed_at=created_at,
        error="",
    )

    scene_rows: list[dict[str, Any]] = []
    scene_manifest_path = resolved_work_dir / "reports" / "scene_manifest.json"
    keyframes_dir = resolved_work_dir / "reports" / "scene_keyframes"
    keyframes_dir.mkdir(parents=True, exist_ok=True)

    for index, clip in enumerate(clips, start=1):
        asset = _asset_from_clip(asset_lookup, clip)
        detector_metadata = _scene_detector_metadata(asset, clip, clip.segmenter.value)
        keyframe_path = keyframes_dir / f"{clip.clip_id}.jpg"
        scene_id = f"{analysis_run_id}_scene_{index:04d}"
        row = {
            "scene_id": scene_id,
            "asset_id": asset.asset_id,
            "analysis_run_id": analysis_run_id,
            "start_ms": int(clip.source_start_ms),
            "end_ms": int(clip.source_end_ms),
            "duration_ms": int(clip.duration_ms),
            "keyframe_path": str(keyframe_path.relative_to(resolved_work_dir)).replace("\\", "/"),
            "score_json": _scene_quality_metadata(asset, clip),
            "detector_json": detector_metadata,
            "schema_version": SCENE_SCHEMA_VERSION,
        }
        scene_rows.append(row)
        store.upsert_scene(project_id=project.project_id, **row)

    payload = {
        "schema_version": SCENE_SCHEMA_VERSION,
        "project_id": project.project_id,
        "analysis_run_id": analysis_run_id,
        "scene_count": len(scene_rows),
        "duration_summary_ms": {
            "min": min((row["duration_ms"] for row in scene_rows), default=0),
            "max": max((row["duration_ms"] for row in scene_rows), default=0),
            "median": int(statistics.median([row["duration_ms"] for row in scene_rows])) if scene_rows else 0,
        },
        "scenes": scene_rows,
    }
    scene_manifest_path.write_text(__import__("json").dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return SceneAnalysisResult(
        analysis_run_id=analysis_run_id,
        scene_count=len(scene_rows),
        scene_manifest_path=str(scene_manifest_path.relative_to(resolved_work_dir)).replace("\\", "/"),
        scenes=scene_rows,
    )


def build_episode_groups_from_scenes(
    project: Project,
    assets: list[Asset],
    scene_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    asset_lookup = {asset.asset_id: asset for asset in assets}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for scene in scene_rows:
        asset = asset_lookup.get(str(scene.get("asset_id") or ""))
        if asset is None:
            continue
        group_id = asset.path.parent.name or asset.path.stem
        grouped.setdefault(group_id, []).append(
            {
                "take_id": str(scene["scene_id"]),
                "asset": asset,
                "start_ms": int(scene["start_ms"]),
                "end_ms": int(scene["end_ms"]),
                "duration_ms": int(scene["duration_ms"]),
                "take_index": len(grouped.get(group_id, ())) + 1,
                "marker_split": False,
                "atomic_take": False,
                "take_type": "scene_take",
                "content_identity": f"{asset.asset_id}:{int(scene['start_ms'])}:{int(scene['end_ms'])}",
            }
        )
    result: list[dict[str, Any]] = []
    for position, (group_id, takes) in enumerate(sorted(grouped.items(), key=lambda item: item[0].casefold()), start=1):
        result.append(
            {
                "episode_id": f"scene_episode_{position:03d}",
                "episode_label": group_id,
                "group_id": group_id,
                "takes": takes,
            }
        )
    return result
