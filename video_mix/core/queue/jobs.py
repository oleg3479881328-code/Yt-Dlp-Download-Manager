from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from video_mix.core.store import VideoMixFoundationStore


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class VideoMixFoundationJobQueue:
    def __init__(self, store: VideoMixFoundationStore) -> None:
        self.store = store

    def enqueue(self, *, project_id: str, job_type: str, payload: dict, idempotency_key: str, max_attempts: int = 3) -> str:
        existing = self.store.fetch_one(
            "SELECT job_id FROM jobs WHERE project_id = ? AND idempotency_key = ?",
            (project_id, idempotency_key),
        )
        if existing:
            return str(existing["job_id"])
        job_id = str(uuid4())
        self.store.upsert_job(
            job_id=job_id,
            project_id=project_id,
            job_type=job_type,
            status="queued",
            payload_json=payload,
            idempotency_key=idempotency_key,
            attempt_count=0,
            max_attempts=max_attempts,
            lease_owner="",
            lease_expires_at="",
            heartbeat_at="",
            progress=0.0,
            cancel_requested=False,
            error="",
            created_at=_utc_now(),
            started_at="",
            finished_at="",
        )
        return job_id

    def lease_next(self, *, lease_owner: str, lease_seconds: int = 120) -> dict | None:
        queued = self.store.fetch_one(
            "SELECT * FROM jobs WHERE status IN ('queued', 'retry_wait') AND cancel_requested = 0 ORDER BY created_at ASC LIMIT 1"
        )
        if not queued:
            return None
        lease_expires_at = datetime.now(UTC) + timedelta(seconds=lease_seconds)
        self.store.upsert_job(
            **{
                **queued,
                "status": "running",
                "lease_owner": lease_owner,
                "lease_expires_at": lease_expires_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "heartbeat_at": _utc_now(),
                "attempt_count": int(queued.get("attempt_count") or 0) + 1,
                "started_at": queued.get("started_at") or _utc_now(),
                "cancel_requested": bool(queued.get("cancel_requested")),
                "payload_json": queued.get("payload_json") or {},
            }
        )
        return self.store.fetch_one("SELECT * FROM jobs WHERE job_id = ?", (queued["job_id"],))

    def heartbeat(self, job_id: str, *, progress: float) -> None:
        current = self.store.fetch_one("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        if not current:
            raise ValueError(f"Unknown job_id: {job_id}")
        self.store.upsert_job(
            **{
                **current,
                "payload_json": current.get("payload_json") or {},
                "heartbeat_at": _utc_now(),
                "progress": progress,
                "cancel_requested": bool(current.get("cancel_requested")),
            }
        )

    def complete(self, job_id: str) -> None:
        current = self.store.fetch_one("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        if not current:
            raise ValueError(f"Unknown job_id: {job_id}")
        self.store.upsert_job(
            **{
                **current,
                "payload_json": current.get("payload_json") or {},
                "status": "completed",
                "progress": 1.0,
                "finished_at": _utc_now(),
                "cancel_requested": bool(current.get("cancel_requested")),
            }
        )

    def fail(self, job_id: str, *, error: str) -> None:
        current = self.store.fetch_one("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        if not current:
            raise ValueError(f"Unknown job_id: {job_id}")
        next_status = "failed"
        if int(current.get("attempt_count") or 0) < int(current.get("max_attempts") or 0):
            next_status = "retry_wait"
        self.store.upsert_job(
            **{
                **current,
                "payload_json": current.get("payload_json") or {},
                "status": next_status,
                "error": error,
                "finished_at": _utc_now() if next_status == "failed" else "",
                "cancel_requested": bool(current.get("cancel_requested")),
            }
        )

    def request_cancel(self, job_id: str) -> None:
        current = self.store.fetch_one("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        if not current:
            raise ValueError(f"Unknown job_id: {job_id}")
        self.store.upsert_job(
            **{
                **current,
                "payload_json": current.get("payload_json") or {},
                "cancel_requested": True,
            }
        )

    def recover_stale_running(self) -> int:
        stale = self.store.fetch_all(
            "SELECT * FROM jobs WHERE status = 'running' AND lease_expires_at != '' AND lease_expires_at < ?",
            (_utc_now(),),
        )
        for job in stale:
            self.store.upsert_job(
                **{
                    **job,
                    "payload_json": job.get("payload_json") or {},
                    "status": "queued",
                    "lease_owner": "",
                    "lease_expires_at": "",
                    "heartbeat_at": "",
                    "cancel_requested": bool(job.get("cancel_requested")),
                }
            )
        return len(stale)
