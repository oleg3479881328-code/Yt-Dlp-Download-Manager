from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DETACHED_FLAGS = 0
if os.name == "nt":
    DETACHED_FLAGS = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

MEDIA_EXTENSIONS = {
    ".mp3",
    ".m4a",
    ".wav",
    ".webm",
    ".mp4",
    ".mkv",
    ".ogg",
    ".flac",
    ".mov",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_message() -> dict[str, Any]:
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return {}
    message_length = struct.unpack("<I", raw_length)[0]
    payload = sys.stdin.buffer.read(message_length).decode("utf-8")
    return json.loads(payload)


def send_message(payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def ensure_path(path_str: str, kind: str) -> Path:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"{kind} not found: {path}")
    return path


def ensure_output_dirs(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir = output_dir / "_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return output_dir, log_dir


def registry_path(output_dir: Path) -> Path:
    _, log_dir = ensure_output_dirs(output_dir)
    return log_dir / "jobs_registry.json"


def load_registry(output_dir: Path) -> list[dict[str, Any]]:
    path = registry_path(output_dir)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_registry(output_dir: Path, jobs: list[dict[str, Any]]) -> None:
    path = registry_path(output_dir)
    path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_job(output_dir: Path, job: dict[str, Any]) -> dict[str, Any]:
    jobs = load_registry(output_dir)
    existing = {entry["jobId"]: entry for entry in jobs}
    merged = {**existing.get(job["jobId"], {}), **job}
    existing[job["jobId"]] = merged
    ordered = sorted(existing.values(), key=lambda entry: entry.get("createdAt", ""), reverse=True)
    save_registry(output_dir, ordered[:100])
    return merged


def update_job(output_dir: Path, job_id: str, **patch: Any) -> dict[str, Any]:
    jobs = load_registry(output_dir)
    existing = {entry["jobId"]: entry for entry in jobs}
    if job_id not in existing:
        raise KeyError(f"Job not found in registry: {job_id}")
    merged = {**existing[job_id], **patch, "updatedAt": utc_now()}
    existing[job_id] = merged
    ordered = sorted(existing.values(), key=lambda entry: entry.get("createdAt", ""), reverse=True)
    save_registry(output_dir, ordered[:100])
    return merged


def is_process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        check=False,
    )
    return str(pid) in result.stdout and "No tasks are running" not in result.stdout


def read_log_tail(log_path: Path, max_chars: int = 4000) -> str:
    if not log_path.exists():
        return ""
    raw = log_path.read_text(encoding="utf-8", errors="ignore")
    return raw[-max_chars:]


def extract_output_path(log_text: str, output_dir: Path) -> str | None:
    patterns = [
        r"\[download\]\s+Destination:\s+(.+)",
        r"\[Merger\]\s+Merging formats into\s+\"(.+)\"",
        r"\[ExtractAudio\]\s+Destination:\s+(.+)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, log_text)
        if matches:
            candidate = matches[-1].strip().strip('"')
            if Path(candidate).exists():
                return str(Path(candidate))
    recent_files = [
        file for file in output_dir.iterdir()
        if file.is_file() and file.suffix.lower() not in {".log", ".json", ".tmp"}
    ]
    if recent_files:
        recent_files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        return str(recent_files[0])
    return None


def summarize_status(job: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    log_path = Path(job["logPath"])
    tail = read_log_tail(log_path)
    alive = is_process_alive(job.get("pid"))
    output_path = job.get("outputPath") or extract_output_path(tail, output_dir)
    transcript_path = job.get("transcriptPath")
    status = job.get("status", "started")
    lowered_tail = tail.lower()

    if alive:
        if status == "transcribing" or "[transcribe]" in lowered_tail:
            status = "transcribing"
        else:
            status = "running"
    elif transcript_path and Path(transcript_path).exists():
        status = "completed"
    elif output_path and Path(output_path).exists() and not job.get("transcribeAudio"):
        status = "completed"
    elif "error:" in lowered_tail or "[transcribe] failed" in lowered_tail:
        status = "failed"
    elif not alive and status in {"queued", "started", "running", "transcribing"}:
        status = "finished"

    progress_matches = re.findall(r"(\d{1,3}\.\d+)%|(\d{1,3})%", tail)
    progress = job.get("progress")
    if progress_matches:
        last = progress_matches[-1]
        progress = float(last[0] or last[1])
    if status == "completed":
        progress = 100

    message = "Waiting for output"
    lines = [line.strip() for line in tail.splitlines() if line.strip()]
    if lines:
        message = lines[-1]

    updated = {
        **job,
        "status": status,
        "progress": progress,
        "outputPath": output_path,
        "lastMessage": message,
        "updatedAt": utc_now(),
    }
    return updated


def build_download_command(message: dict[str, Any]) -> tuple[list[str], Path]:
    yt_dlp = ensure_path(message["ytDlpPath"], "yt-dlp")
    output_dir = Path(message["outputDirectory"])
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = ensure_path(message["ffmpegPath"], "ffmpeg")
    mode = message.get("mode", "video")
    quality = message.get("quality", "best")
    url = message["url"]
    command = [
        str(yt_dlp),
        "--ffmpeg-location",
        str(ffmpeg.parent),
        "-o",
        str(output_dir / "%(title).180s [%(id)s].%(ext)s"),
    ]
    if mode == "audio":
        command.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0"])
    else:
        command.extend(["-f", quality or "best", "--merge-output-format", "mp4"])
    command.append(url)
    return command, output_dir


def write_log_line(log_path: Path, message: str) -> None:
    with log_path.open("a", encoding="utf-8", errors="ignore") as log_file:
        log_file.write(message.rstrip() + "\n")


def _fmt_srt_time(seconds: float, second_marks: bool) -> str:
    if second_marks:
        total = max(0, int(round(seconds)))
        hh = total // 3600
        mm = (total % 3600) // 60
        ss = total % 60
        return f"{hh:02}:{mm:02}:{ss:02},000"

    total_ms = max(0, int(seconds * 1000))
    hh = total_ms // 3_600_000
    mm = (total_ms % 3_600_000) // 60_000
    ss = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"


def transcribe_to_srt(
    input_path: Path,
    second_marks: bool = True,
    model_size: str = "small",
    language: str | None = None,
) -> tuple[Path, Path]:
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "faster-whisper is not installed. Run pip install -r requirements.txt and rebuild the native host."
        ) from exc

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    transcribe_kwargs: dict[str, Any] = {"beam_size": 5}
    if language:
        transcribe_kwargs["language"] = language
    segments, _ = model.transcribe(str(input_path), **transcribe_kwargs)

    srt_path = input_path.with_suffix(".srt")
    txt_path = input_path.with_suffix(".txt")
    idx = 1
    text_lines: list[str] = []

    with srt_path.open("w", encoding="utf-8") as srt:
        for seg in segments:
            start = _fmt_srt_time(seg.start, second_marks)
            end = _fmt_srt_time(seg.end, second_marks)
            text = seg.text.strip()
            if not text:
                continue
            srt.write(f"{idx}\n")
            srt.write(f"{start} --> {end}\n")
            srt.write(f"{text}\n\n")
            text_lines.append(text)
            idx += 1

    txt_path.write_text("\n".join(text_lines), encoding="utf-8")
    return srt_path, txt_path


def list_created_media_files(output_dir: Path, known_before: set[str], started_ts: float) -> list[Path]:
    candidates: list[Path] = []
    for file in output_dir.iterdir():
        if not file.is_file():
            continue
        if file.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        try:
            stat = file.stat()
        except OSError:
            continue
        resolved = str(file.resolve())
        if resolved not in known_before or stat.st_mtime >= started_ts - 2:
            candidates.append(file)
    candidates.sort(key=lambda item: item.stat().st_mtime)
    return candidates


def build_runner_command(job_file: Path) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--run-job", str(job_file)]
    return [sys.executable, str(Path(__file__).resolve()), "--run-job", str(job_file)]


def handle_download(message: dict[str, Any]) -> dict[str, Any]:
    command, output_dir = build_download_command(message)
    _, log_dir = ensure_output_dirs(output_dir)
    job_id = str(uuid.uuid4())
    log_path = log_dir / f"{job_id}.log"
    job_file = log_dir / f"{job_id}.job.json"
    job = {
        "jobId": job_id,
        "pid": None,
        "url": message["url"],
        "mode": message.get("mode", "video"),
        "quality": message.get("quality", "best"),
        "status": "queued",
        "progress": 0,
        "logPath": str(log_path),
        "outputDirectory": str(output_dir),
        "outputPath": None,
        "transcribeAudio": bool(message.get("transcribeAudio")),
        "transcriptSecondMarks": bool(message.get("transcriptSecondMarks", True)),
        "transcriptPath": None,
        "transcriptTextPath": None,
        "transcriptCount": 0,
        "title": message.get("title"),
        "thumbnail": message.get("thumbnail"),
        "createdAt": utc_now(),
        "updatedAt": utc_now(),
    }
    upsert_job(output_dir, job)
    job_payload = {
        "job": job,
        "message": message,
        "command": command,
    }
    job_file.write_text(json.dumps(job_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    process = subprocess.Popen(
        build_runner_command(job_file),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=DETACHED_FLAGS,
        close_fds=False,
    )
    update_job(output_dir, job_id, pid=process.pid, status="started")
    return {
        "ok": True,
        "jobId": job_id,
        "pid": process.pid,
        "message": "Download started",
        "logPath": str(log_path),
        "outputDirectory": str(output_dir),
    }


def handle_open_folder(message: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(message["outputDirectory"])
    output_dir.mkdir(parents=True, exist_ok=True)
    os.startfile(str(output_dir))
    return {"ok": True, "message": "Folder opened"}


def handle_probe(message: dict[str, Any]) -> dict[str, Any]:
    yt_dlp = ensure_path(message["ytDlpPath"], "yt-dlp")
    ffmpeg = ensure_path(message["ffmpegPath"], "ffmpeg")
    output_dir = Path(message["outputDirectory"])
    output_dir.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "message": f"OK: {yt_dlp.name}, {ffmpeg.name}, output ready"}


def handle_analyze(message: dict[str, Any]) -> dict[str, Any]:
    yt_dlp = ensure_path(message["ytDlpPath"], "yt-dlp")
    command = [
        str(yt_dlp),
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        message["url"],
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or "Analyze failed")
    info = json.loads(result.stdout)
    entries = info.get("entries") or []
    return {
        "ok": True,
        "analysis": {
            "title": info.get("title") or message["url"],
            "url": message["url"],
            "extractor": info.get("extractor_key"),
            "type": "playlist" if info.get("_type") == "playlist" or len(entries) > 1 else "single",
            "itemCount": len(entries) if entries else 1,
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "entries": [
                {
                    "title": entry.get("title") or f"Item {index}",
                    "duration": entry.get("duration"),
                    "thumbnail": entry.get("thumbnail"),
                }
                for index, entry in enumerate((entries or [])[:8], start=1)
                if entry
            ],
        },
    }


def handle_status(message: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(message["outputDirectory"])
    jobs = [summarize_status(job, output_dir) for job in load_registry(output_dir)]
    save_registry(output_dir, jobs)
    job_id = message.get("jobId")
    if job_id:
        for job in jobs:
            if job["jobId"] == job_id:
                return {"ok": True, "job": job}
        return {"ok": False, "error": "Job not found"}
    return {"ok": True, "jobs": jobs[:20]}


def handle_open_last_file(message: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(message["outputDirectory"])
    jobs = [summarize_status(job, output_dir) for job in load_registry(output_dir)]
    save_registry(output_dir, jobs)
    for job in jobs:
        output_path = job.get("outputPath")
        if output_path and Path(output_path).exists():
            os.startfile(output_path)
            return {"ok": True, "message": "Last file opened", "job": job}
    return {"ok": False, "error": "No completed file found"}


def handle_open_job_file(message: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(message["outputDirectory"])
    jobs = [summarize_status(job, output_dir) for job in load_registry(output_dir)]
    save_registry(output_dir, jobs)
    for job in jobs:
        if job["jobId"] == message["jobId"]:
            output_path = job.get("outputPath")
            if output_path and Path(output_path).exists():
                os.startfile(output_path)
                return {"ok": True, "message": "File opened", "job": job}
            return {"ok": False, "error": "Output file not found"}
    return {"ok": False, "error": "Job not found"}


def handle_open_job_folder(message: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(message["outputDirectory"])
    jobs = [summarize_status(job, output_dir) for job in load_registry(output_dir)]
    save_registry(output_dir, jobs)
    for job in jobs:
        if job["jobId"] == message["jobId"]:
            output_path = job.get("outputPath")
            if output_path and Path(output_path).exists():
                os.startfile(str(Path(output_path).parent))
                return {"ok": True, "message": "Folder opened", "job": job}
            os.startfile(str(output_dir))
            return {"ok": True, "message": "Output folder opened", "job": job}
    return {"ok": False, "error": "Job not found"}


def run_job_file(job_file_arg: str) -> None:
    job_file = Path(job_file_arg)
    payload = json.loads(job_file.read_text(encoding="utf-8"))
    job = payload["job"]
    message = payload["message"]
    command = payload["command"]
    output_dir = Path(job["outputDirectory"])
    log_path = Path(job["logPath"])
    started_ts = datetime.now().timestamp()
    known_before = {
        str(file.resolve())
        for file in output_dir.iterdir()
        if file.is_file()
    }

    update_job(output_dir, job["jobId"], status="running", progress=0)
    write_log_line(log_path, "[runner] Job started")
    with log_path.open("ab") as log_file:
        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            close_fds=False,
        )
        update_job(output_dir, job["jobId"], pid=process.pid)
        code = process.wait()
    tail = read_log_tail(log_path)
    output_path = extract_output_path(tail, output_dir)

    if code != 0:
        update_job(
            output_dir,
            job["jobId"],
            status="failed",
            progress=0,
            outputPath=output_path,
            lastMessage=f"yt-dlp failed with code {code}",
        )
        write_log_line(log_path, f"[runner] yt-dlp failed with code {code}")
        return

    created_files = list_created_media_files(output_dir, known_before, started_ts)
    if not output_path and created_files:
        output_path = str(created_files[-1])

    if not job.get("transcribeAudio"):
        update_job(
            output_dir,
            job["jobId"],
            status="completed",
            progress=100,
            outputPath=output_path,
            lastMessage="Download completed",
            pid=None,
        )
        write_log_line(log_path, "[runner] Download completed")
        return

    if not created_files and output_path and Path(output_path).exists():
        created_files = [Path(output_path)]

    if not created_files:
        update_job(
            output_dir,
            job["jobId"],
            status="failed",
            progress=100,
            outputPath=output_path,
            lastMessage="Downloaded file not found for transcription",
            pid=None,
        )
        write_log_line(log_path, "[transcribe] failed: no media file found")
        return

    update_job(
        output_dir,
        job["jobId"],
        status="transcribing",
        progress=100,
        outputPath=output_path,
        lastMessage="Transcription started",
    )
    write_log_line(log_path, f"[transcribe] started for {len(created_files)} file(s)")

    transcript_count = 0
    last_srt: str | None = None
    last_txt: str | None = None
    second_marks = bool(message.get("transcriptSecondMarks", True))
    transcription_language = str(message.get("transcriptionLanguage") or "auto").strip().lower()
    language_code = None if transcription_language == "auto" else transcription_language

    try:
        for media_path in created_files:
            write_log_line(log_path, f"[transcribe] processing: {media_path.name}")
            srt_path, txt_path = transcribe_to_srt(
                media_path,
                second_marks=second_marks,
                language=language_code,
            )
            transcript_count += 1
            last_srt = str(srt_path)
            last_txt = str(txt_path)
            write_log_line(log_path, f"[transcribe] saved: {srt_path.name}, {txt_path.name}")
    except Exception as exc:  # noqa: BLE001
        update_job(
            output_dir,
            job["jobId"],
            status="failed",
            progress=100,
            outputPath=output_path,
            transcriptPath=last_srt,
            transcriptTextPath=last_txt,
            transcriptCount=transcript_count,
            lastMessage=f"Transcription failed: {exc}",
            pid=None,
        )
        write_log_line(log_path, f"[transcribe] failed: {exc}")
        return

    update_job(
        output_dir,
        job["jobId"],
        status="completed",
        progress=100,
        outputPath=output_path,
        transcriptPath=last_srt,
        transcriptTextPath=last_txt,
        transcriptCount=transcript_count,
        lastMessage=f"Transcript created for {transcript_count} file(s)",
        pid=None,
    )
    write_log_line(log_path, f"[transcribe] completed for {transcript_count} file(s)")


def main() -> None:
    try:
        if len(sys.argv) >= 3 and sys.argv[1] == "--run-job":
            run_job_file(sys.argv[2])
            return

        message = read_message()
        action = message.get("action")
        if action == "download":
            send_message(handle_download(message))
            return
        if action == "open_folder":
            send_message(handle_open_folder(message))
            return
        if action == "probe":
            send_message(handle_probe(message))
            return
        if action == "analyze":
            send_message(handle_analyze(message))
            return
        if action == "status":
            send_message(handle_status(message))
            return
        if action == "open_last_file":
            send_message(handle_open_last_file(message))
            return
        if action == "open_job_file":
            send_message(handle_open_job_file(message))
            return
        if action == "open_job_folder":
            send_message(handle_open_job_folder(message))
            return
        send_message({"ok": False, "error": f"Unsupported action: {action}"})
    except Exception as exc:  # noqa: BLE001
        send_message({"ok": False, "error": str(exc)})


if __name__ == "__main__":
    main()
