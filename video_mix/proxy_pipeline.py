from __future__ import annotations

import json
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from .core.models import Asset, MediaType, Orientation
from .core.storage import load_assets, read_json, write_json

PROXY_DIRECTORY_NAME = "video_proxies"
PROXY_MANIFEST_RELATIVE_PATH = "reports/video_proxy_manifest.json"
PROXY_LOG_DIRECTORY_RELATIVE_PATH = "reports/video_proxy_jobs"
PROXY_ALLOWED_CONCURRENCY = 1
PROXY_ALLOWED_MAX_CONCURRENCY = 2
PROXY_PROFILE_VERSION = "video-proxy-v1"
PROXY_READY = "ready"
PROXY_FAILED = "failed"
PROXY_STALE = "stale"
PROXY_MISSING = "missing"
PROXY_PENDING = "pending"
PROXY_RUNNING = "running"
PROXY_JOB_QUEUED = "queued"
PROXY_JOB_RUNNING = "running"
PROXY_JOB_COMPLETED = "completed"
PROXY_JOB_FAILED = "failed"
PROXY_JOB_CANCELLED = "cancelled"

PROXY_PROFILE = {
    "container": "mp4",
    "video_codec": "libx264",
    "pixel_format": "yuv420p",
    "scale_width": 1280,
    "scale_height": 720,
    "crf": 28,
    "preset": "veryfast",
    "audio_codec": "aac",
    "audio_bitrate": "96k",
    "movflags": "+faststart",
    "profile_version": PROXY_PROFILE_VERSION,
}


def proxy_manifest_path(work_dir: Path) -> Path:
    return work_dir / PROXY_MANIFEST_RELATIVE_PATH


def proxy_directory_path(work_dir: Path) -> Path:
    return work_dir / PROXY_DIRECTORY_NAME


def proxy_log_directory_path(work_dir: Path) -> Path:
    return work_dir / PROXY_LOG_DIRECTORY_RELATIVE_PATH


def proxy_output_path(work_dir: Path, asset_id: str) -> Path:
    return proxy_directory_path(work_dir) / f"{asset_id}.proxy.mp4"


def proxy_partial_path(work_dir: Path, asset_id: str) -> Path:
    return proxy_directory_path(work_dir) / f"{asset_id}.proxy.partial.mp4"


def proxy_job_log_path(work_dir: Path, asset_id: str) -> Path:
    return proxy_log_directory_path(work_dir) / f"{asset_id}.log"


def _json_hash(payload: dict[str, Any]) -> str:
    return f"sha256:{sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()}"


def _duration_tolerance_ms(asset: Asset) -> int:
    if asset.fps and asset.fps > 0:
        return max(50, int(round(1000 / float(asset.fps))))
    return 50


def _decode_stdout(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


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
    completed = subprocess.run(command, capture_output=True, check=True)
    return json.loads(_decode_stdout(completed.stdout))


def _ffprobe_video_stream(payload: dict[str, Any]) -> dict[str, Any] | None:
    for stream in payload.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    return None


def _ffprobe_audio_stream(payload: dict[str, Any]) -> dict[str, Any] | None:
    for stream in payload.get("streams", []):
        if stream.get("codec_type") == "audio":
            return stream
    return None


def _probe_duration_ms(payload: dict[str, Any]) -> int:
    raw_duration = payload.get("format", {}).get("duration")
    if raw_duration is None:
        return 0
    return max(0, int(round(float(raw_duration) * 1000)))


def _probe_rotation(stream: dict[str, Any] | None) -> int:
    if not stream:
        return 0
    tags = stream.get("tags") or {}
    if "rotate" in tags:
        try:
            return int(tags["rotate"])
        except (TypeError, ValueError):
            return 0
    for side_data in stream.get("side_data_list") or []:
        if "rotation" in side_data:
            try:
                return int(side_data["rotation"])
            except (TypeError, ValueError):
                return 0
    return 0


def _orientation_from_dimensions(width: int | None, height: int | None) -> str:
    if not width or not height:
        return Orientation.UNKNOWN.value
    if width == height:
        return Orientation.SQUARE.value
    if height > width:
        return Orientation.VERTICAL.value
    return Orientation.HORIZONTAL.value


def _apply_rotation_to_dimensions(width: int | None, height: int | None, rotation: int) -> tuple[int | None, int | None]:
    if rotation % 180 == 90:
        return height, width
    return width, height


def build_source_fingerprint(asset: Asset) -> str:
    stat_result = asset.path.stat()
    payload = {
        "asset_id": asset.asset_id,
        "path": str(asset.path.resolve()).lower(),
        "size": stat_result.st_size,
        "mtime_ns": stat_result.st_mtime_ns,
        "duration_ms": asset.duration_ms or 0,
        "width": asset.width or 0,
        "height": asset.height or 0,
        "fps": round(float(asset.fps or 0.0), 6),
        "orientation": asset.orientation.value,
        "has_audio": bool(asset.has_audio),
    }
    return _json_hash(payload)


def build_profile_fingerprint() -> str:
    return _json_hash(PROXY_PROFILE)


def load_proxy_manifest(work_dir: Path) -> dict[str, Any]:
    path = proxy_manifest_path(work_dir)
    if not path.exists():
        return {
            "profile_version": PROXY_PROFILE_VERSION,
            "profile_fingerprint": build_profile_fingerprint(),
            "entries": {},
        }
    payload = read_json(path)
    payload.setdefault("profile_version", PROXY_PROFILE_VERSION)
    payload.setdefault("profile_fingerprint", build_profile_fingerprint())
    payload.setdefault("entries", {})
    return payload


def save_proxy_manifest(work_dir: Path, manifest: dict[str, Any]) -> None:
    manifest["profile_version"] = PROXY_PROFILE_VERSION
    manifest["profile_fingerprint"] = build_profile_fingerprint()
    write_json(proxy_manifest_path(work_dir), manifest)


def validate_proxy_against_asset(asset: Asset, proxy_path: Path, ffprobe_path: str) -> dict[str, Any]:
    payload = _ffprobe_payload(proxy_path, ffprobe_path)
    video_stream = _ffprobe_video_stream(payload)
    if video_stream is None:
        raise ValueError("Proxy has no decodable video stream")
    audio_stream = _ffprobe_audio_stream(payload)
    proxy_duration_ms = _probe_duration_ms(payload)
    source_duration_ms = int(asset.duration_ms or 0)
    if source_duration_ms <= 0:
        raise ValueError("Original asset has no valid duration")
    duration_delta_ms = abs(proxy_duration_ms - source_duration_ms)
    tolerance_ms = _duration_tolerance_ms(asset)
    if duration_delta_ms > tolerance_ms:
        raise ValueError(
            f"Proxy duration delta {duration_delta_ms}ms exceeds tolerance {tolerance_ms}ms"
        )
    rotation = _probe_rotation(video_stream)
    raw_width = int(video_stream.get("width") or 0) or None
    raw_height = int(video_stream.get("height") or 0) or None
    visual_width, visual_height = _apply_rotation_to_dimensions(raw_width, raw_height, rotation)
    proxy_orientation = _orientation_from_dimensions(visual_width, visual_height)
    if asset.orientation != Orientation.UNKNOWN and proxy_orientation != asset.orientation.value:
        raise ValueError(
            f"Proxy orientation mismatch: expected {asset.orientation.value}, got {proxy_orientation}"
        )
    if asset.has_audio and audio_stream is None:
        raise ValueError("Proxy is missing expected audio stream")
    return {
        "proxy_duration_ms": proxy_duration_ms,
        "proxy_width": int(visual_width or 0),
        "proxy_height": int(visual_height or 0),
        "has_audio": audio_stream is not None,
        "rotation": rotation,
        "tolerance_ms": tolerance_ms,
        "duration_delta_ms": duration_delta_ms,
    }


def sync_proxy_manifest(work_dir: Path, *, ffprobe_path: str = "ffprobe") -> dict[str, Any]:
    assets = [asset for asset in load_assets(work_dir) if asset.media_type == MediaType.VIDEO]
    manifest = load_proxy_manifest(work_dir)
    entries = manifest.setdefault("entries", {})
    profile_fingerprint = build_profile_fingerprint()
    current_asset_ids = {asset.asset_id for asset in assets}

    for stale_asset_id in list(entries):
        if stale_asset_id not in current_asset_ids:
            entries.pop(stale_asset_id, None)

    for asset in assets:
        output_path = proxy_output_path(work_dir, asset.asset_id)
        entry = entries.get(asset.asset_id, {})
        source_fingerprint = build_source_fingerprint(asset)
        status = entry.get("status") or PROXY_MISSING
        if not output_path.exists():
            status = PROXY_MISSING if status not in {PROXY_RUNNING, PROXY_PENDING} else status
        elif (
            entry.get("source_fingerprint") != source_fingerprint
            or entry.get("profile_fingerprint") != profile_fingerprint
        ):
            status = PROXY_STALE
        else:
            try:
                validation = validate_proxy_against_asset(asset, output_path, ffprobe_path)
                status = PROXY_READY
                entry.update(validation)
            except Exception as exc:  # noqa: BLE001
                status = PROXY_FAILED
                entry["error"] = str(exc)

        entries[asset.asset_id] = {
            "asset_id": asset.asset_id,
            "original_path": str(asset.path.resolve()),
            "proxy_path": str(output_path.relative_to(work_dir)).replace("\\", "/"),
            "source_fingerprint": source_fingerprint,
            "profile_fingerprint": profile_fingerprint,
            "status": status,
            "original_duration_ms": int(asset.duration_ms or 0),
            "proxy_duration_ms": int(entry.get("proxy_duration_ms") or 0),
            "original_width": int(asset.width or 0),
            "original_height": int(asset.height or 0),
            "proxy_width": int(entry.get("proxy_width") or 0),
            "proxy_height": int(entry.get("proxy_height") or 0),
            "created_at": entry.get("created_at") or "",
            "updated_at": entry.get("updated_at") or "",
            "error": entry.get("error") or "",
            "has_audio": bool(entry.get("has_audio") if "has_audio" in entry else asset.has_audio),
        }
    save_proxy_manifest(work_dir, manifest)
    return manifest


@dataclass(slots=True)
class ProxyJob:
    asset_id: str
    queue_state: str = PROXY_JOB_QUEUED
    progress_ratio: float = 0.0
    progress_text: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: str = ""
    current_frame: int = 0
    cancelled: bool = False


class ProxyQueueManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs_by_work_dir: dict[str, dict[str, ProxyJob]] = {}
        self._queues_by_work_dir: dict[str, deque[str]] = {}
        self._workers_by_work_dir: dict[str, threading.Thread] = {}
        self._process_by_work_dir: dict[str, subprocess.Popen[str] | None] = {}

    def dashboard_payload(self, work_dir: Path, *, ffprobe_path: str = "ffprobe") -> dict[str, Any]:
        manifest = sync_proxy_manifest(work_dir, ffprobe_path=ffprobe_path)
        assets = [asset for asset in load_assets(work_dir) if asset.media_type == MediaType.VIDEO]
        jobs = self._jobs_by_work_dir.get(str(work_dir.resolve()), {})
        cards = []
        counts = {
            "total": 0,
            "ready": 0,
            "missing": 0,
            "stale": 0,
            "running": 0,
            "failed": 0,
        }
        for asset in sorted(assets, key=lambda item: item.path.name.lower()):
            entry = manifest["entries"].get(asset.asset_id, {})
            job = jobs.get(asset.asset_id)
            status = str(entry.get("status") or PROXY_MISSING)
            if job and job.queue_state in {PROXY_JOB_QUEUED, PROXY_JOB_RUNNING}:
                status = PROXY_RUNNING if job.queue_state == PROXY_JOB_RUNNING else PROXY_PENDING
            counts["total"] += 1
            if status in counts:
                counts[status] += 1
            elif status in {PROXY_PENDING, PROXY_RUNNING}:
                counts["running"] += 1
            elif status == PROXY_READY:
                counts["ready"] += 1
            elif status == PROXY_STALE:
                counts["stale"] += 1
            elif status == PROXY_FAILED:
                counts["failed"] += 1
            else:
                counts["missing"] += 1
            proxy_file = work_dir / str(entry.get("proxy_path") or "")
            proxy_size_bytes = proxy_file.stat().st_size if proxy_file.exists() else 0
            cards.append(
                {
                    "asset_id": asset.asset_id,
                    "file_name": asset.path.name,
                    "original_path": str(asset.path.resolve()),
                    "original_duration_ms": int(asset.duration_ms or 0),
                    "original_width": int(asset.width or 0),
                    "original_height": int(asset.height or 0),
                    "original_size_bytes": asset.path.stat().st_size if asset.path.exists() else 0,
                    "has_audio": bool(asset.has_audio),
                    "status": status,
                    "proxy_path": str(entry.get("proxy_path") or ""),
                    "proxy_absolute_path": str(proxy_file.resolve()) if proxy_file.exists() else "",
                    "proxy_folder_path": str(proxy_file.parent.resolve()) if proxy_file.exists() else str(proxy_directory_path(work_dir).resolve()),
                    "proxy_duration_ms": int(entry.get("proxy_duration_ms") or 0),
                    "proxy_width": int(entry.get("proxy_width") or 0),
                    "proxy_height": int(entry.get("proxy_height") or 0),
                    "proxy_size_bytes": proxy_size_bytes,
                    "progress_ratio": float(job.progress_ratio if job else 0.0),
                    "progress_text": str(job.progress_text if job else ""),
                    "queue_state": str(job.queue_state if job else ""),
                    "error": str(job.error if job and job.error else entry.get("error") or ""),
                }
            )
        return {
            "summary": counts,
            "profile": {
                "version": PROXY_PROFILE_VERSION,
                "fingerprint": build_profile_fingerprint(),
                "container": PROXY_PROFILE["container"],
                "video_codec": PROXY_PROFILE["video_codec"],
                "audio_codec": PROXY_PROFILE["audio_codec"],
                "scale": f'{PROXY_PROFILE["scale_width"]}x{PROXY_PROFILE["scale_height"]}',
            },
            "queue": {
                "concurrency": PROXY_ALLOWED_CONCURRENCY,
                "max_concurrency": PROXY_ALLOWED_MAX_CONCURRENCY,
                "active_jobs": [
                    {
                        "asset_id": job.asset_id,
                        "queue_state": job.queue_state,
                        "progress_ratio": job.progress_ratio,
                        "progress_text": job.progress_text,
                        "error": job.error,
                    }
                    for job in jobs.values()
                    if job.queue_state in {PROXY_JOB_QUEUED, PROXY_JOB_RUNNING, PROXY_JOB_FAILED}
                ],
            },
            "items": cards,
        }

    def enqueue_missing_or_stale(self, work_dir: Path, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe", only_statuses: set[str] | None = None) -> dict[str, Any]:
        manifest = sync_proxy_manifest(work_dir, ffprobe_path=ffprobe_path)
        only = only_statuses or {PROXY_MISSING, PROXY_STALE}
        asset_ids = [
            asset_id
            for asset_id, entry in manifest["entries"].items()
            if str(entry.get("status") or "") in only
        ]
        return self._enqueue_assets(work_dir, asset_ids, ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)

    def enqueue_asset(self, work_dir: Path, asset_id: str, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> dict[str, Any]:
        return self._enqueue_assets(work_dir, [asset_id], ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)

    def cancel(self, work_dir: Path, asset_id: str) -> dict[str, Any]:
        work_key = str(work_dir.resolve())
        with self._lock:
            job = self._jobs_by_work_dir.setdefault(work_key, {}).get(asset_id)
            if job is None:
                raise ValueError(f"Proxy job not found: {asset_id}")
            job.cancelled = True
            job.updated_at = time.time()
            if job.queue_state == PROXY_JOB_QUEUED:
                job.queue_state = PROXY_JOB_CANCELLED
            process = self._process_by_work_dir.get(work_key)
            if process and job.queue_state == PROXY_JOB_RUNNING:
                process.terminate()
        return self.dashboard_payload(work_dir)

    def delete_proxy(self, work_dir: Path, asset_id: str) -> dict[str, Any]:
        manifest = load_proxy_manifest(work_dir)
        entry = manifest.get("entries", {}).get(asset_id)
        if entry:
            output_path = work_dir / str(entry.get("proxy_path") or "")
            if output_path.exists():
                output_path.unlink()
            entry["status"] = PROXY_MISSING
            entry["proxy_duration_ms"] = 0
            entry["proxy_width"] = 0
            entry["proxy_height"] = 0
            entry["error"] = ""
            entry["updated_at"] = _iso_timestamp()
            save_proxy_manifest(work_dir, manifest)
        partial_path = proxy_partial_path(work_dir, asset_id)
        if partial_path.exists():
            partial_path.unlink()
        return self.dashboard_payload(work_dir)

    def cleanup_partial_files(self, work_dir: Path) -> dict[str, Any]:
        removed = []
        for partial_file in proxy_directory_path(work_dir).glob("*.proxy.partial.mp4"):
            removed.append(partial_file.name)
            partial_file.unlink(missing_ok=True)
        return {"removed": removed, "dashboard": self.dashboard_payload(work_dir)}

    def _enqueue_assets(self, work_dir: Path, asset_ids: list[str], *, ffmpeg_path: str, ffprobe_path: str) -> dict[str, Any]:
        work_key = str(work_dir.resolve())
        manifest = sync_proxy_manifest(work_dir, ffprobe_path=ffprobe_path)
        available_asset_ids = set(manifest.get("entries", {}))
        with self._lock:
            jobs = self._jobs_by_work_dir.setdefault(work_key, {})
            queue = self._queues_by_work_dir.setdefault(work_key, deque())
            for asset_id in asset_ids:
                if asset_id not in available_asset_ids:
                    raise ValueError(f"Proxy asset not found: {asset_id}")
                existing_job = jobs.get(asset_id)
                if existing_job and existing_job.queue_state in {PROXY_JOB_QUEUED, PROXY_JOB_RUNNING}:
                    continue
                jobs[asset_id] = ProxyJob(asset_id=asset_id)
                queue.append(asset_id)
                manifest["entries"][asset_id]["status"] = PROXY_PENDING
                manifest["entries"][asset_id]["updated_at"] = _iso_timestamp()
            save_proxy_manifest(work_dir, manifest)
            worker = self._workers_by_work_dir.get(work_key)
            if worker is None or not worker.is_alive():
                worker = threading.Thread(
                    target=self._worker_loop,
                    args=(work_dir, ffmpeg_path, ffprobe_path),
                    daemon=True,
                    name=f"video-proxy-{work_dir.name}",
                )
                self._workers_by_work_dir[work_key] = worker
                worker.start()
        return self.dashboard_payload(work_dir, ffprobe_path=ffprobe_path)

    def _worker_loop(self, work_dir: Path, ffmpeg_path: str, ffprobe_path: str) -> None:
        work_key = str(work_dir.resolve())
        while True:
            with self._lock:
                queue = self._queues_by_work_dir.setdefault(work_key, deque())
                jobs = self._jobs_by_work_dir.setdefault(work_key, {})
                while queue:
                    asset_id = queue.popleft()
                    candidate = jobs.get(asset_id)
                    if candidate and candidate.queue_state == PROXY_JOB_QUEUED:
                        job = candidate
                        break
                else:
                    self._process_by_work_dir.pop(work_key, None)
                    return
                job.queue_state = PROXY_JOB_RUNNING
                job.updated_at = time.time()
            try:
                self._run_job(work_dir, job, ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    job.queue_state = PROXY_JOB_CANCELLED if job.cancelled else PROXY_JOB_FAILED
                    job.error = str(exc)
                    job.updated_at = time.time()
                manifest = load_proxy_manifest(work_dir)
                if job.asset_id in manifest.get("entries", {}):
                    manifest["entries"][job.asset_id]["status"] = PROXY_FAILED
                    manifest["entries"][job.asset_id]["error"] = str(exc)
                    manifest["entries"][job.asset_id]["updated_at"] = _iso_timestamp()
                    save_proxy_manifest(work_dir, manifest)
                proxy_partial_path(work_dir, job.asset_id).unlink(missing_ok=True)
            finally:
                with self._lock:
                    self._process_by_work_dir[work_key] = None

    def _run_job(self, work_dir: Path, job: ProxyJob, *, ffmpeg_path: str, ffprobe_path: str) -> None:
        assets = {asset.asset_id: asset for asset in load_assets(work_dir) if asset.media_type == MediaType.VIDEO}
        asset = assets.get(job.asset_id)
        if asset is None:
            raise ValueError(f"Video asset not found for proxy job: {job.asset_id}")
        output_dir = proxy_directory_path(work_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        log_path = proxy_job_log_path(work_dir, job.asset_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = proxy_partial_path(work_dir, job.asset_id)
        final_path = proxy_output_path(work_dir, job.asset_id)
        partial_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        command = _build_proxy_command(asset, partial_path, ffmpeg_path=ffmpeg_path)
        with log_path.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            with self._lock:
                self._process_by_work_dir[str(work_dir.resolve())] = process
            duration_ms = max(1, int(asset.duration_ms or 1))
            assert process.stdout is not None
            for line in process.stdout:
                log_handle.write(line)
                log_handle.flush()
                self._update_job_progress(job, line=line, duration_ms=duration_ms)
                if job.cancelled and process.poll() is None:
                    process.terminate()
            return_code = process.wait()
            if job.cancelled:
                partial_path.unlink(missing_ok=True)
                raise RuntimeError("Proxy job was cancelled")
            if return_code != 0:
                partial_path.unlink(missing_ok=True)
                raise RuntimeError(f"ffmpeg exited with code {return_code}")
        validation = validate_proxy_against_asset(asset, partial_path, ffprobe_path)
        partial_path.replace(final_path)
        manifest = load_proxy_manifest(work_dir)
        entry = manifest.setdefault("entries", {}).setdefault(job.asset_id, {})
        entry.update(
            {
                "asset_id": asset.asset_id,
                "original_path": str(asset.path.resolve()),
                "proxy_path": str(final_path.relative_to(work_dir)).replace("\\", "/"),
                "source_fingerprint": build_source_fingerprint(asset),
                "profile_fingerprint": build_profile_fingerprint(),
                "status": PROXY_READY,
                "original_duration_ms": int(asset.duration_ms or 0),
                "proxy_duration_ms": int(validation["proxy_duration_ms"]),
                "original_width": int(asset.width or 0),
                "original_height": int(asset.height or 0),
                "proxy_width": int(validation["proxy_width"]),
                "proxy_height": int(validation["proxy_height"]),
                "created_at": entry.get("created_at") or _iso_timestamp(),
                "updated_at": _iso_timestamp(),
                "error": "",
                "has_audio": bool(validation["has_audio"]),
            }
        )
        save_proxy_manifest(work_dir, manifest)
        with self._lock:
            job.queue_state = PROXY_JOB_COMPLETED
            job.progress_ratio = 1.0
            job.progress_text = "100%"
            job.updated_at = time.time()

    def _update_job_progress(self, job: ProxyJob, *, line: str, duration_ms: int) -> None:
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key == "out_time_ms":
            try:
                out_time_ms = int(value)
            except ValueError:
                return
            ratio = max(0.0, min(1.0, out_time_ms / duration_ms))
            with self._lock:
                job.progress_ratio = ratio
                job.progress_text = f"{int(round(ratio * 100))}%"
                job.updated_at = time.time()
            return
        if key == "progress" and value == "end":
            with self._lock:
                job.progress_ratio = 1.0
                job.progress_text = "100%"
                job.updated_at = time.time()


def _build_proxy_command(asset: Asset, output_path: Path, *, ffmpeg_path: str) -> list[str]:
    scale = (
        f"scale={PROXY_PROFILE['scale_width']}:{PROXY_PROFILE['scale_height']}:"
        "force_original_aspect_ratio=decrease:force_divisible_by=2"
    )
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(asset.path),
        "-map_metadata",
        "-1",
        "-movflags",
        str(PROXY_PROFILE["movflags"]),
        "-vf",
        scale,
        "-c:v",
        str(PROXY_PROFILE["video_codec"]),
        "-preset",
        str(PROXY_PROFILE["preset"]),
        "-crf",
        str(PROXY_PROFILE["crf"]),
        "-pix_fmt",
        str(PROXY_PROFILE["pixel_format"]),
    ]
    if asset.has_audio:
        command.extend(
            [
                "-c:a",
                str(PROXY_PROFILE["audio_codec"]),
                "-b:a",
                str(PROXY_PROFILE["audio_bitrate"]),
            ]
        )
    else:
        command.append("-an")
    command.extend(
        [
            "-progress",
            "pipe:1",
            "-nostats",
            str(output_path),
        ]
    )
    return command


def _iso_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


proxy_queue_manager = ProxyQueueManager()
