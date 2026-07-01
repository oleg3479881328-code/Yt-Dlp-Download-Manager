from __future__ import annotations

import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from video_mix.core.models import CandidateStatus
from video_mix.service import plan_source_materials, quick_mix_source_materials, scan_source_materials

from .path_safety import MissingPathError, UnsafePathError, resolve_existing_output_path
from .segment_utils import SegmentValidationError, normalize_segment_payload
from .storage import Storage
from .video_mix_dashboard import (
    build_dashboard_payload as build_video_mix_dashboard_payload,
)
from .video_mix_dashboard import (
    bulk_update_candidate_status,
    export_approved_candidates,
    open_dashboard_target,
    pick_dashboard_work_dir,
    pick_source_materials_dir,
    resolve_relative_work_path,
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


class VideoMixQuickMixRequest(BaseModel):
    source_dir: str
    duration_seconds: float = Field(gt=0)
    output_count: int = Field(gt=0)
    project_name: str = ""
    pack: str = "wedding"
    work_dir: str = ""
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    output_orientation: str = "vertical"


@asynccontextmanager
async def lifespan(_: FastAPI):
    worker.start()
    yield


app = FastAPI(title="yt-dlp Download Manager", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")


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
        return {"ok": True, "analysis": analyze_url(payload.url)}
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
        analysis = analyze_url(payload.url)
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


@app.post("/api/video-mix/quick-mix")
async def quick_mix_video_mix_source(payload: VideoMixQuickMixRequest) -> dict[str, Any]:
    try:
        result = quick_mix_source_materials(
            payload.source_dir,
            duration_seconds=payload.duration_seconds,
            output_count=payload.output_count,
            project_name=payload.project_name or None,
            pack=payload.pack,
            work_dir=payload.work_dir or None,
            ffmpeg_path=payload.ffmpeg,
            ffprobe_path=payload.ffprobe,
            output_orientation=payload.output_orientation,
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
    try:
        while True:
            message = await websocket.receive_text()
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                payload = {}
            history_status = payload.get("history_status", history_status)
            selected_job_id = payload.get("selected_job_id", selected_job_id)
            await websocket.send_json(build_state_payload(history_status, selected_job_id))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return
