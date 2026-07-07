from __future__ import annotations

import os
import shutil
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
    write_json,
)

ALLOWED_FILE_PREFIXES = (
    "reports/review.html",
    "reports/thumbnails/",
    "exports/",
)
PROJECT_MATERIALS_STATE_VERSION = 1


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


def _show_windows_folder_picker(initial_dir: str = "", title: str = "Select folder") -> str:
    pwsh_path = shutil.which("pwsh")
    if not pwsh_path:
        raise HTTPException(
            status_code=500,
            detail="PowerShell 7 (pwsh) is required for the modern Windows folder picker but was not found.",
        )

    script = """
Add-Type -AssemblyName PresentationFramework
$dialog = New-Object Microsoft.Win32.OpenFolderDialog
$dialog.Multiselect = $false
$dialog.Title = $args[1]
if ($args[0] -and (Test-Path -LiteralPath $args[0])) {
    $dialog.InitialDirectory = (Resolve-Path -LiteralPath $args[0]).Path
}
$result = $dialog.ShowDialog()
if ($result -eq $true) {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $dialog.FolderName
}
""".strip()
    completed = subprocess.run(
        [pwsh_path, "-NoProfile", "-STA", "-Command", script, initial_dir, title],
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
    selected_path = _show_windows_folder_picker(normalized_initial_dir, "Select VIDEO MIX work_dir")
    if not selected_path:
        return {"ok": False, "canceled": True, "work_dir": ""}
    work_dir = resolve_work_dir(selected_path)
    return {"ok": True, "canceled": False, "work_dir": str(work_dir)}


def pick_source_materials_dir(initial_dir: str = "") -> dict[str, Any]:
    normalized_initial_dir = _normalize_initial_dir(initial_dir)
    selected_path = _show_windows_folder_picker(normalized_initial_dir, "Select source materials folder")
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


def _project_materials_state_path(work_dir: Path) -> Path:
    return work_file(work_dir, "project_materials_state.json")


def _default_material_episode(position: int) -> dict[str, Any]:
    return {
        "episode_id": f"episode_{position:03d}",
        "label": f"Episode {position}",
        "position": position,
        "takes": [],
    }


def _normalize_project_materials_state(raw_state: dict[str, Any] | None, asset_ids: set[str]) -> tuple[dict[str, Any], bool]:
    state = raw_state or {}
    changed = False
    episodes = []
    for index, raw_episode in enumerate(state.get("episodes", []), start=1):
        if not isinstance(raw_episode, dict):
            changed = True
            continue
        takes = []
        for raw_take in raw_episode.get("takes", []):
            if not isinstance(raw_take, dict):
                changed = True
                continue
            asset_id = str(raw_take.get("asset_id", "")).strip()
            if not asset_id or asset_id not in asset_ids:
                changed = True
                continue
            takes.append(
                {
                    "take_id": str(raw_take.get("take_id", "")).strip() or f"{asset_id}_take_{len(takes) + 1:03d}",
                    "asset_id": asset_id,
                    "mode": "reused" if str(raw_take.get("mode", "assigned")) == "reused" else "assigned",
                }
            )
        episodes.append(
            {
                "episode_id": str(raw_episode.get("episode_id", "")).strip() or f"episode_{index:03d}",
                "label": str(raw_episode.get("label", "")).strip() or f"Episode {index}",
                "position": int(raw_episode.get("position") or index),
                "takes": takes,
            }
        )
    episodes.sort(key=lambda episode: episode["position"])
    if not episodes:
        episodes = [_default_material_episode(1)]
        changed = True
    normalized = {
        "version": PROJECT_MATERIALS_STATE_VERSION,
        "episodes": episodes,
    }
    if state.get("version") != PROJECT_MATERIALS_STATE_VERSION:
        changed = True
    return normalized, changed


def _load_project_materials_state(work_dir: Path) -> tuple[dict[str, Any], list[Asset]]:
    assets = load_assets(work_dir)
    asset_ids = {asset.asset_id for asset in assets}
    state_path = _project_materials_state_path(work_dir)
    raw_state = read_json(state_path) if state_path.exists() else None
    state, changed = _normalize_project_materials_state(raw_state, asset_ids)
    if changed or not state_path.exists():
        write_json(state_path, state)
    return state, assets


def _save_project_materials_state(work_dir: Path, state: dict[str, Any]) -> None:
    write_json(_project_materials_state_path(work_dir), state)


def _find_material_episode(state: dict[str, Any], episode_id: str) -> dict[str, Any]:
    for episode in state["episodes"]:
        if episode["episode_id"] == episode_id:
            return episode
    raise HTTPException(status_code=404, detail=f"Project materials episode not found: {episode_id}")


def _asset_assignment_rows(state: dict[str, Any], assets: list[Asset]) -> dict[str, list[dict[str, Any]]]:
    asset_lookup = {asset.asset_id: asset for asset in assets}
    assignments_by_asset: dict[str, list[dict[str, Any]]] = {asset.asset_id: [] for asset in assets}
    for episode in state["episodes"]:
        for take in episode.get("takes", []):
            asset = asset_lookup.get(take["asset_id"])
            if asset is None:
                continue
            assignments_by_asset.setdefault(asset.asset_id, []).append(
                {
                    "episode_id": episode["episode_id"],
                    "episode_label": episode["label"],
                    "take_id": take["take_id"],
                    "mode": take["mode"],
                }
            )
    return assignments_by_asset


def build_project_materials_payload(raw_work_dir: str) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    state, assets = _load_project_materials_state(work_dir)
    assignments_by_asset = _asset_assignment_rows(state, assets)
    asset_lookup = {asset.asset_id: asset for asset in assets}

    asset_cards = []
    for asset in sorted(assets, key=lambda item: item.path.name.lower()):
        assignments = assignments_by_asset.get(asset.asset_id, [])
        assignment_state = "unassigned"
        if len(assignments) == 1:
            assignment_state = "assigned"
        elif len(assignments) > 1:
            assignment_state = "reused"
        asset_cards.append(
            {
                "asset_id": asset.asset_id,
                "file_name": asset.path.name,
                "source_path": str(asset.path),
                "media_type": asset.media_type.value,
                "duration_ms": asset.duration_ms,
                "has_audio": asset.has_audio,
                "assignment_state": assignment_state,
                "assignments": assignments,
            }
        )

    episodes = []
    for episode in state["episodes"]:
        takes = []
        for take in episode["takes"]:
            asset = asset_lookup.get(take["asset_id"])
            if asset is None:
                continue
            takes.append(
                {
                    "take_id": take["take_id"],
                    "asset_id": take["asset_id"],
                    "mode": take["mode"],
                    "file_name": asset.path.name,
                    "media_type": asset.media_type.value,
                    "duration_ms": asset.duration_ms,
                }
            )
        episodes.append(
            {
                "episode_id": episode["episode_id"],
                "label": episode["label"],
                "position": episode["position"],
                "takes": takes,
            }
        )

    return {
        "episodes": episodes,
        "assets": asset_cards,
        "counts": {
            "all": len(asset_cards),
            "unassigned": sum(asset["assignment_state"] == "unassigned" for asset in asset_cards),
            "assigned": sum(asset["assignment_state"] == "assigned" for asset in asset_cards),
            "reused": sum(asset["assignment_state"] == "reused" for asset in asset_cards),
        },
    }


def add_project_materials_episode(raw_work_dir: str, label: str = "") -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    state, _assets = _load_project_materials_state(work_dir)
    next_position = max((int(episode["position"]) for episode in state["episodes"]), default=0) + 1
    state["episodes"].append(
        {
            "episode_id": f"episode_{next_position:03d}",
            "label": label.strip() or f"Episode {next_position}",
            "position": next_position,
            "takes": [],
        }
    )
    _save_project_materials_state(work_dir, state)
    return build_dashboard_payload(str(work_dir))


def _next_project_material_take_id(episode: dict[str, Any], asset_id: str) -> str:
    return f"{asset_id}_take_{len(episode.get('takes', [])) + 1:03d}"


def assign_project_material(raw_work_dir: str, asset_id: str, episode_id: str, reuse: bool = False) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    state, assets = _load_project_materials_state(work_dir)
    asset_lookup = {asset.asset_id: asset for asset in assets}
    if asset_id not in asset_lookup:
        raise HTTPException(status_code=404, detail=f"Project material asset not found: {asset_id}")
    episode = _find_material_episode(state, episode_id)
    assignments_by_asset = _asset_assignment_rows(state, assets)
    existing_assignments = assignments_by_asset.get(asset_id, [])
    if existing_assignments and not reuse:
        raise HTTPException(
            status_code=409,
            detail="Asset is already assigned. Use explicit reuse to place the same source again.",
        )
    episode["takes"].append(
        {
            "take_id": _next_project_material_take_id(episode, asset_id),
            "asset_id": asset_id,
            "mode": "reused" if existing_assignments else "assigned",
        }
    )
    _save_project_materials_state(work_dir, state)
    return build_dashboard_payload(str(work_dir))


def unassign_project_material(raw_work_dir: str, episode_id: str, take_id: str) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    state, _assets = _load_project_materials_state(work_dir)
    episode = _find_material_episode(state, episode_id)
    before = len(episode["takes"])
    episode["takes"] = [take for take in episode["takes"] if take["take_id"] != take_id]
    if len(episode["takes"]) == before:
        raise HTTPException(status_code=404, detail=f"Project material take not found: {take_id}")
    _save_project_materials_state(work_dir, state)
    return build_dashboard_payload(str(work_dir))


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
        "project_materials": build_project_materials_payload(str(work_dir)),
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
