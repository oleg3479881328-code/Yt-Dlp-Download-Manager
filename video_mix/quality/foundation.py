from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

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


def build_quality_report(
    *,
    work_dir: Path,
    project_id: str,
    plan: dict[str, Any],
    output_path: Path,
    ffprobe_path: str = "ffprobe",
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
        "timeline_gaps_detected": False,
        "timeline_overlaps_detected": False,
    }
    status = "qc_passed"
    if not findings["decodable"] or findings["width"] != 1080 or findings["height"] != 1920:
        status = "qc_failed"
    if requested_duration_ms and findings["duration_delta_ms"] > 1750:
        status = "qc_failed"
    if findings["proxy_used_as_source"]:
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
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "report_id": report_id,
        "status": status,
        "report_path": str(report_path.relative_to(resolved_work_dir)).replace("\\", "/"),
        "output_sha256": findings["output_sha256"],
        "findings": findings,
    }
