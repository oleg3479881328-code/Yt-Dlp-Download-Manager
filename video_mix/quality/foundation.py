from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from PIL import Image

from video_mix.core.data_model.foundation import QualityReportRecord, RenderProvenanceRecord
from video_mix.core.schemas import validate_schema_document
from video_mix.core.store import VideoMixFoundationStore

QUALITY_SCHEMA_VERSION = "quality-report/v1"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _ffprobe_payload(path: Path, ffprobe_path: str) -> dict[str, Any]:
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    return json.loads(completed.stdout)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _timeline_gap_overlap_flags(plan: dict[str, Any]) -> tuple[bool, bool]:
    items = sorted(
        [dict(item) for item in plan.get("items", [])],
        key=lambda item: int(item.get("timeline_start_ms") or 0),
    )
    gap_detected = False
    overlap_detected = False
    previous_end = 0
    for item in items:
        start_ms = int(item.get("timeline_start_ms") or 0)
        end_ms = int(item.get("timeline_end_ms") or 0)
        if start_ms > previous_end:
            gap_detected = True
        if start_ms < previous_end:
            overlap_detected = True
        previous_end = max(previous_end, end_ms)
    return gap_detected, overlap_detected


def _detect_black_segments(output_path: Path, ffmpeg_path: str) -> list[dict[str, float]]:
    command = [
        ffmpeg_path,
        "-hide_banner",
        "-i",
        str(output_path),
        "-vf",
        "blackdetect=d=0.20:pix_th=0.10",
        "-an",
        "-f",
        "null",
        "-",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    matches = re.findall(r"black_start:([0-9.]+)\s+black_end:([0-9.]+)\s+black_duration:([0-9.]+)", completed.stderr)
    return [
        {"start_s": float(start), "end_s": float(end), "duration_s": float(duration)}
        for start, end, duration in matches
    ]


def _detect_freeze_segments(output_path: Path, ffmpeg_path: str) -> list[dict[str, float]]:
    command = [
        ffmpeg_path,
        "-hide_banner",
        "-i",
        str(output_path),
        "-vf",
        "freezedetect=n=0.003:d=0.40",
        "-an",
        "-f",
        "null",
        "-",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    starts = [float(value) for value in re.findall(r"freeze_start: ([0-9.]+)", completed.stderr)]
    ends = [float(value) for value in re.findall(r"freeze_end: ([0-9.]+)", completed.stderr)]
    durations = [float(value) for value in re.findall(r"freeze_duration: ([0-9.]+)", completed.stderr)]
    segments: list[dict[str, float]] = []
    for index, start in enumerate(starts):
        end = ends[index] if index < len(ends) else start
        duration = durations[index] if index < len(durations) else max(0.0, end - start)
        segments.append({"start_s": start, "end_s": end, "duration_s": duration})
    return segments


def _average_hash(image_path: Path, *, size: int = 8) -> list[int]:
    with Image.open(image_path) as image:
        grayscale = image.convert("L").resize((size, size))
        pixels = list(grayscale.getdata())
    if not pixels:
        return [0] * (size * size)
    mean_value = sum(pixels) / len(pixels)
    return [1 if value >= mean_value else 0 for value in pixels]


def _hamming_distance(left: list[int], right: list[int]) -> int:
    limit = min(len(left), len(right))
    return sum(1 for index in range(limit) if left[index] != right[index]) + abs(len(left) - len(right))


def _detect_similar_segments(work_dir: Path, plan: dict[str, Any], *, threshold: int = 6) -> list[dict[str, Any]]:
    items = [dict(item) for item in plan.get("items", [])]
    hashes: list[tuple[int, str, list[int]]] = []
    for index, item in enumerate(items, start=1):
        metadata = dict(item.get("metadata_json") or {})
        keyframe_relative = str(metadata.get("keyframe_path") or "")
        if not keyframe_relative:
            continue
        keyframe_path = (work_dir / keyframe_relative).resolve()
        if not keyframe_path.exists():
            continue
        try:
            hashes.append((index, keyframe_relative, _average_hash(keyframe_path)))
        except OSError:
            continue
    similar_pairs: list[dict[str, Any]] = []
    for left_index in range(len(hashes)):
        left_position, left_keyframe, left_hash = hashes[left_index]
        for right_position, right_keyframe, right_hash in hashes[left_index + 1 :]:
            distance = _hamming_distance(left_hash, right_hash)
            if distance <= threshold:
                similar_pairs.append(
                    {
                        "left_position": left_position,
                        "right_position": right_position,
                        "left_keyframe_path": left_keyframe,
                        "right_keyframe_path": right_keyframe,
                        "hash_distance": distance,
                    }
                )
    return similar_pairs


def build_quality_report(
    *,
    work_dir: Path,
    project_id: str,
    plan: dict[str, Any],
    output_path: Path,
    ffprobe_path: str = "ffprobe",
    ffmpeg_path: str = "ffmpeg",
    renderer_version: str = "quick-mix-renderer-v1",
) -> dict[str, Any]:
    resolved_work_dir = work_dir.expanduser().resolve()
    absolute_output = output_path.expanduser().resolve()
    if not absolute_output.exists():
        raise FileNotFoundError(f"Rendered output does not exist: {absolute_output}")
    payload = _ffprobe_payload(absolute_output, ffprobe_path)
    streams = payload.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    fmt = payload.get("format", {})
    duration_ms = int(float(fmt.get("duration") or 0) * 1000) if fmt.get("duration") else 0
    requested_duration_ms = int(plan.get("requested_duration_ms") or 0)
    timeline_gaps_detected, timeline_overlaps_detected = _timeline_gap_overlap_flags(plan)
    black_segments = _detect_black_segments(absolute_output, ffmpeg_path)
    freeze_segments = _detect_freeze_segments(absolute_output, ffmpeg_path)
    similar_segments = _detect_similar_segments(resolved_work_dir, plan)
    source_asset_ids = [str(item.get("asset_id") or "") for item in plan.get("items", [])]
    duplicate_source_asset_count = max(0, len(source_asset_ids) - len(set(source_asset_ids)))
    findings = {
        "exists": absolute_output.exists(),
        "decodable": bool(video_stream),
        "duration_ms": duration_ms,
        "requested_duration_ms": requested_duration_ms,
        "duration_delta_ms": abs(duration_ms - requested_duration_ms) if requested_duration_ms else 0,
        "width": int((video_stream or {}).get("width") or 0),
        "height": int((video_stream or {}).get("height") or 0),
        "has_audio": bool(audio_stream),
        "output_sha256": _sha256_file(absolute_output),
        "proxy_used_as_source": any(
            "proxy" in str((item.get("metadata_json") or {}).get("source_path") or "").lower()
            for item in plan.get("items", [])
        ),
        "timeline_gaps_detected": timeline_gaps_detected,
        "timeline_overlaps_detected": timeline_overlaps_detected,
        "black_segment_count": len(black_segments),
        "black_segments": black_segments,
        "freeze_segment_count": len(freeze_segments),
        "freeze_segments": freeze_segments,
        "similar_segment_count": len(similar_segments),
        "similar_segments": similar_segments,
        "duplicate_source_asset_count": duplicate_source_asset_count,
    }
    status = "qc_passed"
    if not findings["decodable"] or findings["width"] != 1080 or findings["height"] != 1920:
        status = "qc_failed"
    if requested_duration_ms and findings["duration_delta_ms"] > 1750:
        status = "qc_failed"
    if findings["proxy_used_as_source"]:
        status = "qc_failed"
    if findings["timeline_gaps_detected"] or findings["timeline_overlaps_detected"]:
        status = "qc_failed"
    if findings["black_segment_count"] or findings["freeze_segment_count"]:
        status = "qc_failed"
    if findings["similar_segment_count"]:
        status = "qc_failed"

    report_payload = {
        "schema_version": QUALITY_SCHEMA_VERSION,
        "plan_id": plan["plan_id"],
        "status": status,
        "findings": findings,
        "ffprobe": payload,
    }
    validate_schema_document("quality_report", report_payload)

    store = VideoMixFoundationStore(resolved_work_dir)
    report_id = f"quality_{uuid4().hex}"
    created_at = _utc_now()
    record = QualityReportRecord(
        report_id=report_id,
        project_id=project_id,
        plan_id=plan["plan_id"],
        output_path=str(absolute_output.relative_to(resolved_work_dir)).replace("\\", "/"),
        status=status,
        findings_json=report_payload,
        schema_version=QUALITY_SCHEMA_VERSION,
        created_at=created_at,
    )
    store.upsert_quality_report(**record.model_dump())
    provenance = RenderProvenanceRecord(
        provenance_id=f"prov_{uuid4().hex}",
        project_id=project_id,
        plan_id=plan["plan_id"],
        renderer_version=renderer_version,
        output_path=str(absolute_output.relative_to(resolved_work_dir)).replace("\\", "/"),
        output_sha256=findings["output_sha256"],
        source_asset_ids=[item["asset_id"] for item in plan.get("items", [])],
        source_ranges=[
            {
                "asset_id": item["asset_id"],
                "start_ms": item["source_start_ms"],
                "end_ms": item["source_end_ms"],
            }
            for item in plan.get("items", [])
        ],
        settings_json={"requested_duration_ms": requested_duration_ms},
        qc_status=status,
        review_status="draft",
        created_at=created_at,
    )
    provenance_payload = provenance.model_dump()
    store.upsert_render_provenance(
        provenance_id=provenance_payload["provenance_id"],
        project_id=provenance_payload["project_id"],
        plan_id=provenance_payload["plan_id"],
        renderer_version=provenance_payload["renderer_version"],
        output_path=provenance_payload["output_path"],
        output_sha256=provenance_payload["output_sha256"],
        source_asset_ids_json=provenance_payload["source_asset_ids"],
        source_ranges_json=provenance_payload["source_ranges"],
        settings_json=provenance_payload["settings_json"],
        qc_status=provenance_payload["qc_status"],
        review_status=provenance_payload["review_status"],
        created_at=provenance_payload["created_at"],
    )
    report_path = resolved_work_dir / "reports" / f"{plan['plan_id']}_quality_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "report_id": report_id,
        "status": status,
        "report_path": str(report_path.relative_to(resolved_work_dir)).replace("\\", "/"),
        "output_sha256": findings["output_sha256"],
        "findings": findings,
    }
