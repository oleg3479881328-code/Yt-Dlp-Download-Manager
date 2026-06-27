from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from video_mix.core.export_plan import export_candidate
from video_mix.core.models import Asset, CandidateReel, CandidateStatus, Clip, Project
from video_mix.core.review import write_review_html
from video_mix.core.storage import (
    build_summary,
    load_assets,
    load_candidates,
    load_clips,
    load_project,
    read_json,
    save_candidates,
    save_summary,
    work_file,
)

ALLOWED_FILE_PREFIXES = (
    "reports/review.html",
    "reports/thumbnails/",
    "exports/",
)


def resolve_work_dir(raw_work_dir: str) -> Path:
    work_dir = Path(raw_work_dir).expanduser().resolve()
    required = [
        work_file(work_dir, "project.json"),
        work_file(work_dir, "assets.json"),
        work_file(work_dir, "clips.json"),
        work_file(work_dir, "candidates.json"),
    ]
    missing = [path.name for path in required if not path.exists()]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"VIDEO MIX work_dir is missing required files: {', '.join(missing)}",
        )
    return work_dir


def _normalize_initial_dir(initial_dir: str) -> str:
    if not initial_dir:
        return ""
    path = Path(initial_dir).expanduser()
    if path.is_file():
        path = path.parent
    try:
        resolved = path.resolve()
    except OSError:
        return ""
    return str(resolved) if resolved.exists() else ""


def _show_windows_folder_picker(initial_dir: str = "") -> str:
    script = """
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = 'Select VIDEO MIX work_dir'
$dialog.ShowNewFolderButton = $false
if ($args[0]) { $dialog.SelectedPath = $args[0] }
$result = $dialog.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $dialog.SelectedPath
}
""".strip()
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script, initial_dir],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "Folder picker failed"
        raise HTTPException(status_code=500, detail=stderr)
    return completed.stdout.strip()


def pick_dashboard_work_dir(initial_dir: str = "") -> dict[str, Any]:
    normalized_initial_dir = _normalize_initial_dir(initial_dir)
    selected_path = _show_windows_folder_picker(normalized_initial_dir)
    if not selected_path:
        return {"ok": False, "canceled": True, "work_dir": ""}
    work_dir = resolve_work_dir(selected_path)
    return {"ok": True, "canceled": False, "work_dir": str(work_dir)}


def pick_source_materials_dir(initial_dir: str = "") -> dict[str, Any]:
    normalized_initial_dir = _normalize_initial_dir(initial_dir)
    selected_path = _show_windows_folder_picker(normalized_initial_dir)
    if not selected_path:
        return {"ok": False, "canceled": True, "source_dir": ""}
    source_dir = Path(selected_path).expanduser().resolve()
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail=f"Source folder does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"Source folder is not a directory: {source_dir}")
    return {"ok": True, "canceled": False, "source_dir": str(source_dir)}


def resolve_relative_work_path(raw_work_dir: str, relative_path: str) -> Path:
    work_dir = resolve_work_dir(raw_work_dir)
    normalized_relative = relative_path.replace("\\", "/").lstrip("/")
    if not any(
        normalized_relative == allowed_prefix or normalized_relative.startswith(allowed_prefix)
        for allowed_prefix in ALLOWED_FILE_PREFIXES
    ):
        raise HTTPException(status_code=403, detail="Requested VIDEO MIX file is outside the allowed dashboard artifacts")

    path = (work_dir / normalized_relative).resolve()
    if work_dir not in path.parents and path != work_dir:
        raise HTTPException(status_code=403, detail="Requested path escapes the VIDEO MIX work_dir")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Requested VIDEO MIX file was not found")
    return path


def _load_summary(work_dir: Path, project: Project, assets: list[Asset], clips: list[Clip], candidates: list[CandidateReel]) -> dict[str, Any]:
    summary_path = work_file(work_dir, "summary.json")
    if summary_path.exists():
        return read_json(summary_path)
    summary = build_summary(project, assets, clips, candidates)
    save_summary(work_dir, summary)
    return summary


def _thumbnail_relative_path(work_dir: Path, clip_id: str) -> str | None:
    thumbnail_path = work_dir / "reports" / "thumbnails" / f"{clip_id}.jpg"
    if thumbnail_path.exists():
        return str(thumbnail_path.relative_to(work_dir)).replace("\\", "/")
    return None


def _candidate_export_paths(work_dir: Path, candidate_id: str) -> list[str]:
    export_dir = work_dir / "exports"
    if not export_dir.exists():
        return []
    matches = sorted(export_dir.glob(f"*{candidate_id}*"))
    return [str(path.relative_to(work_dir)).replace("\\", "/") for path in matches if path.is_file()]


def _status_totals(candidates: list[CandidateReel]) -> dict[str, int]:
    counts = {status.value: 0 for status in CandidateStatus}
    for candidate in candidates:
        counts[candidate.status.value] = counts.get(candidate.status.value, 0) + 1
    return counts


def _build_candidate_card(work_dir: Path, candidate: CandidateReel, clip_lookup: dict[str, Clip], asset_lookup: dict[str, Asset]) -> dict[str, Any]:
    source_filenames: list[str] = []
    source_clips: list[dict[str, Any]] = []
    for timeline_clip in candidate.video_clips:
        clip = clip_lookup.get(timeline_clip.clip_id)
        if clip is None:
            continue
        asset = asset_lookup.get(clip.asset_id)
        source_name = (asset.path if asset else clip.source_path).name
        if source_name not in source_filenames:
            source_filenames.append(source_name)
        source_clips.append(
            {
                "clip_id": clip.clip_id,
                "source_filename": source_name,
                "start_ms": clip.source_start_ms,
                "end_ms": clip.source_end_ms,
                "duration_ms": clip.duration_ms,
                "tags": clip.tags,
            }
        )

    first_clip_id = candidate.video_clips[0].clip_id if candidate.video_clips else None
    thumbnail_path = _thumbnail_relative_path(work_dir, first_clip_id) if first_clip_id else None
    export_paths = _candidate_export_paths(work_dir, candidate.candidate_id)
    return {
        "candidate_id": candidate.candidate_id,
        "template_id": candidate.template_id,
        "status": candidate.status.value,
        "score": candidate.score,
        "duration_ms": candidate.duration_ms,
        "warnings": candidate.warnings,
        "review_notes": candidate.review_notes,
        "source_filenames": source_filenames,
        "source_clips": source_clips,
        "thumbnail_path": thumbnail_path,
        "export_paths": export_paths,
        "approve_command": f'python -m video_mix.cli approve "{work_dir}" {candidate.candidate_id}',
        "reject_command": f'python -m video_mix.cli reject "{work_dir}" {candidate.candidate_id}',
    }


def build_dashboard_payload(raw_work_dir: str) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    project = load_project(work_dir)
    assets = load_assets(work_dir)
    clips = load_clips(work_dir)
    candidates = load_candidates(work_dir)
    summary = _load_summary(work_dir, project, assets, clips, candidates)
    clip_lookup = {clip.clip_id: clip for clip in clips}
    asset_lookup = {asset.asset_id: asset for asset in assets}
    review_path = work_dir / "reports" / "review.html"
    exports_dir = work_dir / "exports"

    return {
        "project": {
            "project_id": project.project_id,
            "name": project.name,
            "industry_pack": project.industry_pack,
            "root_path": str(project.root_path),
        },
        "work_dir": str(work_dir),
        "summary": {
            **summary,
            "status_totals": _status_totals(candidates),
        },
        "pipeline": [
            {"id": "assets", "label": "Assets", "count": len(assets), "state": "ready" if assets else "empty"},
            {"id": "clips", "label": "Clips", "count": len(clips), "state": "ready" if clips else "empty"},
            {"id": "candidates", "label": "Candidates", "count": len(candidates), "state": "ready" if candidates else "empty"},
            {
                "id": "review",
                "label": "Review",
                "count": 1 if review_path.exists() else 0,
                "state": "ready" if review_path.exists() else "missing",
            },
            {
                "id": "approval",
                "label": "Approval",
                "count": summary.get("approved_candidate_count", 0),
                "state": "ready" if summary.get("approved_candidate_count", 0) else "pending",
            },
            {
                "id": "export",
                "label": "Export",
                "count": summary.get("exported_candidate_count", 0),
                "state": "ready" if summary.get("exported_candidate_count", 0) else "pending",
            },
        ],
        "artifacts": {
            "review_available": review_path.exists(),
            "review_path": str(review_path),
            "review_relative_path": "reports/review.html",
            "thumbnails_dir": str(work_dir / "reports" / "thumbnails"),
            "exports_dir": str(exports_dir),
            "exports_exist": exports_dir.exists(),
        },
        "candidates": [
            _build_candidate_card(work_dir, candidate, clip_lookup, asset_lookup)
            for candidate in candidates
        ],
    }


def _persist_dashboard_state(
    work_dir: Path,
    candidates: list[CandidateReel],
    ffmpeg_path: str = "ffmpeg",
    regenerate_thumbnails: bool = True,
) -> None:
    project = load_project(work_dir)
    assets = load_assets(work_dir)
    clips = load_clips(work_dir)
    save_candidates(work_dir, candidates)
    save_summary(work_dir, build_summary(project, assets, clips, candidates))
    write_review_html(
        project,
        candidates,
        clips,
        assets,
        work_dir,
        ffmpeg_path=ffmpeg_path,
        regenerate_thumbnails=regenerate_thumbnails,
    )


def update_candidate_status(raw_work_dir: str, candidate_id: str, status: CandidateStatus, note: str = "") -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    candidates = load_candidates(work_dir)
    target = next((candidate for candidate in candidates if candidate.candidate_id == candidate_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Candidate not found: {candidate_id}")
    target.status = status
    target.review_notes = note
    _persist_dashboard_state(work_dir, candidates, regenerate_thumbnails=False)
    return build_dashboard_payload(str(work_dir))


def bulk_update_candidate_status(
    raw_work_dir: str,
    candidate_ids: list[str],
    status: CandidateStatus,
    note: str = "",
) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    normalized_ids = [candidate_id for candidate_id in dict.fromkeys(candidate_ids) if candidate_id]
    if not normalized_ids:
        raise HTTPException(status_code=400, detail="No candidate ids were provided for the bulk action.")

    candidates = load_candidates(work_dir)
    candidate_lookup = {candidate.candidate_id: candidate for candidate in candidates}
    missing = [candidate_id for candidate_id in normalized_ids if candidate_id not in candidate_lookup]
    if missing:
        raise HTTPException(status_code=404, detail=f"Candidate not found: {', '.join(missing)}")

    for candidate_id in normalized_ids:
        candidate = candidate_lookup[candidate_id]
        candidate.status = status
        candidate.review_notes = note or candidate.review_notes

    _persist_dashboard_state(work_dir, candidates, regenerate_thumbnails=False)
    return build_dashboard_payload(str(work_dir))


def export_approved_candidates(raw_work_dir: str, ffmpeg_path: str = "ffmpeg") -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    project = load_project(work_dir)
    clips = load_clips(work_dir)
    candidates = load_candidates(work_dir)
    approved = [candidate for candidate in candidates if candidate.status == CandidateStatus.APPROVED]
    if not approved:
        raise HTTPException(status_code=400, detail="No approved candidates found. Approve at least one candidate first.")

    exported_paths: list[str] = []
    for candidate in approved:
        plan = export_candidate(
            project_name=project.name,
            pack_id=project.industry_pack,
            candidate=candidate,
            clips=clips,
            work_dir=work_dir,
            ffmpeg_path=ffmpeg_path,
        )
        candidate.status = CandidateStatus.EXPORTED
        candidate.review_notes = f"{candidate.review_notes}\nexported:{plan.output_path.name}".strip()
        exported_paths.append(str(plan.output_path.relative_to(work_dir)).replace("\\", "/"))

    _persist_dashboard_state(work_dir, candidates, ffmpeg_path=ffmpeg_path)
    return {
        "ok": True,
        "work_dir": str(work_dir),
        "exported_paths": exported_paths,
        "dashboard": build_dashboard_payload(str(work_dir)),
    }


def open_dashboard_target(raw_work_dir: str, target: str) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    targets = {
        "work_dir": work_dir,
        "review": work_dir / "reports" / "review.html",
        "exports": work_dir / "exports",
    }
    path = targets.get(target)
    if path is None:
        raise HTTPException(status_code=400, detail=f"Unsupported VIDEO MIX open target: {target}")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"VIDEO MIX target does not exist yet: {target}")
    os.startfile(str(path))
    return {"ok": True, "opened": str(path)}
