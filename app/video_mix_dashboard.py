from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from video_mix.core.asset_scan import SKIP_DIR_NAMES, detect_media_type, scan_project_assets
from video_mix.core.export_plan import export_candidate
from video_mix.core.models import Asset, CandidateReel, CandidateStatus, Clip, MediaType, Project
from video_mix.core.review import write_review_html
from video_mix.core.storage import (
    build_summary,
    load_assets,
    load_candidates,
    load_clips,
    load_project,
    read_json,
    save_assets,
    save_candidates,
    save_summary,
    work_file,
    write_json,
)
from video_mix.proxy_pipeline import (
    PROXY_FAILED,
    PROXY_STALE,
    proxy_queue_manager,
)
from video_mix.service import scan_source_materials

ALLOWED_FILE_PREFIXES = (
    "reports/review.html",
    "reports/thumbnails/",
    "exports/",
)
PROJECT_MATERIALS_STATE_VERSION = 3
PROJECT_MATERIAL_SIMPLE_TAKE = "asset_take"
PROJECT_MATERIAL_COMPOSITE_TAKE = "video_photo_composite"
PROJECT_MATERIAL_PHOTO_MOTION_MODES = {"static", "ken_burns"}
PROJECT_MATERIAL_DEFAULT_PHOTO_DURATION_MS = 1200


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


def _show_windows_file_picker(initial_dir: str = "", title: str = "Select file") -> str:
    pwsh_path = shutil.which("pwsh")
    if not pwsh_path:
        raise HTTPException(
            status_code=500,
            detail="PowerShell 7 (pwsh) is required for the modern Windows file picker but was not found.",
        )

    script = """
Add-Type -AssemblyName PresentationFramework
$dialog = New-Object Microsoft.Win32.OpenFileDialog
$dialog.Multiselect = $false
$dialog.Title = $args[1]
if ($args[0] -and (Test-Path -LiteralPath $args[0])) {
    $resolved = Resolve-Path -LiteralPath $args[0]
    if ((Get-Item -LiteralPath $resolved).PSIsContainer) {
        $dialog.InitialDirectory = $resolved.Path
    } else {
        $dialog.InitialDirectory = Split-Path -Parent $resolved.Path
        $dialog.FileName = Split-Path -Leaf $resolved.Path
    }
}
$result = $dialog.ShowDialog()
if ($result -eq $true) {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $dialog.FileName
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
        stderr = completed.stderr.strip() or completed.stdout.strip() or "File picker failed"
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


def pick_source_media_file(initial_dir: str = "", title: str = "Select media file") -> dict[str, Any]:
    normalized_initial_dir = _normalize_initial_dir(initial_dir)
    selected_path = _show_windows_file_picker(normalized_initial_dir, title)
    if not selected_path:
        return {"ok": False, "canceled": True, "file_path": ""}
    file_path = Path(selected_path).expanduser().resolve()
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Selected file does not exist: {file_path}")
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"Selected path is not a file: {file_path}")
    return {"ok": True, "canceled": False, "file_path": str(file_path)}


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


def _load_quick_mix_summary(work_dir: Path) -> dict[str, Any] | None:
    quick_mix_path = work_dir / "reports" / "quick_mix.json"
    if not quick_mix_path.exists():
        return None
    return read_json(quick_mix_path)


def _load_zip_import_summary(work_dir: Path) -> dict[str, Any] | None:
    zip_import_path = work_dir / "reports" / "zip_import.json"
    if not zip_import_path.exists():
        return None
    return read_json(zip_import_path)


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


def _default_take_source_end_ms(asset: Asset) -> int:
    return max(int(asset.duration_ms or 0), 1000)


def _normalize_photo_motion_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "static").strip().lower().replace("-", "_")
    if mode not in PROJECT_MATERIAL_PHOTO_MOTION_MODES:
        return "static"
    return mode


def _normalize_composite_photo_asset_ids(raw_value: Any, asset_ids: set[str]) -> tuple[list[str], bool]:
    if not isinstance(raw_value, list):
        return [], True
    result: list[str] = []
    changed = False
    for item in raw_value:
        asset_id = str(item or "").strip()
        if not asset_id or asset_id not in asset_ids:
            changed = True
            continue
        result.append(asset_id)
    if len(result) != len(raw_value):
        changed = True
    return result, changed


def _take_effective_duration_ms(take: dict[str, Any], asset_lookup: dict[str, Asset]) -> int:
    take_type = str(take.get("take_type") or PROJECT_MATERIAL_SIMPLE_TAKE)
    if take_type == PROJECT_MATERIAL_COMPOSITE_TAKE:
        video_asset = asset_lookup.get(str(take.get("video_asset_id") or ""))
        video_duration_ms = int(video_asset.duration_ms or 0) if video_asset is not None else 0
        photo_duration_ms = max(0, int(take.get("photo_duration_ms") or 0))
        photo_count = len(take.get("photo_asset_ids") or [])
        return max(0, video_duration_ms + (photo_duration_ms * photo_count))
    return max(0, int(take.get("source_end_ms") or 0) - int(take.get("source_start_ms") or 0))


def _resequence_episode_takes(episode: dict[str, Any]) -> None:
    for index, take in enumerate(episode.get("takes", []), start=1):
        take["order"] = index


def _normalize_take_trim(asset: Asset, source_start_ms: int | None, source_end_ms: int | None) -> tuple[int, int]:
    max_end_ms = _default_take_source_end_ms(asset)
    start_ms = max(0, int(source_start_ms or 0))
    end_ms = int(source_end_ms or max_end_ms)
    if end_ms > max_end_ms:
        end_ms = max_end_ms
    if start_ms >= end_ms:
        start_ms = 0
        end_ms = max_end_ms
    return start_ms, end_ms


def _normalize_project_materials_state(raw_state: dict[str, Any] | None, asset_ids: set[str]) -> tuple[dict[str, Any], bool]:
    state = raw_state or {}
    changed = False
    episodes = []
    max_take_sequence = 0
    for index, raw_episode in enumerate(state.get("episodes", []), start=1):
        if not isinstance(raw_episode, dict):
            changed = True
            continue
        takes = []
        episode_takes = raw_episode.get("takes", [])
        if not isinstance(episode_takes, list):
            changed = True
            episode_takes = []
        for take_index, raw_take in enumerate(episode_takes, start=1):
            if not isinstance(raw_take, dict):
                changed = True
                continue
            take_type = str(raw_take.get("take_type") or PROJECT_MATERIAL_SIMPLE_TAKE).strip() or PROJECT_MATERIAL_SIMPLE_TAKE
            if take_type not in {PROJECT_MATERIAL_SIMPLE_TAKE, PROJECT_MATERIAL_COMPOSITE_TAKE}:
                take_type = PROJECT_MATERIAL_SIMPLE_TAKE
                changed = True
            asset_id = str(raw_take.get("asset_id", "")).strip()
            video_asset_id = str(raw_take.get("video_asset_id", "")).strip()
            photo_asset_ids, photo_ids_changed = _normalize_composite_photo_asset_ids(raw_take.get("photo_asset_ids"), asset_ids)
            changed = changed or photo_ids_changed
            if take_type == PROJECT_MATERIAL_COMPOSITE_TAKE:
                if not video_asset_id or video_asset_id not in asset_ids or not photo_asset_ids:
                    changed = True
                    continue
                take_id_seed = video_asset_id
            else:
                if not asset_id or asset_id not in asset_ids:
                    changed = True
                    continue
                take_id_seed = asset_id
            take_id = str(raw_take.get("take_id", "")).strip() or f"{take_id_seed}_take_{len(takes) + 1:03d}"
            if take_id != str(raw_take.get("take_id", "")).strip():
                changed = True
            suffix = take_id.rsplit("_take_", 1)
            if len(suffix) == 2 and suffix[1].isdigit():
                max_take_sequence = max(max_take_sequence, int(suffix[1]))
            order = int(raw_take.get("order") or take_index)
            if take_type == PROJECT_MATERIAL_COMPOSITE_TAKE:
                takes.append(
                    {
                        "take_id": take_id,
                        "take_type": PROJECT_MATERIAL_COMPOSITE_TAKE,
                        "video_asset_id": video_asset_id,
                        "photo_asset_ids": photo_asset_ids,
                        "photo_duration_ms": max(100, int(raw_take.get("photo_duration_ms") or PROJECT_MATERIAL_DEFAULT_PHOTO_DURATION_MS)),
                        "photo_motion_mode": _normalize_photo_motion_mode(raw_take.get("photo_motion_mode")),
                        "mode": "reused" if str(raw_take.get("mode", "assigned")) == "reused" else "assigned",
                        "order": order,
                    }
                )
            else:
                source_start_ms = int(raw_take.get("source_start_ms") or 0)
                source_end_ms = int(raw_take.get("source_end_ms") or 0)
                takes.append(
                    {
                        "take_id": take_id,
                        "take_type": PROJECT_MATERIAL_SIMPLE_TAKE,
                        "asset_id": asset_id,
                        "mode": "reused" if str(raw_take.get("mode", "assigned")) == "reused" else "assigned",
                        "order": order,
                        "source_start_ms": source_start_ms,
                        "source_end_ms": source_end_ms,
                    }
                )
        takes.sort(key=lambda item: (int(item.get("order") or 0), item["take_id"]))
        for resequenced_order, take in enumerate(takes, start=1):
            if int(take.get("order") or 0) != resequenced_order:
                changed = True
            take["order"] = resequenced_order
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
    raw_next_take_sequence = int(state.get("next_take_sequence") or 0)
    next_take_sequence = max(raw_next_take_sequence, max_take_sequence + 1, 1)
    normalized = {
        "version": PROJECT_MATERIALS_STATE_VERSION,
        "next_take_sequence": next_take_sequence,
        "episodes": episodes,
    }
    if state.get("version") != PROJECT_MATERIALS_STATE_VERSION:
        changed = True
    if raw_next_take_sequence != next_take_sequence:
        changed = True
    return normalized, changed


def _load_project_materials_state(work_dir: Path) -> tuple[dict[str, Any], list[Asset]]:
    assets = load_assets(work_dir)
    asset_ids = {asset.asset_id for asset in assets}
    state_path = _project_materials_state_path(work_dir)
    raw_state = read_json(state_path) if state_path.exists() else None
    state, changed = _normalize_project_materials_state(raw_state, asset_ids)
    assets_by_id = {asset.asset_id: asset for asset in assets}
    for episode in state["episodes"]:
        for take in episode.get("takes", []):
            if str(take.get("take_type") or PROJECT_MATERIAL_SIMPLE_TAKE) == PROJECT_MATERIAL_COMPOSITE_TAKE:
                take["photo_motion_mode"] = _normalize_photo_motion_mode(take.get("photo_motion_mode"))
                take["photo_duration_ms"] = max(100, int(take.get("photo_duration_ms") or PROJECT_MATERIAL_DEFAULT_PHOTO_DURATION_MS))
                continue
            asset = assets_by_id.get(take["asset_id"])
            if asset is None:
                continue
            start_ms, end_ms = _normalize_take_trim(asset, take.get("source_start_ms"), take.get("source_end_ms"))
            if start_ms != int(take.get("source_start_ms") or 0) or end_ms != int(take.get("source_end_ms") or 0):
                changed = True
            take["source_start_ms"] = start_ms
            take["source_end_ms"] = end_ms
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
            take_type = str(take.get("take_type") or PROJECT_MATERIAL_SIMPLE_TAKE)
            assigned_asset_ids = []
            if take_type == PROJECT_MATERIAL_COMPOSITE_TAKE:
                assigned_asset_ids = [
                    str(take.get("video_asset_id") or "").strip(),
                    *[str(item or "").strip() for item in take.get("photo_asset_ids") or []],
                ]
            else:
                assigned_asset_ids = [str(take.get("asset_id") or "").strip()]
            for assigned_asset_id in assigned_asset_ids:
                asset = asset_lookup.get(assigned_asset_id)
                if asset is None:
                    continue
                assignments_by_asset.setdefault(asset.asset_id, []).append(
                    {
                        "episode_id": episode["episode_id"],
                        "episode_label": episode["label"],
                        "take_id": take["take_id"],
                        "mode": take["mode"],
                        "take_type": take_type,
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
    timeline_rows = []
    for episode in state["episodes"]:
        takes = []
        for take in episode["takes"]:
            take_type = str(take.get("take_type") or PROJECT_MATERIAL_SIMPLE_TAKE)
            if take_type == PROJECT_MATERIAL_COMPOSITE_TAKE:
                video_asset = asset_lookup.get(str(take.get("video_asset_id") or ""))
                photo_assets = [
                    asset_lookup[photo_asset_id]
                    for photo_asset_id in take.get("photo_asset_ids") or []
                    if photo_asset_id in asset_lookup
                ]
                if video_asset is None or not photo_assets:
                    continue
                photo_duration_ms = max(100, int(take.get("photo_duration_ms") or PROJECT_MATERIAL_DEFAULT_PHOTO_DURATION_MS))
                effective_duration_ms = _take_effective_duration_ms(take, asset_lookup)
                takes.append(
                    {
                        "take_id": take["take_id"],
                        "take_type": PROJECT_MATERIAL_COMPOSITE_TAKE,
                        "asset_id": video_asset.asset_id,
                        "video_asset_id": video_asset.asset_id,
                        "photo_asset_ids": [asset.asset_id for asset in photo_assets],
                        "mode": take["mode"],
                        "order": int(take["order"]),
                        "file_name": video_asset.path.name,
                        "source_path": str(video_asset.path),
                        "media_type": "composite",
                        "asset_duration_ms": video_asset.duration_ms,
                        "duration_ms": effective_duration_ms,
                        "source_start_ms": 0,
                        "source_end_ms": int(video_asset.duration_ms or 0),
                        "photo_duration_ms": photo_duration_ms,
                        "photo_motion_mode": _normalize_photo_motion_mode(take.get("photo_motion_mode")),
                        "photo_count": len(photo_assets),
                        "photo_items": [
                            {
                                "asset_id": asset.asset_id,
                                "file_name": asset.path.name,
                                "source_path": str(asset.path),
                                "media_type": asset.media_type.value,
                            }
                            for asset in photo_assets
                        ],
                        "summary": {
                            "video_file_name": video_asset.path.name,
                            "photo_count": len(photo_assets),
                            "photo_duration_ms": photo_duration_ms,
                            "photo_motion_mode": _normalize_photo_motion_mode(take.get("photo_motion_mode")),
                        },
                    }
                )
                continue

            asset = asset_lookup.get(take["asset_id"])
            if asset is None:
                continue
            trimmed_duration_ms = max(0, int(take["source_end_ms"]) - int(take["source_start_ms"]))
            takes.append(
                {
                    "take_id": take["take_id"],
                    "take_type": PROJECT_MATERIAL_SIMPLE_TAKE,
                    "asset_id": take["asset_id"],
                    "mode": take["mode"],
                    "order": int(take["order"]),
                    "file_name": asset.path.name,
                    "source_path": str(asset.path),
                    "media_type": asset.media_type.value,
                    "asset_duration_ms": asset.duration_ms,
                    "duration_ms": trimmed_duration_ms,
                    "source_start_ms": int(take["source_start_ms"]),
                    "source_end_ms": int(take["source_end_ms"]),
                }
            )
        takes.sort(key=lambda item: (int(item["order"]), item["take_id"]))
        timeline_rows.append(
            {
                "episode_id": episode["episode_id"],
                "label": episode["label"],
                "position": episode["position"],
                "blocks": [
                    {
                        "take_id": take["take_id"],
                        "take_type": take["take_type"],
                        "asset_id": take["asset_id"],
                        "mode": take["mode"],
                        "order": int(take["order"]),
                        "file_name": take["file_name"],
                        "source_path": take["source_path"],
                        "media_type": take["media_type"],
                        "duration_ms": take["duration_ms"],
                        "source_start_ms": int(take["source_start_ms"]),
                        "source_end_ms": int(take["source_end_ms"]),
                        "video_asset_id": take.get("video_asset_id"),
                        "photo_asset_ids": take.get("photo_asset_ids", []),
                        "photo_duration_ms": int(take.get("photo_duration_ms") or 0),
                        "photo_motion_mode": str(take.get("photo_motion_mode") or ""),
                        "photo_count": int(take.get("photo_count") or 0),
                        "summary": take.get("summary"),
                    }
                    for take in takes
                ],
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
        "timeline": {
            "rows": timeline_rows,
            "has_blocks": any(row["blocks"] for row in timeline_rows),
        },
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


def _next_project_material_take_id(state: dict[str, Any], asset_id: str) -> str:
    next_take_sequence = int(state.get("next_take_sequence") or 1)
    state["next_take_sequence"] = next_take_sequence + 1
    return f"{asset_id}_take_{next_take_sequence:03d}"


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
            "take_id": _next_project_material_take_id(state, asset_id),
            "take_type": PROJECT_MATERIAL_SIMPLE_TAKE,
            "asset_id": asset_id,
            "mode": "reused" if existing_assignments else "assigned",
            "order": len(episode["takes"]) + 1,
            "source_start_ms": 0,
            "source_end_ms": _default_take_source_end_ms(asset_lookup[asset_id]),
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
    _resequence_episode_takes(episode)
    _save_project_materials_state(work_dir, state)
    return build_dashboard_payload(str(work_dir))


def update_project_material_take(
    raw_work_dir: str,
    episode_id: str,
    take_id: str,
    source_start_ms: int | None = None,
    source_end_ms: int | None = None,
    *,
    take_type: str | None = None,
    video_asset_id: str | None = None,
    photo_asset_ids: list[str] | None = None,
    photo_duration_ms: int | None = None,
    photo_motion_mode: str | None = None,
) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    state, assets = _load_project_materials_state(work_dir)
    asset_lookup = {asset.asset_id: asset for asset in assets}
    episode = _find_material_episode(state, episode_id)
    take = next((item for item in episode["takes"] if item["take_id"] == take_id), None)
    if take is None:
        raise HTTPException(status_code=404, detail=f"Project material take not found: {take_id}")
    normalized_take_type = str(take_type or take.get("take_type") or PROJECT_MATERIAL_SIMPLE_TAKE).strip() or PROJECT_MATERIAL_SIMPLE_TAKE
    take_order = int(take.get("order") or 1)
    take_mode = str(take.get("mode") or "assigned")

    if normalized_take_type == PROJECT_MATERIAL_COMPOSITE_TAKE:
        normalized_video_asset_id = str(video_asset_id or take.get("video_asset_id") or "").strip()
        video_asset = asset_lookup.get(normalized_video_asset_id)
        if video_asset is None:
            raise HTTPException(status_code=404, detail="Composite Take video asset was not found.")
        if video_asset.media_type != MediaType.VIDEO:
            raise HTTPException(status_code=400, detail="Composite Take base asset must be a video.")
        normalized_photo_asset_ids = [str(item or "").strip() for item in (photo_asset_ids or []) if str(item or "").strip()]
        if not normalized_photo_asset_ids:
            raise HTTPException(status_code=400, detail="Composite Take requires at least one photo asset.")
        photo_assets = []
        for photo_asset_id in normalized_photo_asset_ids:
            photo_asset = asset_lookup.get(photo_asset_id)
            if photo_asset is None:
                raise HTTPException(status_code=404, detail=f"Composite Take photo asset was not found: {photo_asset_id}")
            if photo_asset.media_type != MediaType.PHOTO:
                raise HTTPException(status_code=400, detail="Composite Take photo list can contain only photo assets.")
            photo_assets.append(photo_asset)
        take.clear()
        take.update(
            {
                "take_id": take_id,
                "take_type": PROJECT_MATERIAL_COMPOSITE_TAKE,
                "video_asset_id": normalized_video_asset_id,
                "photo_asset_ids": [asset.asset_id for asset in photo_assets],
                "photo_duration_ms": max(100, int(photo_duration_ms or PROJECT_MATERIAL_DEFAULT_PHOTO_DURATION_MS)),
                "photo_motion_mode": _normalize_photo_motion_mode(photo_motion_mode),
                "mode": take_mode,
                "order": take_order,
            }
        )
    else:
        normalized_asset_id = str(
            take.get("asset_id")
            or take.get("video_asset_id")
            or video_asset_id
            or ""
        ).strip()
        asset = asset_lookup.get(normalized_asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail=f"Project material asset not found for take: {take_id}")
        max_end_ms = _default_take_source_end_ms(asset)
        if asset.media_type not in {MediaType.VIDEO, MediaType.PHOTO}:
            raise HTTPException(status_code=400, detail="Simple Take base asset must be a video or photo.")

        start_ms = int(source_start_ms or 0)
        end_ms = int(source_end_ms or 0)
        if start_ms < 0:
            raise HTTPException(status_code=400, detail="Take trim start must be zero or greater.")
        if end_ms > max_end_ms:
            raise HTTPException(status_code=400, detail=f"Take trim end exceeds asset duration ({max_end_ms} ms).")
        if start_ms >= end_ms:
            raise HTTPException(status_code=400, detail="Take trim must satisfy start < end.")

        take["asset_id"] = normalized_asset_id
        take["take_type"] = PROJECT_MATERIAL_SIMPLE_TAKE
        take["source_start_ms"] = start_ms
        take["source_end_ms"] = end_ms
        take.pop("video_asset_id", None)
        take.pop("photo_asset_ids", None)
        take.pop("photo_duration_ms", None)
        take.pop("photo_motion_mode", None)
    _save_project_materials_state(work_dir, state)
    return build_dashboard_payload(str(work_dir))


def reorder_project_material_takes(raw_work_dir: str, episode_id: str, ordered_take_ids: list[str]) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    state, _assets = _load_project_materials_state(work_dir)
    episode = _find_material_episode(state, episode_id)
    existing_take_lookup = {take["take_id"]: take for take in episode["takes"]}
    normalized_take_ids = [str(take_id).strip() for take_id in ordered_take_ids if str(take_id).strip()]
    if len(normalized_take_ids) != len(episode["takes"]) or set(normalized_take_ids) != set(existing_take_lookup):
        raise HTTPException(status_code=400, detail="Take reorder payload must contain each Episode take exactly once.")
    episode["takes"] = [existing_take_lookup[take_id] for take_id in normalized_take_ids]
    _resequence_episode_takes(episode)
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


def _project_source_dir(work_dir: Path) -> Path:
    project = load_project(work_dir)
    source_dir = project.root_path.resolve()
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project source folder does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"Project source path is not a folder: {source_dir}")
    return source_dir


def _iter_project_files(source_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.relative_to(source_dir).parts):
            continue
        files.append(path)
    return files


def _project_file_payload(source_dir: Path, path: Path) -> dict[str, Any]:
    media_type = detect_media_type(path)
    return {
        "name": path.name,
        "relative_path": str(path.relative_to(source_dir)).replace("\\", "/"),
        "absolute_path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "media_type": media_type.value if media_type else "other",
    }


def build_project_files_payload(raw_work_dir: str) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    source_dir = _project_source_dir(work_dir)
    files = _iter_project_files(source_dir)
    return {
        "source_dir": str(source_dir),
        "file_count": len(files),
        "files": [_project_file_payload(source_dir, path) for path in files],
    }


def build_video_proxies_payload(raw_work_dir: str, *, ffprobe_path: str = "ffprobe") -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    return proxy_queue_manager.dashboard_payload(work_dir, ffprobe_path=ffprobe_path)


def create_missing_video_proxies(raw_work_dir: str, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    return proxy_queue_manager.enqueue_missing_or_stale(work_dir, ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)


def rebuild_stale_video_proxies(raw_work_dir: str, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    return proxy_queue_manager.enqueue_missing_or_stale(
        work_dir,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        only_statuses={PROXY_STALE},
    )


def retry_failed_video_proxies(raw_work_dir: str, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    return proxy_queue_manager.enqueue_missing_or_stale(
        work_dir,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        only_statuses={PROXY_FAILED},
    )


def rebuild_single_video_proxy(raw_work_dir: str, asset_id: str, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    return proxy_queue_manager.enqueue_asset(work_dir, asset_id, ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)


def cancel_video_proxy_job(raw_work_dir: str, asset_id: str) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    return proxy_queue_manager.cancel(work_dir, asset_id)


def delete_video_proxy(raw_work_dir: str, asset_id: str) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    return proxy_queue_manager.delete_proxy(work_dir, asset_id)


def cleanup_video_proxy_partials(raw_work_dir: str) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    return proxy_queue_manager.cleanup_partial_files(work_dir)


def _unique_destination_path(target_dir: Path, filename: str) -> Path:
    candidate = target_dir / Path(filename).name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while True:
        alternate = target_dir / f"{stem} ({index}){suffix}"
        if not alternate.exists():
            return alternate
        index += 1


def _unique_project_material_destination(project_root: Path, filename: str) -> Path:
    candidate = project_root / Path(filename).name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while True:
        alternate = project_root / f"{stem} ({index}){suffix}"
        if not alternate.exists():
            return alternate
        index += 1


def add_project_files(raw_work_dir: str, file_paths: list[str]) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    source_dir = _project_source_dir(work_dir)
    normalized_paths = [Path(file_path).expanduser().resolve() for file_path in file_paths if str(file_path).strip()]
    if not normalized_paths:
        raise HTTPException(status_code=400, detail="No files were provided for project import.")

    added_files: list[str] = []
    for input_path in normalized_paths:
        if not input_path.exists():
            raise HTTPException(status_code=404, detail=f"Selected file does not exist: {input_path}")
        if not input_path.is_file():
            raise HTTPException(status_code=400, detail=f"Selected path is not a file: {input_path}")
        destination = _unique_destination_path(source_dir, input_path.name)
        shutil.copy2(input_path, destination)
        added_files.append(str(destination.relative_to(source_dir)).replace("\\", "/"))

    return {
        "ok": True,
        "added_files": added_files,
        "project_files": build_project_files_payload(str(work_dir)),
        "source_scan": scan_source_materials(str(source_dir)),
    }


def remove_project_file(raw_work_dir: str, relative_path: str) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    source_dir = _project_source_dir(work_dir)
    normalized_relative = relative_path.replace("\\", "/").lstrip("/")
    if not normalized_relative:
        raise HTTPException(status_code=400, detail="Project file path is empty.")
    target = (source_dir / normalized_relative).resolve()
    if source_dir not in target.parents:
        raise HTTPException(status_code=403, detail="Requested project file escapes the source folder.")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Project file does not exist: {normalized_relative}")
    if not target.is_file():
        raise HTTPException(status_code=400, detail=f"Project path is not a file: {normalized_relative}")
    target.unlink()

    parent = target.parent
    while parent != source_dir and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent

    return {
        "ok": True,
        "removed_file": normalized_relative,
        "project_files": build_project_files_payload(str(work_dir)),
        "source_scan": scan_source_materials(str(source_dir)),
    }


def add_external_project_materials(raw_work_dir: str, episode_id: str, file_paths: list[str]) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    if not file_paths:
        raise HTTPException(status_code=400, detail="No files were provided.")

    project = load_project(work_dir)
    project_root = project.root_path.expanduser().resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise HTTPException(status_code=404, detail=f"Project source folder does not exist: {project_root}")

    written_paths: list[Path] = []
    for raw_path in file_paths:
        input_path = Path(str(raw_path or "").strip()).expanduser().resolve()
        if not input_path.exists() or not input_path.is_file():
            raise HTTPException(status_code=404, detail=f"Dragged file was not found: {input_path}")
        destination = _unique_project_material_destination(project_root, input_path.name)
        shutil.copy2(input_path, destination)
        written_paths.append(destination)

    assets = scan_project_assets(project)
    save_assets(work_dir, assets)
    clips = load_clips(work_dir)
    candidates = load_candidates(work_dir)
    save_summary(work_dir, build_summary(project, assets, clips, candidates))

    state, _ = _load_project_materials_state(work_dir)
    _find_material_episode(state, episode_id)
    asset_lookup = {str(asset.path.resolve()): asset for asset in assets}
    assignments_by_asset = _asset_assignment_rows(state, assets)
    for path in written_paths:
        asset = asset_lookup.get(str(path.resolve()))
        if asset is None:
            continue
        episode = _find_material_episode(state, episode_id)
        existing_assignments = assignments_by_asset.get(asset.asset_id, [])
        episode["takes"].append(
            {
                "take_id": _next_project_material_take_id(state, asset.asset_id),
                "take_type": PROJECT_MATERIAL_SIMPLE_TAKE,
                "asset_id": asset.asset_id,
                "mode": "reused" if existing_assignments else "assigned",
                "order": len(episode["takes"]) + 1,
                "source_start_ms": 0,
                "source_end_ms": _default_take_source_end_ms(asset),
            }
        )
        assignments_by_asset.setdefault(asset.asset_id, []).append(
            {"episode_id": episode["episode_id"], "episode_label": episode["label"], "take_id": episode["takes"][-1]["take_id"]}
        )
    _save_project_materials_state(work_dir, state)
    return build_dashboard_payload(str(work_dir))


def build_dashboard_payload(raw_work_dir: str) -> dict[str, Any]:
    work_dir = resolve_work_dir(raw_work_dir)
    project = load_project(work_dir)
    assets = load_assets(work_dir)
    clips = load_clips(work_dir)
    candidates = load_candidates(work_dir)
    summary = _load_summary(work_dir, project, assets, clips, candidates)
    quick_mix = _load_quick_mix_summary(work_dir)
    zip_import = _load_zip_import_summary(work_dir)
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
        "quick_mix": quick_mix,
        "zip_import": zip_import,
        "project_files": build_project_files_payload(str(work_dir)),
        "video_proxies": build_video_proxies_payload(str(work_dir)),
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
