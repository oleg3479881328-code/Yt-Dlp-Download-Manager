from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from video_mix.analysis import analyze_project_scenes
from video_mix.core.events import append_event
from video_mix.core.queue import VideoMixFoundationJobQueue
from video_mix.core.storage import load_project
from video_mix.core.store import VideoMixFoundationStore
from video_mix.ingestion import bootstrap_foundation_state
from video_mix.planning import build_foundation_edit_plans
from video_mix.publishing import build_publishing_package
from video_mix.quality import build_quality_report
from video_mix.rendering import render_foundation_outputs
from video_mix.service import plan_source_materials


@dataclass(slots=True)
class ProductionRunRequest:
    source_dir: str
    work_dir: str = ""
    project_name: str = ""
    count: int = 5
    duration_seconds: float = 15.0
    episode_duration_min_seconds: float = 1.5
    episode_duration_max_seconds: float = 2.0
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    music_paths: list[str] | None = None
    use_music_duration: bool = False
    opening_media_paths: list[str] | None = None
    closing_media_paths: list[str] | None = None
    use_closing_duration: bool = False
    pack: str = "wedding"


class ProductionRunManager:
    def __init__(self) -> None:
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def _serialize_request(self, request: ProductionRunRequest) -> dict[str, Any]:
        def _normalize(value: Any) -> Any:
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, list):
                return [_normalize(item) for item in value]
            if isinstance(value, dict):
                return {str(key): _normalize(item) for key, item in value.items()}
            return value

        return {key: _normalize(value) for key, value in asdict(request).items()}

    def recover(self) -> None:
        # Recovery of stale jobs is store-local; each active work_dir is recovered on demand.
        return

    def start(self, request: ProductionRunRequest) -> dict[str, Any]:
        bootstrap_probe = plan_source_materials(
            request.source_dir,
            project_name=request.project_name or None,
            pack=request.pack,
            work_dir=request.work_dir or None,
            ffprobe_path=request.ffprobe,
            ffmpeg_path=request.ffmpeg,
            clip_ms=int(((request.episode_duration_min_seconds + request.episode_duration_max_seconds) / 2) * 1000),
        )
        work_dir = Path(str(bootstrap_probe["work_dir"])).resolve()
        store = VideoMixFoundationStore(work_dir)
        bootstrap_foundation_state(work_dir)
        project_id = load_project(work_dir).project_id
        queue = VideoMixFoundationJobQueue(store)
        run_id = queue.enqueue(
            project_id=project_id,
            job_type="production_run",
            payload={
                "request": self._serialize_request(request),
                "work_dir": str(work_dir),
            },
            idempotency_key=(
                f"production-run:{project_id}:{request.count}:{request.duration_seconds}:"
                f"{request.episode_duration_min_seconds}:{request.episode_duration_max_seconds}:{request.source_dir}"
            ),
        )
        self._ensure_worker(work_dir)
        return {"run_id": run_id, "work_dir": str(work_dir), "project_id": project_id}

    def _ensure_worker(self, work_dir: Path) -> None:
        key = str(work_dir.resolve())
        with self._lock:
            thread = self._threads.get(key)
            if thread and thread.is_alive():
                return
            thread = threading.Thread(target=self._worker_loop, args=(work_dir,), daemon=True, name=f"video-mix-foundation-{work_dir.name}")
            self._threads[key] = thread
            thread.start()

    def _worker_loop(self, work_dir: Path) -> None:
        store = VideoMixFoundationStore(work_dir)
        queue = VideoMixFoundationJobQueue(store)
        queue.recover_stale_running()
        while True:
            leased = queue.lease_next(lease_owner="foundation-runtime", lease_seconds=300)
            if not leased:
                return
            job_id = str(leased["job_id"])
            payload = leased.get("payload_json") or {}
            try:
                self._execute_job(work_dir, job_id, payload)
                queue.complete(job_id)
            except Exception as exc:  # noqa: BLE001
                queue.fail(job_id, error=str(exc))

    def _job_row(self, store: VideoMixFoundationStore, run_id: str) -> dict[str, Any]:
        row = store.fetch_one("SELECT * FROM jobs WHERE job_id = ?", (run_id,))
        if row is None:
            raise ValueError(f"Production run not found: {run_id}")
        payload = row.get("payload_json")
        if isinstance(payload, str):
            try:
                row["payload_json"] = json.loads(payload)
            except json.JSONDecodeError:
                row["payload_json"] = {}
        row["cancel_requested"] = bool(row.get("cancel_requested"))
        return row

    def _is_cancelled(self, store: VideoMixFoundationStore, run_id: str) -> bool:
        row = self._job_row(store, run_id)
        return bool(row.get("cancel_requested")) or str(row.get("status") or "") == "canceled"

    def _mark_canceled(self, store: VideoMixFoundationStore, run_id: str) -> None:
        row = self._job_row(store, run_id)
        row["status"] = "canceled"
        row["finished_at"] = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        row["cancel_requested"] = True
        store.upsert_job(**row)

    def _heartbeat(self, store: VideoMixFoundationStore, run_id: str, progress: float, stage: str) -> None:
        row = self._job_row(store, run_id)
        payload = dict(row.get("payload_json") or {})
        payload["stage"] = stage
        row["payload_json"] = payload
        row["heartbeat_at"] = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        row["progress"] = progress
        store.upsert_job(**row)

    def _execute_job(self, work_dir: Path, run_id: str, payload: dict[str, Any]) -> None:
        if isinstance(payload, str):
            payload = json.loads(payload)
        request_payload = dict(payload.get("request") or {})
        request = ProductionRunRequest(**request_payload)
        store = VideoMixFoundationStore(work_dir)
        if self._is_cancelled(store, run_id):
            self._mark_canceled(store, run_id)
            return
        self._heartbeat(store, run_id, 0.05, "bootstrap")
        bootstrap_summary = bootstrap_foundation_state(work_dir)
        project = load_project(work_dir)
        append_event(
            store,
            project_id=project.project_id,
            entity_type="project",
            entity_id=project.project_id,
            event_type="project.registered",
            payload=bootstrap_summary,
        )
        self._heartbeat(store, run_id, 0.15, "analysis")
        analysis = analyze_project_scenes(
            work_dir,
            ffprobe_path=request.ffprobe,
            min_scene_ms=int(request.episode_duration_min_seconds * 1000),
            fixed_clip_ms=int(((request.episode_duration_min_seconds + request.episode_duration_max_seconds) / 2) * 1000),
        )
        append_event(
            store,
            project_id=project.project_id,
            entity_type="analysis_run",
            entity_id=analysis.analysis_run_id,
            event_type="analysis.completed",
            payload={"scene_count": analysis.scene_count},
        )
        if self._is_cancelled(store, run_id):
            self._mark_canceled(store, run_id)
            return
        self._heartbeat(store, run_id, 0.35, "planning")
        planning = build_foundation_edit_plans(
            work_dir,
            analysis_run_id=analysis.analysis_run_id,
            scene_rows=analysis.scenes,
            requested_output_count=request.count,
            target_duration_ms=int(request.duration_seconds * 1000),
        )
        append_event(
            store,
            project_id=project.project_id,
            entity_type="edit_plan",
            entity_id=planning["generation_id"],
            event_type="plan.created",
            payload={"selected_count": planning["selected_count"], "candidate_count": planning["candidate_count"]},
        )
        row = self._job_row(store, run_id)
        payload_json = dict(row.get("payload_json") or {})
        payload_json["analysis_run_id"] = analysis.analysis_run_id
        payload_json["generation_id"] = planning["generation_id"]
        payload_json["plan_path"] = planning["plan_path"]
        row["payload_json"] = payload_json
        store.upsert_job(**row)
        if self._is_cancelled(store, run_id):
            self._mark_canceled(store, run_id)
            return
        self._heartbeat(store, run_id, 0.55, "rendering")
        outputs = render_foundation_outputs(
            work_dir=work_dir,
            generation_id=planning["generation_id"],
            selected_plans=planning["selected_plans"],
            ffmpeg_path=request.ffmpeg,
            music_paths=request.music_paths or [],
        )
        if self._is_cancelled(store, run_id):
            self._mark_canceled(store, run_id)
            return
        self._heartbeat(store, run_id, 0.75, "quality")
        qc_reports: list[dict[str, Any]] = []
        for row in outputs:
            report = build_quality_report(
                work_dir=work_dir,
                project_id=project.project_id,
                plan=row["plan"],
                output_path=work_dir / row["output_path"],
                ffprobe_path=request.ffprobe,
            )
            row["quality_report"] = report
            qc_reports.append(report)
            append_event(
                store,
                project_id=project.project_id,
                entity_type="quality_report",
                entity_id=report["report_id"],
                event_type="quality.completed",
                payload={"status": report["status"]},
            )
        if self._is_cancelled(store, run_id):
            self._mark_canceled(store, run_id)
            return
        self._heartbeat(store, run_id, 0.92, "publishing")
        package = build_publishing_package(
            work_dir=work_dir,
            generation_id=planning["generation_id"],
            outputs=outputs,
        )
        append_event(
            store,
            project_id=project.project_id,
            entity_type="package",
            entity_id=planning["generation_id"],
            event_type="package.created",
            payload=package,
        )
        row = self._job_row(store, run_id)
        payload_json = dict(row.get("payload_json") or {})
        payload_json["package"] = package
        payload_json["quality_reports"] = qc_reports
        row["payload_json"] = payload_json
        store.upsert_job(**row)
        self._heartbeat(store, run_id, 0.99, "completed")

    def get_status(self, work_dir: str, run_id: str) -> dict[str, Any]:
        resolved_work_dir = Path(work_dir).expanduser().resolve()
        store = VideoMixFoundationStore(resolved_work_dir)
        row = self._job_row(store, run_id)
        payload = dict(row.get("payload_json") or {})
        row["latest_package"] = payload.get("package")
        row["analysis_run_id"] = payload.get("analysis_run_id") or ""
        row["generation_id"] = payload.get("generation_id") or ""
        row["plan_path"] = payload.get("plan_path") or ""
        row["quality_reports"] = payload.get("quality_reports") or []
        row["stage"] = payload.get("stage") or ""
        return row

    def cancel(self, work_dir: str, run_id: str) -> dict[str, Any]:
        resolved_work_dir = Path(work_dir).expanduser().resolve()
        store = VideoMixFoundationStore(resolved_work_dir)
        row = self._job_row(store, run_id)
        if str(row.get("status") or "") in {"queued", "retry_wait"}:
            row["status"] = "canceled"
            row["cancel_requested"] = True
            row["finished_at"] = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
            store.upsert_job(**row)
        else:
            queue = VideoMixFoundationJobQueue(store)
            queue.request_cancel(run_id)
        return self.get_status(str(resolved_work_dir), run_id)

    def retry(self, work_dir: str, run_id: str) -> dict[str, Any]:
        resolved_work_dir = Path(work_dir).expanduser().resolve()
        store = VideoMixFoundationStore(resolved_work_dir)
        row = self._job_row(store, run_id)
        payload = dict(row.get("payload_json") or {})
        request_payload = dict(payload.get("request") or {})
        request = ProductionRunRequest(**request_payload)
        project_id = str(row["project_id"])
        queue = VideoMixFoundationJobQueue(store)
        retried_run_id = queue.enqueue(
            project_id=project_id,
            job_type="production_run",
            payload={
                "request": self._serialize_request(request),
                "work_dir": str(resolved_work_dir),
                "retried_from": run_id,
            },
            idempotency_key=f"retry-production-run:{run_id}:{time.time_ns()}",
        )
        self._ensure_worker(resolved_work_dir)
        return self.get_status(str(resolved_work_dir), retried_run_id)


production_run_manager = ProductionRunManager()
