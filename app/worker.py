from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from .storage import Storage
from .yt_service import build_ydl_options, format_eta, format_speed, utc_now


def _require_youtube_dl():
    try:
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import DownloadError
    except ModuleNotFoundError as exc:
        raise RuntimeError("yt_dlp is not installed. Install project requirements to run downloader jobs.") from exc
    return YoutubeDL, DownloadError


class DownloadWorker:
    def __init__(self, storage: Storage, base_dir: Path) -> None:
        self.storage = storage
        self.base_dir = base_dir
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run_loop, name="yt-dlp-worker", daemon=True)
        self.thread.start()

    def _run_loop(self) -> None:
        while not self.stop_event.is_set():
            next_job = self._pick_next_job()
            if not next_job:
                time.sleep(1)
                continue
            self._execute_job(next_job["id"])

    def _pick_next_job(self) -> dict[str, Any] | None:
        jobs = self.storage.list_jobs(("queued", "ready"))
        return jobs[0] if jobs else None

    def _is_canceled(self, job_id: str) -> bool:
        job = self.storage.get_job(job_id)
        return bool(job and job["status"] == "canceled")

    def _progress_hook(self, job_id: str, item_id: str | None = None):
        def hook(payload: dict[str, Any]) -> None:
            if self._is_canceled(job_id):
                _, DownloadError = _require_youtube_dl()
                raise DownloadError("Canceled by user")

            progress_status = payload.get("status")
            stage = "Downloading" if progress_status == "downloading" else "Post-processing"
            downloaded = payload.get("downloaded_bytes") or 0
            total = payload.get("total_bytes") or payload.get("total_bytes_estimate") or 0
            percent = round((downloaded / total) * 100, 1) if total else 0
            speed = format_speed(payload.get("speed"))
            eta = format_eta(payload.get("eta"))
            filename = payload.get("filename")

            self.storage.update_job(
                job_id,
                stage=stage,
                progress=percent,
                speed=speed,
                eta=eta,
                output_path=filename,
            )
            if item_id:
                self.storage.update_playlist_item(
                    item_id,
                    status="downloading" if progress_status == "downloading" else "post_processing",
                    progress=percent,
                    speed=speed,
                    eta=eta,
                    output_path=filename,
                )
        return hook

    def _resolve_output_dir(self, output_directory: str) -> Path:
        output = Path(output_directory)
        if not output.is_absolute():
            output = self.base_dir / output
        return output

    def _attempts_total(self, settings: dict[str, Any]) -> int:
        if not settings.get("retry_enabled"):
            return 1
        return max(1, int(settings.get("retry_count", 0)) + 1)

    def _resolve_final_output_path(self, info: dict[str, Any], ydl: Any) -> str | None:
        requested = info.get("requested_downloads") or []
        for entry in requested:
            filepath = entry.get("filepath")
            if filepath:
                return str(filepath)

        filepath = info.get("filepath")
        if filepath:
            return str(filepath)

        return ydl.prepare_filename(info)

    def _execute_job(self, job_id: str) -> None:
        job = self.storage.get_job(job_id)
        if not job or job["status"] not in {"queued", "ready"}:
            return

        self.storage.update_job(
            job_id,
            status="downloading",
            stage="Preparing download",
            started_at=utc_now(),
            error=None,
        )
        self.storage.add_log(job_id, "Job started", utc_now())
        self.storage.refresh_queue_positions()

        try:
            if job["type"] == "playlist":
                self._download_playlist(job_id)
            else:
                self._download_single(job_id)
        except Exception as exc:  # noqa: BLE001
            finished_status = "canceled" if "Canceled by user" in str(exc) else "failed"
            self.storage.update_job(
                job_id,
                status=finished_status,
                stage="Canceled" if finished_status == "canceled" else "Failed",
                error=str(exc),
                finished_at=utc_now(),
            )
            self.storage.add_log(job_id, f"Job ended: {exc}", utc_now())
        finally:
            self.storage.refresh_queue_positions()

    def _download_single(self, job_id: str) -> None:
        job = self.storage.get_job(job_id)
        if not job:
            return
        YoutubeDL, DownloadError = _require_youtube_dl()
        settings = self.storage.get_settings()
        output_dir = self._resolve_output_dir(settings["output_directory"])
        output_dir.mkdir(parents=True, exist_ok=True)
        mode = job["mode"] or settings["default_mode"]
        quality = job["quality"] or settings["quality"]
        segment = (job.get("analysis_json") or {}).get("segment")
        attempts_total = self._attempts_total(settings)
        output_path = None

        for attempt in range(1, attempts_total + 1):
            options = build_ydl_options(output_dir, mode, quality, self._progress_hook(job_id), segment=segment)
            if segment:
                self.storage.add_log(
                    job_id,
                    (
                        "Starting selected segment download "
                        f"(attempt {attempt}/{attempts_total}): "
                        f"{segment['section_expression']} ({segment['label']})"
                    ),
                    utc_now(),
                )
            else:
                self.storage.add_log(
                    job_id,
                    f"Starting single-item download (attempt {attempt}/{attempts_total})",
                    utc_now(),
                )
            try:
                with YoutubeDL(options) as ydl:
                    info = ydl.extract_info(job["url"], download=True)
                    output_path = self._resolve_final_output_path(info, ydl)
                break
            except Exception:
                if attempt == attempts_total:
                    raise
                self.storage.add_log(job_id, f"Retrying single-item download after failed attempt {attempt}", utc_now())

        if self._is_canceled(job_id):
            raise DownloadError("Canceled by user")

        self.storage.update_job(
            job_id,
            status="completed",
            stage="Completed",
            progress=100,
            speed=None,
            eta=None,
            finished_at=utc_now(),
            output_path=output_path,
        )
        self.storage.add_log(job_id, "Segment download completed" if segment else "Download completed", utc_now())

    def _download_playlist(self, job_id: str) -> None:
        job = self.storage.get_job(job_id)
        if not job:
            return
        YoutubeDL, DownloadError = _require_youtube_dl()
        settings = self.storage.get_settings()
        output_dir = self._resolve_output_dir(settings["output_directory"])
        output_dir.mkdir(parents=True, exist_ok=True)
        mode = job["mode"] or settings["default_mode"]
        quality = job["quality"] or settings["quality"]
        attempts_total = self._attempts_total(settings)
        items = job["playlist_items"]
        completed = 0
        failed = 0

        for item in items:
            if self._is_canceled(job_id):
                raise DownloadError("Canceled by user")

            item_number = item["item_index"] + 1
            self.storage.update_job(
                job_id,
                current_item_id=item["id"],
                current_item_index=item_number,
                stage=f"Downloading item {item_number} of {len(items)}",
            )
            self.storage.update_playlist_item(item["id"], status="downloading", error=None)
            self.storage.add_log(job_id, f"Starting playlist item: {item['title']}", utc_now(), item_id=item["id"])

            try:
                output_path = None
                for attempt in range(1, attempts_total + 1):
                    self.storage.add_log(
                        job_id,
                        f"Downloading playlist item attempt {attempt}/{attempts_total}: {item['title']}",
                        utc_now(),
                        item_id=item["id"],
                    )
                    try:
                        with YoutubeDL(build_ydl_options(output_dir, mode, quality, self._progress_hook(job_id, item["id"]))) as ydl:
                            info = ydl.extract_info(item["url"], download=True)
                            output_path = self._resolve_final_output_path(info, ydl)
                        break
                    except Exception:
                        if attempt == attempts_total:
                            raise
                        self.storage.add_log(
                            job_id,
                            f"Retrying playlist item after failed attempt {attempt}: {item['title']}",
                            utc_now(),
                            item_id=item["id"],
                        )
                self.storage.update_playlist_item(
                    item["id"],
                    status="completed",
                    progress=100,
                    speed=None,
                    eta=None,
                    output_path=output_path,
                )
                completed += 1
                self.storage.add_log(job_id, f"Completed playlist item: {item['title']}", utc_now(), item_id=item["id"])
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self.storage.update_playlist_item(
                    item["id"],
                    status="failed",
                    error=str(exc),
                    speed=None,
                    eta=None,
                )
                self.storage.add_log(job_id, f"Playlist item failed: {item['title']} ({exc})", utc_now(), item_id=item["id"])

            self.storage.update_job(
                job_id,
                progress=round(((completed + failed) / max(len(items), 1)) * 100, 1),
                item_completed=completed,
                item_failed=failed,
            )

        final_status = "failed" if completed == 0 and failed else "completed"
        final_stage = "Completed with partial success" if completed and failed else ("Completed" if completed else "Failed")
        self.storage.update_job(
            job_id,
            status=final_status,
            stage=final_stage,
            progress=100,
            speed=None,
            eta=None,
            finished_at=utc_now(),
            current_item_id=None,
            current_item_index=0,
        )
        self.storage.add_log(job_id, f"Playlist finished: {completed} completed, {failed} failed", utc_now())

    def retry_job(self, job_id: str) -> None:
        job = self.storage.get_job(job_id)
        if not job:
            return
        self.storage.update_job(
            job_id,
            status="queued",
            stage="Queued",
            progress=0,
            speed=None,
            eta=None,
            error=None,
            finished_at=None,
            started_at=None,
            item_completed=0,
            item_failed=0,
            current_item_id=None,
            current_item_index=0,
            output_path=None,
        )
        for item in job["playlist_items"]:
            self.storage.update_playlist_item(
                item["id"],
                status="pending",
                progress=0,
                speed=None,
                eta=None,
                error=None,
                output_path=None,
            )
        self.storage.add_log(job_id, "Job queued for retry", utc_now())
        self.storage.refresh_queue_positions()
