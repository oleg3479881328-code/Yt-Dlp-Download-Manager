from __future__ import annotations

import asyncio
import json
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from posixpath import normpath
from typing import Annotated, Any
from urllib.parse import unquote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from video_mix.core.asset_scan import detect_media_type
from video_mix.core.models import CandidateStatus
from video_mix.core.zip_intake import import_video_mix_zip, stage_upload_file
from video_mix.foundation_runtime import ProductionRunRequest, production_run_manager
from video_mix.service import (
    estimate_quick_mix_capacity,
    plan_source_materials,
    quick_mix_source_materials,
    scan_source_materials,
)

from .path_safety import MissingPathError, UnsafePathError, resolve_existing_output_path
from .segment_utils import SegmentValidationError, normalize_segment_payload
from .storage import Storage
from .video_mix_dashboard import (
    add_external_project_materials,
    add_project_files,
    add_project_materials_episode,
    assign_project_material,
    build_project_files_payload,
    build_project_materials_payload,
    build_video_proxies_payload,
    bulk_update_candidate_status,
    cancel_video_proxy_job,
    cleanup_video_proxy_partials,
    create_missing_video_proxies,
    delete_video_proxy,
    export_approved_candidates,
    open_dashboard_target,
    pick_dashboard_work_dir,
    pick_source_materials_dir,
    pick_source_media_file,
    rebuild_single_video_proxy,
    rebuild_stale_video_proxies,
    remove_project_file,
    reorder_project_material_takes,
    resolve_relative_work_path,
    retry_failed_video_proxies,
    unassign_project_material,
    update_project_material_take,
)
from .video_mix_dashboard import (
    build_dashboard_payload as build_video_mix_dashboard_payload,
)
from .video_mix_dashboard import (
    update_candidate_status as update_video_mix_candidate_status,
)
from .worker import DownloadWorker
from .yt_service import analyze_url, utc_now

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"

storage = Storage(DB_PATH)
worker = DownloadWorker(storage, BASE_DIR)


class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=3)


class QueueRequest(BaseModel):
    url: str
    mode: str = "video"
    quality: str = "bestvideo*+bestaudio/best"
    segment_start: str | float | None = None
    segment_end: str | float | None = None
    segment_duration: str | float | None = None
    segment_label: str | None = None


class SettingsRequest(BaseModel):
    output_directory: str
    default_mode: str
    quality: str
    retry_enabled: bool
    retry_count: int
    auth_mode: str = "none"
    cookies_browser: str = "chrome"
    cookies_browser_profile: str = ""
    cookies_file: str = ""


class VideoMixCandidateRequest(BaseModel):
    work_dir: str
    note: str = ""


class VideoMixExportRequest(BaseModel):
    work_dir: str
    ffmpeg: str = "ffmpeg"


class VideoMixBulkRequest(BaseModel):
    work_dir: str
    candidate_ids: list[str]
    note: str = ""


class VideoMixOpenRequest(BaseModel):
    work_dir: str
    target: str


class VideoMixPickWorkDirRequest(BaseModel):
    initial_dir: str = ""


class VideoMixPickSourceRequest(BaseModel):
    initial_dir: str = ""


class VideoMixPickFileRequest(BaseModel):
    initial_dir: str = ""
    title: str = "Select file"


class VideoMixOpenLocalFileRequest(BaseModel):
    file_path: str


class VideoMixOpenLocalPathRequest(BaseModel):
    path: str


class VideoMixSourceScanRequest(BaseModel):
    source_dir: str


class VideoMixSourcePlanRequest(BaseModel):
    source_dir: str
    project_name: str = ""
    pack: str = "wedding"
    work_dir: str = ""
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    scenedetect: str = "scenedetect"
    prefer_pyscenedetect: bool = False
    clip_ms: int = 3000
    max_clips_per_asset: int = 12
    max_candidates: int = 10


class VideoMixZipImportPathRequest(BaseModel):
    zip_path: str
    project_name: str = ""
    work_dir: str = ""
    ffprobe: str = "ffprobe"
    ffmpeg: str = "ffmpeg"


class VideoMixQuickMixRequest(BaseModel):
    source_dir: str
    duration_seconds: float = Field(gt=0)
    output_count: int = Field(gt=0)
    episode_duration_min_seconds: float = Field(default=1.5, gt=0)
    episode_duration_max_seconds: float = Field(default=2.0, gt=0)
    project_name: str = ""
    pack: str = "wedding"
    work_dir: str = ""
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    music_path: str = ""
    music_paths: list[str] = Field(default_factory=list)
    use_music_duration: bool = False
    opening_media_path: str = ""
    opening_media_paths: list[str] = Field(default_factory=list)
    closing_media_path: str = ""
    closing_media_paths: list[str] = Field(default_factory=list)
    use_closing_duration: bool = False


class VideoMixQuickMixEstimateRequest(BaseModel):
    source_dir: str
    duration_seconds: float = Field(gt=0)
    episode_duration_min_seconds: float = Field(default=1.5, gt=0)
    episode_duration_max_seconds: float = Field(default=2.0, gt=0)
    ffprobe: str = "ffprobe"
    music_path: str = ""
    music_paths: list[str] = Field(default_factory=list)
    use_music_duration: bool = False
    opening_media_path: str = ""
    opening_media_paths: list[str] = Field(default_factory=list)
    closing_media_path: str = ""
    closing_media_paths: list[str] = Field(default_factory=list)
    use_closing_duration: bool = False


class VideoMixProjectFilesRequest(BaseModel):
    work_dir: str
    file_paths: list[str] = Field(default_factory=list)


class VideoMixProjectFileRemoveRequest(BaseModel):
    work_dir: str
    relative_path: str


class VideoMixProjectMaterialsEpisodeRequest(BaseModel):
    work_dir: str
    label: str = ""


class VideoMixProjectMaterialAssignRequest(BaseModel):
    work_dir: str
    asset_id: str
    episode_id: str
    reuse: bool = False


class VideoMixProjectMaterialUnassignRequest(BaseModel):
    work_dir: str
    episode_id: str
    take_id: str


class VideoMixProjectMaterialExternalDropRequest(BaseModel):
    work_dir: str
    episode_id: str
    file_paths: list[str] = Field(default_factory=list)


class VideoMixProjectMaterialTakeUpdateRequest(BaseModel):
    work_dir: str
    episode_id: str
    take_id: str
    take_type: str = ""
    source_start_ms: int | None = Field(default=None, ge=0)
    source_end_ms: int | None = Field(default=None, gt=0)
    video_asset_id: str = ""
    photo_asset_ids: list[str] = Field(default_factory=list)
    photo_duration_ms: int | None = Field(default=None, ge=100)
    photo_motion_mode: str = ""


class VideoMixProjectMaterialTakeReorderRequest(BaseModel):
    work_dir: str
    episode_id: str
    ordered_take_ids: list[str] = Field(default_factory=list)


class VideoMixProxyQueueRequest(BaseModel):
    work_dir: str
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"


class VideoMixProxyAssetRequest(BaseModel):
    work_dir: str
    asset_id: str
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"


class VideoMixProductionRunRequest(BaseModel):
    source_dir: str
    work_dir: str = ""
    project_name: str = ""
    count: int = Field(default=5, gt=0)
    duration_seconds: float = Field(default=15.0, gt=0)
    episode_duration_min_seconds: float = Field(default=1.5, gt=0)
    episode_duration_max_seconds: float = Field(default=2.0, gt=0)
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    music_path: str = ""
    music_paths: list[str] = Field(default_factory=list)
    use_music_duration: bool = False
    opening_media_path: str = ""
    opening_media_paths: list[str] = Field(default_factory=list)
    closing_media_path: str = ""
    closing_media_paths: list[str] = Field(default_factory=list)
    use_closing_duration: bool = False
    pack: str = "wedding"


class VideoMixProductionRunStatusRequest(BaseModel):
    work_dir: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    worker.start()
    production_run_manager.recover()
    yield


app = FastAPI(title="yt-dlp Download Manager", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")

SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


def resolve_local_preview_media_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser().resolve()
    if not candidate.exists():
        raise HTTPException(status_code=404, detail=f"Selected media does not exist: {candidate}")
    if not candidate.is_file():
        raise HTTPException(status_code=400, detail=f"Selected media path is not a file: {candidate}")
    if detect_media_type(candidate) is None and candidate.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Selected media type is not supported for preview: {candidate}")
    return candidate


def build_state_payload(history_status: str = "all", selected_job_id: str | None = None) -> dict[str, Any]:
    queue = storage.get_queue()
    snapshot = storage.get_dashboard_snapshot()
    active = [job for job in queue if job["status"] in {"downloading", "post_processing"}]
    queued = [job for job in queue if job["status"] in {"queued", "ready"}]
    worker_state = "active" if active else ("queued" if queued else "idle")
    return {
        "dashboard": {
            "active_jobs": queue[:5],
            "queue_preview": queued[:5],
            "queue_size": len(queued),
            "worker_state": worker_state,
            "errors_count": snapshot["errors_count"],
        },
        "queue": queue,
        "history": storage.get_history(history_status),
        "selected_job": storage.get_job(selected_job_id) if selected_job_id else None,
    }


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse((BASE_DIR / "app" / "templates" / "index.html").read_text(encoding="utf-8"))


@app.get("/video-mix", response_class=HTMLResponse)
async def video_mix_dashboard_page() -> HTMLResponse:
    return HTMLResponse((BASE_DIR / "app" / "templates" / "video_mix_dashboard.html").read_text(encoding="utf-8"))


@app.post("/api/analyze")
async def analyze(payload: AnalyzeRequest) -> dict[str, Any]:
    try:
        return {"ok": True, "analysis": analyze_url(payload.url, auth=storage.get_settings())}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/jobs")
async def create_job(payload: QueueRequest) -> dict[str, Any]:
    segment = None
    has_segment_fields = any(
        value not in {None, ""}
        for value in (payload.segment_start, payload.segment_end, payload.segment_duration, payload.segment_label)
    )
    if has_segment_fields:
        try:
            segment_range = normalize_segment_payload(
                {
                    "start": payload.segment_start,
                    "end": payload.segment_end,
                    "duration": payload.segment_duration,
                    "label": payload.segment_label,
                }
            )
        except SegmentValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        segment = segment_range.to_metadata()

    try:
        analysis = analyze_url(payload.url, auth=storage.get_settings())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if segment and analysis["type"] != "single":
        raise HTTPException(status_code=400, detail="Segment download currently supports single videos only")

    job_id = str(uuid.uuid4())
    queue_count = len(storage.list_jobs(("queued", "ready")))
    analysis_json = {**analysis, "segment": segment} if segment else analysis
    job = {
        "id": job_id,
        "url": payload.url,
        "type": analysis["type"],
        "title": analysis["title"],
        "status": "queued",
        "stage": "Queued",
        "progress": 0,
        "speed": None,
        "eta": None,
        "created_at": utc_now(),
        "started_at": None,
        "finished_at": None,
        "error": None,
        "output_path": None,
        "item_total": analysis["item_count"],
        "item_completed": 0,
        "item_failed": 0,
        "current_item_id": None,
        "current_item_index": 0,
        "analysis_json": analysis_json,
        "mode": payload.mode,
        "quality": payload.quality,
        "queue_position": queue_count + 1,
    }
    items = [
        {
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "item_index": entry["index"] - 1,
            "title": entry["title"],
            "url": entry["url"],
            "status": "pending",
            "progress": 0,
            "speed": None,
            "eta": None,
            "error": None,
            "output_path": None,
        }
        for entry in analysis.get("entries", [])
        if entry.get("url")
    ]
    storage.create_job(job, items)
    storage.add_log(job_id, "Segment job added to queue" if segment else "Job added to queue", utc_now())
    storage.refresh_queue_positions()
    return {"ok": True, "job": storage.get_job(job_id)}


@app.get("/api/dashboard")
async def dashboard() -> dict[str, Any]:
    return build_state_payload()["dashboard"]


@app.get("/api/queue")
async def queue() -> dict[str, Any]:
    return {"jobs": storage.get_queue()}


@app.get("/api/history")
async def history(status: str = "all") -> dict[str, Any]:
    return {"jobs": storage.get_history(status)}


@app.get("/api/jobs/{job_id}")
async def job_details(job_id: str) -> dict[str, Any]:
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": job}


@app.post("/api/jobs/{job_id}/retry")
async def retry_job(job_id: str) -> dict[str, Any]:
    if not storage.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    worker.retry_job(job_id)
    return {"ok": True}


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict[str, Any]:
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    storage.update_job(job_id, status="canceled", stage="Cancel requested", error="Canceled by user")
    storage.add_log(job_id, "Cancel requested", utc_now())
    storage.refresh_queue_positions()
    return {"ok": True}


@app.delete("/api/jobs/{job_id}")
async def remove_job(job_id: str) -> dict[str, Any]:
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] in {"downloading", "post_processing"}:
        raise HTTPException(status_code=400, detail="Cannot remove active job")
    with storage.lock, storage.connect() as connection:
        connection.execute("DELETE FROM logs WHERE job_id = ?", (job_id,))
        connection.execute("DELETE FROM playlist_items WHERE job_id = ?", (job_id,))
        connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    storage.refresh_queue_positions()
    return {"ok": True}


@app.get("/api/settings")
async def get_settings() -> dict[str, Any]:
    return storage.get_settings()


@app.post("/api/settings")
async def save_settings(payload: SettingsRequest) -> dict[str, Any]:
    return {"ok": True, "settings": storage.update_settings(payload.model_dump())}


@app.get("/api/video-mix/dashboard")
async def video_mix_dashboard(work_dir: str) -> dict[str, Any]:
    return build_video_mix_dashboard_payload(work_dir)


@app.get("/api/video-mix/project-files")
async def video_mix_project_files(work_dir: str) -> dict[str, Any]:
    return build_project_files_payload(work_dir)


@app.post("/api/video-mix/project-files/add")
async def video_mix_add_project_files(payload: VideoMixProjectFilesRequest) -> dict[str, Any]:
    return add_project_files(payload.work_dir, payload.file_paths)


@app.post("/api/video-mix/project-files/remove")
async def video_mix_remove_project_file(payload: VideoMixProjectFileRemoveRequest) -> dict[str, Any]:
    return remove_project_file(payload.work_dir, payload.relative_path)


@app.get("/api/video-mix/project-materials")
async def video_mix_project_materials(work_dir: str) -> dict[str, Any]:
    return build_project_materials_payload(work_dir)


@app.post("/api/video-mix/project-materials/episodes")
async def create_video_mix_project_materials_episode(payload: VideoMixProjectMaterialsEpisodeRequest) -> dict[str, Any]:
    dashboard = add_project_materials_episode(payload.work_dir, payload.label)
    return {"ok": True, "dashboard": dashboard}


@app.post("/api/video-mix/project-materials/assign")
async def assign_video_mix_project_material(payload: VideoMixProjectMaterialAssignRequest) -> dict[str, Any]:
    dashboard = assign_project_material(payload.work_dir, payload.asset_id, payload.episode_id, reuse=payload.reuse)
    return {"ok": True, "dashboard": dashboard}


@app.post("/api/video-mix/project-materials/unassign")
async def unassign_video_mix_project_material(payload: VideoMixProjectMaterialUnassignRequest) -> dict[str, Any]:
    dashboard = unassign_project_material(payload.work_dir, payload.episode_id, payload.take_id)
    return {"ok": True, "dashboard": dashboard}


@app.post("/api/video-mix/project-materials/external-drop")
async def drop_and_assign_video_mix_project_materials(payload: VideoMixProjectMaterialExternalDropRequest) -> dict[str, Any]:
    dashboard = add_external_project_materials(payload.work_dir, payload.episode_id, payload.file_paths)
    return {"ok": True, "dashboard": dashboard}


@app.post("/api/video-mix/project-materials/takes/update")
async def update_video_mix_project_material_take(payload: VideoMixProjectMaterialTakeUpdateRequest) -> dict[str, Any]:
    dashboard = update_project_material_take(
        payload.work_dir,
        payload.episode_id,
        payload.take_id,
        payload.source_start_ms,
        payload.source_end_ms,
        take_type=payload.take_type,
        video_asset_id=payload.video_asset_id,
        photo_asset_ids=payload.photo_asset_ids,
        photo_duration_ms=payload.photo_duration_ms,
        photo_motion_mode=payload.photo_motion_mode,
    )
    return {"ok": True, "dashboard": dashboard}


@app.post("/api/video-mix/project-materials/takes/reorder")
async def reorder_video_mix_project_material_takes(payload: VideoMixProjectMaterialTakeReorderRequest) -> dict[str, Any]:
    dashboard = reorder_project_material_takes(payload.work_dir, payload.episode_id, payload.ordered_take_ids)
    return {"ok": True, "dashboard": dashboard}


@app.get("/api/video-mix/proxies")
async def video_mix_video_proxies(work_dir: str, ffprobe: str = "ffprobe") -> dict[str, Any]:
    return build_video_proxies_payload(work_dir, ffprobe_path=ffprobe)


@app.post("/api/video-mix/proxies/create-missing")
async def video_mix_create_missing_proxies(payload: VideoMixProxyQueueRequest) -> dict[str, Any]:
    return {
        "ok": True,
        "video_proxies": create_missing_video_proxies(payload.work_dir, ffmpeg_path=payload.ffmpeg, ffprobe_path=payload.ffprobe),
    }


@app.post("/api/video-mix/proxies/rebuild-stale")
async def video_mix_rebuild_stale_proxies(payload: VideoMixProxyQueueRequest) -> dict[str, Any]:
    return {
        "ok": True,
        "video_proxies": rebuild_stale_video_proxies(payload.work_dir, ffmpeg_path=payload.ffmpeg, ffprobe_path=payload.ffprobe),
    }


@app.post("/api/video-mix/proxies/retry-failed")
async def video_mix_retry_failed_proxies(payload: VideoMixProxyQueueRequest) -> dict[str, Any]:
    return {
        "ok": True,
        "video_proxies": retry_failed_video_proxies(payload.work_dir, ffmpeg_path=payload.ffmpeg, ffprobe_path=payload.ffprobe),
    }


@app.post("/api/video-mix/proxies/rebuild-one")
async def video_mix_rebuild_one_proxy(payload: VideoMixProxyAssetRequest) -> dict[str, Any]:
    return {
        "ok": True,
        "video_proxies": rebuild_single_video_proxy(
            payload.work_dir,
            payload.asset_id,
            ffmpeg_path=payload.ffmpeg,
            ffprobe_path=payload.ffprobe,
        ),
    }


@app.post("/api/video-mix/proxies/cancel")
async def video_mix_cancel_proxy_job(payload: VideoMixProxyAssetRequest) -> dict[str, Any]:
    return {"ok": True, "video_proxies": cancel_video_proxy_job(payload.work_dir, payload.asset_id)}


@app.post("/api/video-mix/proxies/delete")
async def video_mix_delete_proxy(payload: VideoMixProxyAssetRequest) -> dict[str, Any]:
    return {"ok": True, "video_proxies": delete_video_proxy(payload.work_dir, payload.asset_id)}


@app.post("/api/video-mix/proxies/cleanup")
async def video_mix_cleanup_proxy_partials(payload: VideoMixProxyQueueRequest) -> dict[str, Any]:
    return {"ok": True, **cleanup_video_proxy_partials(payload.work_dir)}


@app.post("/api/video-mix/production-runs")
async def create_video_mix_production_run(payload: VideoMixProductionRunRequest) -> dict[str, Any]:
    request = ProductionRunRequest(
        source_dir=payload.source_dir,
        work_dir=payload.work_dir,
        project_name=payload.project_name,
        count=payload.count,
        duration_seconds=payload.duration_seconds,
        episode_duration_min_seconds=payload.episode_duration_min_seconds,
        episode_duration_max_seconds=payload.episode_duration_max_seconds,
        ffmpeg=payload.ffmpeg,
        ffprobe=payload.ffprobe,
        music_paths=payload.music_paths or ([payload.music_path] if payload.music_path else []),
        use_music_duration=payload.use_music_duration,
        opening_media_paths=payload.opening_media_paths or ([payload.opening_media_path] if payload.opening_media_path else []),
        closing_media_paths=payload.closing_media_paths or ([payload.closing_media_path] if payload.closing_media_path else []),
        use_closing_duration=payload.use_closing_duration,
        pack=payload.pack,
    )
    result = production_run_manager.start(request)
    return {
        "ok": True,
        **result,
        "status": production_run_manager.get_status(result["work_dir"], result["run_id"]),
        "dashboard": build_video_mix_dashboard_payload(result["work_dir"]),
    }


@app.get("/api/video-mix/production-runs/{run_id}")
async def get_video_mix_production_run(run_id: str, work_dir: str) -> dict[str, Any]:
    try:
        status = production_run_manager.get_status(work_dir, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "status": status}


@app.post("/api/video-mix/production-runs/{run_id}/cancel")
async def cancel_video_mix_production_run(run_id: str, payload: VideoMixProductionRunStatusRequest) -> dict[str, Any]:
    try:
        status = production_run_manager.cancel(payload.work_dir, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "status": status, "dashboard": build_video_mix_dashboard_payload(payload.work_dir)}


@app.post("/api/video-mix/production-runs/{run_id}/retry")
async def retry_video_mix_production_run(run_id: str, payload: VideoMixProductionRunStatusRequest) -> dict[str, Any]:
    try:
        status = production_run_manager.retry(payload.work_dir, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "status": status, "dashboard": build_video_mix_dashboard_payload(payload.work_dir)}


@app.get("/api/video-mix/production-runs/{run_id}/package")
async def get_video_mix_production_run_package(run_id: str, work_dir: str) -> dict[str, Any]:
    try:
        status = production_run_manager.get_status(work_dir, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    package = status.get("latest_package")
    if not package:
        raise HTTPException(status_code=404, detail=f"Publishing package not found yet for production run: {run_id}")
    return {"ok": True, "package": package}


@app.post("/api/video-mix/candidates/bulk/approve")
async def approve_video_mix_candidates_bulk(payload: VideoMixBulkRequest) -> dict[str, Any]:
    dashboard = bulk_update_candidate_status(payload.work_dir, payload.candidate_ids, CandidateStatus.APPROVED, payload.note)
    return {"ok": True, "dashboard": dashboard}


@app.post("/api/video-mix/candidates/bulk/reject")
async def reject_video_mix_candidates_bulk(payload: VideoMixBulkRequest) -> dict[str, Any]:
    dashboard = bulk_update_candidate_status(payload.work_dir, payload.candidate_ids, CandidateStatus.REJECTED, payload.note)
    return {"ok": True, "dashboard": dashboard}


@app.post("/api/video-mix/candidates/{candidate_id}/approve")
async def approve_video_mix_candidate(candidate_id: str, payload: VideoMixCandidateRequest) -> dict[str, Any]:
    dashboard = update_video_mix_candidate_status(payload.work_dir, candidate_id, CandidateStatus.APPROVED, payload.note)
    return {"ok": True, "dashboard": dashboard}


@app.post("/api/video-mix/candidates/{candidate_id}/reject")
async def reject_video_mix_candidate(candidate_id: str, payload: VideoMixCandidateRequest) -> dict[str, Any]:
    dashboard = update_video_mix_candidate_status(payload.work_dir, candidate_id, CandidateStatus.REJECTED, payload.note)
    return {"ok": True, "dashboard": dashboard}


@app.post("/api/video-mix/export")
async def export_video_mix(payload: VideoMixExportRequest) -> dict[str, Any]:
    return export_approved_candidates(payload.work_dir, ffmpeg_path=payload.ffmpeg)


@app.post("/api/video-mix/open")
async def open_video_mix_target(payload: VideoMixOpenRequest) -> dict[str, Any]:
    return open_dashboard_target(payload.work_dir, payload.target)


@app.post("/api/video-mix/pick-workdir")
async def pick_video_mix_work_dir(payload: VideoMixPickWorkDirRequest) -> dict[str, Any]:
    return pick_dashboard_work_dir(payload.initial_dir)


@app.post("/api/video-mix/pick-source-folder")
async def pick_video_mix_source_folder(payload: VideoMixPickSourceRequest) -> dict[str, Any]:
    return pick_source_materials_dir(payload.initial_dir)


@app.post("/api/video-mix/pick-file")
async def pick_video_mix_file(payload: VideoMixPickFileRequest) -> dict[str, Any]:
    return pick_source_media_file(payload.initial_dir, title=payload.title)


@app.post("/api/video-mix/upload-file")
async def upload_video_mix_file(request: Request) -> dict[str, Any]:
    purpose = request.headers.get("x-video-mix-upload-purpose", "generic")
    raw_filename = request.headers.get("x-video-mix-upload-filename") or "upload.bin"
    filename = Path(unquote(raw_filename)).name
    upload_session = request.headers.get("x-video-mix-upload-session", "").strip()
    relative_path = unquote(request.headers.get("x-video-mix-upload-relative-path", "").strip())
    suffix = Path(filename).suffix
    safe_purpose = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in purpose) or "generic"
    upload_root = Path(tempfile.gettempdir()) / "yt_dlp_video_mix_uploads" / safe_purpose
    upload_root.mkdir(parents=True, exist_ok=True)
    if upload_session:
        safe_session = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in upload_session) or uuid.uuid4().hex
        session_root = upload_root / safe_session
        session_root.mkdir(parents=True, exist_ok=True)
        normalized_relative = normpath(relative_path.replace("\\", "/")).lstrip("/")
        if normalized_relative in {".", ""}:
            normalized_relative = filename
        if normalized_relative.startswith("../") or normalized_relative == "..":
            raise HTTPException(status_code=400, detail="Dropped relative path is unsafe")
        stored_path = (session_root / normalized_relative).resolve()
        if session_root.resolve() not in stored_path.parents and stored_path != session_root.resolve():
            raise HTTPException(status_code=400, detail="Dropped relative path escapes the upload session root")
        stored_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        session_root = None
        stored_path = upload_root / f"{uuid.uuid4().hex}{suffix}"
    payload = await request.body()
    stored_path.write_bytes(payload)
    result = {
        "ok": True,
        "purpose": safe_purpose,
        "original_filename": filename,
        "file_path": str(stored_path.resolve()),
    }
    if session_root is not None:
        result["root_dir"] = str(session_root.resolve())
        result["relative_path"] = normalized_relative
        result["upload_session"] = safe_session
    return result


@app.get("/api/video-mix/local-media")
async def video_mix_local_media(file_path: str) -> FileResponse:
    path = resolve_local_preview_media_path(file_path)
    return FileResponse(path=path, filename=path.name)


@app.post("/api/video-mix/open-local-file")
async def video_mix_open_local_file(payload: VideoMixOpenLocalFileRequest) -> dict[str, Any]:
    path = resolve_local_preview_media_path(payload.file_path)
    os.startfile(str(path))
    return {"ok": True, "file_path": str(path)}


@app.post("/api/video-mix/open-local-path")
async def video_mix_open_local_path(payload: VideoMixOpenLocalPathRequest) -> dict[str, Any]:
    path = Path(payload.path).expanduser().resolve()
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Selected path does not exist: {path}")
    os.startfile(str(path))
    return {"ok": True, "path": str(path)}


@app.post("/api/video-mix/source/scan")
async def scan_video_mix_source(payload: VideoMixSourceScanRequest) -> dict[str, Any]:
    try:
        return {"ok": True, **scan_source_materials(payload.source_dir)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/video-mix/source/plan")
async def plan_video_mix_source(payload: VideoMixSourcePlanRequest) -> dict[str, Any]:
    try:
        result = plan_source_materials(
            payload.source_dir,
            project_name=payload.project_name or None,
            pack=payload.pack,
            work_dir=payload.work_dir or None,
            ffprobe_path=payload.ffprobe,
            ffmpeg_path=payload.ffmpeg,
            scenedetect_path=payload.scenedetect,
            prefer_pyscenedetect=payload.prefer_pyscenedetect,
            clip_ms=payload.clip_ms,
            max_clips_per_asset=payload.max_clips_per_asset,
            max_candidates=payload.max_candidates,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        **result,
        "dashboard": build_video_mix_dashboard_payload(result["work_dir"]),
    }


@app.post("/api/video-mix/import-zip")
async def import_video_mix_zip_archive(
    file: Annotated[UploadFile, File(...)],
    project_name: Annotated[str, Form()] = "",
    work_dir: Annotated[str, Form()] = "",
    ffprobe: Annotated[str, Form()] = "ffprobe",
    ffmpeg: Annotated[str, Form()] = "ffmpeg",
) -> dict[str, Any]:
    filename = Path(file.filename or "upload.zip").name
    if Path(filename).suffix.lower() != ".zip":
        raise HTTPException(status_code=400, detail="Uploaded file must be a ZIP archive.")
    staged_path = stage_upload_file(filename, await file.read())
    try:
        result = import_video_mix_zip(
            staged_path,
            project_name=project_name or None,
            work_dir=work_dir or None,
            ffprobe_path=ffprobe,
            ffmpeg_path=ffmpeg,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if staged_path.exists():
            staged_path.unlink(missing_ok=True)
    return {
        "ok": True,
        **result,
        "dashboard": build_video_mix_dashboard_payload(result["work_dir"]),
    }


@app.post("/api/video-mix/import-zip-path")
async def import_video_mix_zip_from_path(payload: VideoMixZipImportPathRequest) -> dict[str, Any]:
    try:
        result = import_video_mix_zip(
            payload.zip_path,
            project_name=payload.project_name or None,
            work_dir=payload.work_dir or None,
            ffprobe_path=payload.ffprobe,
            ffmpeg_path=payload.ffmpeg,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        **result,
        "dashboard": build_video_mix_dashboard_payload(result["work_dir"]),
    }


@app.post("/api/video-mix/quick-mix-estimate")
async def estimate_video_mix_quick_mix(payload: VideoMixQuickMixEstimateRequest) -> dict[str, Any]:
    try:
        return {
            "ok": True,
            **estimate_quick_mix_capacity(
                payload.source_dir,
                duration_seconds=payload.duration_seconds,
                episode_duration_min_seconds=payload.episode_duration_min_seconds,
                episode_duration_max_seconds=payload.episode_duration_max_seconds,
                ffprobe_path=payload.ffprobe,
                music_path=payload.music_path or None,
                music_paths=payload.music_paths or None,
                use_music_duration=payload.use_music_duration,
                opening_media_path=payload.opening_media_path or None,
                opening_media_paths=payload.opening_media_paths or None,
                closing_media_path=payload.closing_media_path or None,
                closing_media_paths=payload.closing_media_paths or None,
                use_closing_duration=payload.use_closing_duration,
            ),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/video-mix/quick-mix")
async def quick_mix_video_mix_source(payload: VideoMixQuickMixRequest) -> dict[str, Any]:
    try:
        result = quick_mix_source_materials(
            payload.source_dir,
            duration_seconds=payload.duration_seconds,
            output_count=payload.output_count,
            episode_duration_min_seconds=payload.episode_duration_min_seconds,
            episode_duration_max_seconds=payload.episode_duration_max_seconds,
            project_name=payload.project_name or None,
            pack=payload.pack,
            work_dir=payload.work_dir or None,
            ffmpeg_path=payload.ffmpeg,
            ffprobe_path=payload.ffprobe,
            music_path=payload.music_path or None,
            music_paths=payload.music_paths or None,
            use_music_duration=payload.use_music_duration,
            opening_media_path=payload.opening_media_path or None,
            opening_media_paths=payload.opening_media_paths or None,
            closing_media_path=payload.closing_media_path or None,
            closing_media_paths=payload.closing_media_paths or None,
            use_closing_duration=payload.use_closing_duration,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        **result,
        "dashboard": build_video_mix_dashboard_payload(result["work_dir"]),
    }


@app.get("/api/video-mix/file")
async def video_mix_file(work_dir: str, relative_path: str) -> FileResponse:
    path = resolve_relative_work_path(work_dir, relative_path)
    return FileResponse(path=path, filename=path.name)


def _find_playlist_item(item_id: str) -> dict[str, Any] | None:
    with storage.connect() as connection:
        row = connection.execute("SELECT * FROM playlist_items WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def _resolve_existing_path(raw_path: str | None) -> Path:
    try:
        settings = storage.get_settings()
        return resolve_existing_output_path(raw_path, settings["output_directory"], BASE_DIR)
    except MissingPathError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsafePathError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/download/{job_id}")
async def download_job(job_id: str) -> FileResponse:
    job = storage.get_job(job_id)
    if not job or not job.get("output_path"):
        raise HTTPException(status_code=404, detail="Downloaded file not found")
    path = _resolve_existing_path(job.get("output_path"))
    return FileResponse(path=path, filename=path.name)


@app.get("/api/download/item/{item_id}")
async def download_playlist_item(item_id: str) -> FileResponse:
    item = _find_playlist_item(item_id)
    if not item or not item.get("output_path"):
        raise HTTPException(status_code=404, detail="Playlist item not found")
    path = _resolve_existing_path(item.get("output_path"))
    return FileResponse(path=path, filename=path.name)


@app.post("/api/open/job/{job_id}")
async def open_job_file(job_id: str) -> dict[str, Any]:
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    path = _resolve_existing_path(job.get("output_path"))
    os.startfile(str(path))
    return {"ok": True}


@app.post("/api/open/job/{job_id}/folder")
async def open_job_folder(job_id: str) -> dict[str, Any]:
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    path = _resolve_existing_path(job.get("output_path"))
    os.startfile(str(path.parent))
    return {"ok": True}


@app.post("/api/open/item/{item_id}")
async def open_playlist_item_file(item_id: str) -> dict[str, Any]:
    item = _find_playlist_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Playlist item not found")
    path = _resolve_existing_path(item.get("output_path"))
    os.startfile(str(path))
    return {"ok": True}


@app.post("/api/open/item/{item_id}/folder")
async def open_playlist_item_folder(item_id: str) -> dict[str, Any]:
    item = _find_playlist_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Playlist item not found")
    path = _resolve_existing_path(item.get("output_path"))
    os.startfile(str(path.parent))
    return {"ok": True}


@app.websocket("/ws/state")
async def state_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    history_status = "all"
    selected_job_id = None
    await websocket.send_json(build_state_payload(history_status, selected_job_id))
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
                payload = json.loads(message)
                history_status = payload.get("history_filter", history_status)
                selected_job_id = payload.get("selected_job_id", selected_job_id)
            except TimeoutError:
                pass
            await websocket.send_json(build_state_payload(history_status, selected_job_id))
    except WebSocketDisconnect:
        return
