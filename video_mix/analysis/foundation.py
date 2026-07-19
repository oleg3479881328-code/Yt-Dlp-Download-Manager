from __future__ import annotations

import json
import statistics
import subprocess
from dataclasses import dataclass, replace
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
    build_ffmpeg_cut_command,
    plan_segments_for_assets,
)
from video_mix.core.storage import load_assets, load_project, save_assets
from video_mix.core.store import VideoMixFoundationStore
from video_mix.proxy_pipeline import PROXY_READY, load_proxy_manifest

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
    measured_quality_score = round(
        (
            min(1.0, max(0.0, bitrate / 4_000_000)) * 0.35
            + min(1.0, max(0.0, float(asset.fps or 0.0) / 30.0)) * 0.20
            + min(1.0, max(0.0, (int(asset.width or 0) * int(asset.height or 0)) / (1280 * 720))) * 0.25
            + (1.0 if asset.has_audio else 0.0) * 0.10
            + min(1.0, max(0.0, int(clip.duration_ms) / 2000)) * 0.10
        )
        * 100,
        2,
    )
    return {
        "measured_quality_score": measured_quality_score,
        "orientation": getattr(asset.orientation, "value", str(asset.orientation)),
        "has_audio": bool(asset.has_audio),
        "fps": float(asset.fps or 0.0),
        "width": int(asset.width or 0),
        "height": int(asset.height or 0),
        "bitrate": bitrate,
        "source_path": str(asset.path.resolve()),
        "original_source_path": str(clip.metadata.get("original_source_path") or asset.path.resolve()),
        "used_proxy_for_analysis": bool(clip.metadata.get("used_proxy_for_analysis")),
    }


def _scene_detector_metadata(asset: Asset, clip: Clip, segmenter_name: str) -> dict[str, Any]:
    return {
        "segmenter": segmenter_name,
        "fallback_fixed_interval": segmenter_name == "fixed_interval",
        "scene_detected": bool(clip.metadata.get("scene_detected")),
        "scene_threshold": clip.metadata.get("scene_threshold"),
        "source_path": str(asset.path.resolve()),
    }


def _analysis_assets_from_proxy_manifest(assets: list[Asset], work_dir: Path) -> tuple[list[Asset], int]:
    manifest = load_proxy_manifest(work_dir)
    entries = dict(manifest.get("entries") or {})
    analysis_assets: list[Asset] = []
    used_proxy_count = 0
    for asset in assets:
        entry = dict(entries.get(asset.asset_id) or {})
        proxy_path_value = str(entry.get("proxy_path") or "")
        if asset.media_type == MediaType.VIDEO and entry.get("status") == PROXY_READY and proxy_path_value:
            proxy_path = (work_dir / proxy_path_value).resolve()
            if proxy_path.exists():
                analysis_assets.append(
                    replace(
                        asset,
                        path=proxy_path,
                        metadata={
                            **dict(asset.metadata or {}),
                            "analysis_original_path": str(asset.path.resolve()),
                            "analysis_proxy_path": str(proxy_path),
                        },
                    )
                )
                used_proxy_count += 1
                continue
        analysis_assets.append(asset)
    return analysis_assets, used_proxy_count


def _extract_keyframe(source_path: Path, keyframe_path: Path, midpoint_ms: int, ffmpeg_path: str) -> None:
    keyframe_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path,
        "-y",
        "-ss",
        f"{max(0, midpoint_ms) / 1000:.3f}",
        "-i",
        str(source_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(keyframe_path),
    ]
    subprocess.run(command, capture_output=True, check=True)


def _extract_preview_clip(source_path: Path, preview_path: Path, start_ms: int, end_ms: int, ffmpeg_path: str) -> None:
    duration_ms = max(0, end_ms - start_ms)
    if duration_ms <= 0:
        raise ValueError(f"Preview duration must be positive: {preview_path}")
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    clip = Clip(
        clip_id=f"preview_{preview_path.stem}",
        project_id="preview",
        asset_id="preview",
        source_path=source_path,
        source_start_ms=int(start_ms),
        source_end_ms=int(end_ms),
        segmenter=FixedIntervalSegmenter.name,
        working_path=preview_path,
    )
    command = build_ffmpeg_cut_command(clip, ffmpeg_path=ffmpeg_path)
    subprocess.run(command, capture_output=True, check=True)


def analyze_project_scenes(
    work_dir: Path,
    *,
    ffprobe_path: str = "ffprobe",
    ffmpeg_path: str = "ffmpeg",
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
    analysis_assets, used_proxy_count = _analysis_assets_from_proxy_manifest(assets, resolved_work_dir)
    video_assets = [asset for asset in analysis_assets if asset.media_type == MediaType.VIDEO]
    if not video_assets:
        raise ValueError("No video assets are available for scene analysis.")

    segmenters = []
    if prefer_pyscenedetect or used_proxy_count > 0:
        segmenters.append(
            PySceneDetectSegmenter(
                scenedetect_path,
                ffmpeg_path=ffmpeg_path,
                min_scene_ms=min_scene_ms,
                max_clips_per_asset=max_clips_per_asset,
            )
        )
    segmenters.append(FixedIntervalSegmenter(clip_ms=max(min_scene_ms, fixed_clip_ms), max_clips_per_asset=max_clips_per_asset))

    clips = plan_segments_for_assets(video_assets, resolved_work_dir / "analysis_runs", segmenters=segmenters)
    for clip in clips:
        original_asset = asset_lookup.get(clip.asset_id)
        if original_asset is None:
            continue
        clip.metadata["original_source_path"] = str(original_asset.path.resolve())
        clip.metadata["used_proxy_for_analysis"] = str(clip.source_path.resolve()) != str(original_asset.path.resolve())
    clips = score_clips(clips, assets)
    analysis_run_id = f"analysis_{uuid4().hex}"
    created_at = _utc_now()
    store = VideoMixFoundationStore(resolved_work_dir)

    store.upsert_analysis_run(
        project_id=project.project_id,
        analysis_run_id=analysis_run_id,
        algorithm_name=ANALYSIS_ALGORITHM_NAME,
        algorithm_version=ANALYSIS_ALGORITHM_VERSION,
        source_kind="proxy" if used_proxy_count > 0 else "original",
        settings_json={
            "min_scene_ms": min_scene_ms,
            "fixed_clip_ms": fixed_clip_ms,
            "max_clips_per_asset": max_clips_per_asset,
            "prefer_pyscenedetect": prefer_pyscenedetect or used_proxy_count > 0,
            "scenedetect_path": scenedetect_path,
            "ffmpeg_path": ffmpeg_path,
            "used_proxy_count": used_proxy_count,
        },
        status="completed",
        created_at=created_at,
        completed_at=created_at,
        error="",
    )

    scene_rows: list[dict[str, Any]] = []
    scene_manifest_path = resolved_work_dir / "reports" / "scene_manifest.json"
    keyframes_dir = resolved_work_dir / "reports" / "scene_keyframes"
    previews_dir = resolved_work_dir / "reports" / "scene_previews"
    keyframes_dir.mkdir(parents=True, exist_ok=True)
    previews_dir.mkdir(parents=True, exist_ok=True)

    for index, clip in enumerate(clips, start=1):
        asset = _asset_from_clip(asset_lookup, clip)
        detector_metadata = _scene_detector_metadata(asset, clip, clip.segmenter.value)
        keyframe_path = keyframes_dir / f"{clip.clip_id}.jpg"
        preview_path = previews_dir / f"{clip.clip_id}.mp4"
        midpoint_ms = int(clip.source_start_ms + (clip.duration_ms / 2))
        _extract_keyframe(asset.path, keyframe_path, midpoint_ms, ffmpeg_path)
        _extract_preview_clip(asset.path, preview_path, clip.source_start_ms, clip.source_end_ms, ffmpeg_path)
        scene_id = f"{analysis_run_id}_scene_{index:04d}"
        row = {
            "scene_id": scene_id,
            "asset_id": asset.asset_id,
            "analysis_run_id": analysis_run_id,
            "start_ms": int(clip.source_start_ms),
            "end_ms": int(clip.source_end_ms),
            "duration_ms": int(clip.duration_ms),
            "keyframe_path": str(keyframe_path.relative_to(resolved_work_dir)).replace("\\", "/"),
            "preview_path": str(preview_path.relative_to(resolved_work_dir)).replace("\\", "/"),
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
    scene_manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
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
