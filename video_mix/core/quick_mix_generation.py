from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class QuickMixGenerationPaths:
    generation_id: str
    root_dir: Path
    exports_dir: Path
    segments_dir: Path
    reports_dir: Path
    plan_path: Path
    report_path: Path

    def relative(self, path: Path, work_dir: Path) -> str:
        return str(path.relative_to(work_dir)).replace("\\", "/")


def allocate_generation_paths(
    work_dir: Path,
    *,
    generation_id: str | None = None,
    now: datetime | None = None,
) -> QuickMixGenerationPaths:
    resolved_work_dir = work_dir.resolve()
    base_id = generation_id or _timestamp_generation_id(now)
    generations_root = resolved_work_dir / "quick_mix_generations"
    generations_root.mkdir(parents=True, exist_ok=True)

    candidate_id = base_id
    suffix = 1
    while (generations_root / candidate_id).exists():
        suffix += 1
        candidate_id = f"{base_id}_{suffix:03d}"

    root_dir = generations_root / candidate_id
    exports_dir = root_dir / "exports"
    segments_dir = root_dir / "segments"
    reports_dir = root_dir / "reports"
    for path in (exports_dir, segments_dir, reports_dir):
        path.mkdir(parents=True, exist_ok=False)

    return QuickMixGenerationPaths(
        generation_id=candidate_id,
        root_dir=root_dir,
        exports_dir=exports_dir,
        segments_dir=segments_dir,
        reports_dir=reports_dir,
        plan_path=reports_dir / "quick_mix_plan.json",
        report_path=reports_dir / "quick_mix.json",
    )


def record_generation(
    work_dir: Path,
    paths: QuickMixGenerationPaths,
    *,
    requested_output_count: int,
    achieved_output_count: int,
    output_paths: list[Path],
    created_at: datetime | None = None,
) -> dict[str, Any]:
    resolved_work_dir = work_dir.resolve()
    index_path = resolved_work_dir / "reports" / "quick_mix_generations.json"
    payload = load_generation_index(resolved_work_dir)
    entries = payload["generations"]
    entry = {
        "generation_id": paths.generation_id,
        "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
        "root_path": paths.relative(paths.root_dir, resolved_work_dir),
        "plan_path": paths.relative(paths.plan_path, resolved_work_dir),
        "report_path": paths.relative(paths.report_path, resolved_work_dir),
        "requested_output_count": requested_output_count,
        "achieved_output_count": achieved_output_count,
        "output_paths": [
            paths.relative(path.resolve(), resolved_work_dir)
            for path in output_paths
        ],
    }
    entries.append(entry)
    _write_json_atomic(index_path, payload)
    return entry


def load_generation_index(work_dir: Path) -> dict[str, list[dict[str, Any]]]:
    index_path = work_dir.resolve() / "reports" / "quick_mix_generations.json"
    if not index_path.exists():
        return {"generations": []}
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"generations": []}
    entries = payload.get("generations", [])
    if not isinstance(entries, list):
        return {"generations": []}
    return {
        "generations": [
            entry for entry in entries if isinstance(entry, dict)
        ]
    }


def _timestamp_generation_id(now: datetime | None) -> str:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    return f"quick_mix_{moment.strftime('%Y%m%dT%H%M%S%fZ')}"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
