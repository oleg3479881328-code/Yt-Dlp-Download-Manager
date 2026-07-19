from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class FoundationBaseModel(BaseModel):
    model_config = {"extra": "forbid"}


class ProjectRecord(FoundationBaseModel):
    project_id: str
    work_dir: str
    source_root: str
    name: str
    industry_pack: str = "wedding"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")


class ProjectAssetRecord(FoundationBaseModel):
    project_id: str
    asset_id: str
    original_path: str
    media_type: Literal["video", "photo"]
    duration_ms: int | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    orientation: str = "unknown"
    has_audio: bool = False
    probe_status: str = "pending"
    quality_score: float = 0.0
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")


class ProjectProxyRecord(FoundationBaseModel):
    project_id: str
    asset_id: str
    status: Literal["ready", "failed", "stale", "missing", "pending", "running"]
    proxy_path: str = ""
    source_fingerprint: str = ""
    profile_fingerprint: str = ""
    original_duration_ms: int = 0
    proxy_duration_ms: int = 0
    original_width: int = 0
    original_height: int = 0
    proxy_width: int = 0
    proxy_height: int = 0
    error: str = ""
    has_audio: bool = False
    created_at: str = ""
    updated_at: str = ""


class AnalysisRunRecord(FoundationBaseModel):
    project_id: str
    analysis_run_id: str
    algorithm_name: str
    algorithm_version: str
    source_kind: Literal["original", "proxy"] = "proxy"
    settings_json: dict[str, Any] = Field(default_factory=dict)
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")
    completed_at: str = ""
    error: str = ""


class SceneRecord(FoundationBaseModel):
    project_id: str
    analysis_run_id: str
    scene_id: str
    asset_id: str
    start_ms: int
    end_ms: int
    duration_ms: int
    keyframe_path: str = ""
    score_json: dict[str, Any] = Field(default_factory=dict)
    detector_json: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "scene-manifest/v1"


class EditPlanItemRecord(FoundationBaseModel):
    scene_id: str = ""
    asset_id: str
    source_start_ms: int
    source_end_ms: int
    timeline_start_ms: int
    timeline_end_ms: int
    role: Literal["opening", "body", "closing"] = "body"
    source_type: Literal["video", "photo"] = "video"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class EditPlanRecord(FoundationBaseModel):
    project_id: str
    plan_id: str
    analysis_run_id: str = ""
    generation_id: str
    requested_duration_ms: int
    actual_duration_ms: int
    output_index: int
    seed: int
    status: Literal["draft", "rendered", "qc_passed", "qc_failed", "approved", "rejected"] = "draft"
    warnings: list[str] = Field(default_factory=list)
    provenance_key: str = ""
    schema_version: str = "edit-plan/v1"
    items: list[EditPlanItemRecord] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")


class JobRecord(FoundationBaseModel):
    job_id: str
    project_id: str
    job_type: str
    status: Literal["queued", "running", "completed", "failed", "cancelled", "retry_wait"] = "queued"
    payload_json: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str
    attempt_count: int = 0
    max_attempts: int = 3
    lease_owner: str = ""
    lease_expires_at: str = ""
    heartbeat_at: str = ""
    progress: float = 0.0
    cancel_requested: bool = False
    error: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")
    started_at: str = ""
    finished_at: str = ""


class EventRecord(FoundationBaseModel):
    project_id: str
    event_id: str
    entity_type: str
    entity_id: str
    event_type: str
    payload_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")


class QualityReportRecord(FoundationBaseModel):
    project_id: str
    report_id: str
    plan_id: str
    output_path: str
    status: Literal["draft", "rendered", "qc_passed", "qc_failed"] = "draft"
    findings_json: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "quality-report/v1"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")


class RenderProvenanceRecord(FoundationBaseModel):
    project_id: str
    provenance_id: str
    plan_id: str
    renderer_version: str
    output_path: str
    output_sha256: str = ""
    source_asset_ids: list[str] = Field(default_factory=list)
    source_ranges: list[dict[str, Any]] = Field(default_factory=list)
    settings_json: dict[str, Any] = Field(default_factory=dict)
    qc_status: str = ""
    review_status: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")
