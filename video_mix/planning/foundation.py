from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from video_mix.analysis import build_episode_groups_from_scenes
from video_mix.core.data_model.foundation import EditPlanItemRecord, EditPlanRecord
from video_mix.core.quick_mix_diversity_adapter import (
    build_episode_group_diversity_plan,
    diversity_batch_manifest,
    render_segments_for_plan,
    selected_take_manifest_for_plan,
)
from video_mix.core.quick_mix_generation import load_prior_diversity_plans
from video_mix.core.storage import load_assets, load_project
from video_mix.core.store import VideoMixFoundationStore

EDIT_PLAN_SCHEMA_VERSION = "edit-plan/v1"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_foundation_edit_plans(
    work_dir: Path,
    *,
    analysis_run_id: str,
    scene_rows: list[dict[str, Any]],
    requested_output_count: int = 5,
    target_duration_ms: int = 15_000,
    candidate_count: int | None = None,
) -> dict[str, Any]:
    resolved_work_dir = work_dir.expanduser().resolve()
    project = load_project(resolved_work_dir)
    assets = load_assets(resolved_work_dir)
    store = VideoMixFoundationStore(resolved_work_dir)
    episode_groups = build_episode_groups_from_scenes(project, assets, scene_rows)
    if not episode_groups:
        raise ValueError("No episode groups could be built from analyzed scenes.")

    planned_candidate_count = max(candidate_count or max(requested_output_count * 2, 10), requested_output_count)
    adapter = build_episode_group_diversity_plan(
        episode_groups,
        target_duration_ms=target_duration_ms,
        output_count=planned_candidate_count,
        prior_plans=tuple(load_prior_diversity_plans(resolved_work_dir)),
    )
    generation_id = f"foundation_{uuid4().hex[:12]}"
    manifest = diversity_batch_manifest(
        adapter.batch,
        generation_id=generation_id,
        requested_duration_ms=target_duration_ms,
    )
    all_candidates = manifest.get("outputs", [])
    selected_candidates = all_candidates[:requested_output_count]
    created_at = _utc_now()

    stored_plans: list[dict[str, Any]] = []
    for raw_output in selected_candidates:
        output_index = int(raw_output.get("output_index") or 0)
        diversity_plan = adapter.batch.plans[output_index - 1]
        rendered_segments = render_segments_for_plan(diversity_plan, adapter)
        selected_takes = selected_take_manifest_for_plan(diversity_plan, adapter)
        plan_id = f"plan_{generation_id}_{output_index:03d}"
        items: list[dict[str, Any]] = []
        timeline_cursor_ms = 0
        for step_index, segment in enumerate(rendered_segments, start=1):
            source_start_ms = int(segment["start_ms"])
            duration_ms = int(segment["duration_ms"])
            source_end_ms = source_start_ms + duration_ms
            timeline_start_ms = timeline_cursor_ms
            timeline_end_ms = timeline_start_ms + duration_ms
            item = EditPlanItemRecord(
                scene_id=str(segment.get("source_id") or ""),
                asset_id=str(segment["asset"].asset_id),
                source_start_ms=source_start_ms,
                source_end_ms=source_end_ms,
                timeline_start_ms=timeline_start_ms,
                timeline_end_ms=timeline_end_ms,
                role=str(segment.get("segment_kind") or "body"),
                source_type="video",
                metadata_json={
                    "source_path": str(segment["asset"].path.resolve()),
                    "duration_ms": duration_ms,
                    "output_position": step_index,
                    "source_group": str(segment.get("folder_id") or ""),
                    "content_identity": str(segment.get("content_identity") or ""),
                },
            ).model_dump()
            items.append(item)
            timeline_cursor_ms = timeline_end_ms

        record = EditPlanRecord(
            plan_id=plan_id,
            project_id=project.project_id,
            analysis_run_id=analysis_run_id,
            generation_id=generation_id,
            requested_duration_ms=target_duration_ms,
            actual_duration_ms=int(raw_output.get("generated_duration_ms") or raw_output.get("planned_duration_ms") or 0),
            output_index=output_index,
            seed=0,
            status="draft",
            warnings=list(raw_output.get("warnings") or []),
            provenance_key=f"{generation_id}:{output_index}:{analysis_run_id}",
            schema_version=EDIT_PLAN_SCHEMA_VERSION,
            items=items,
            created_at=created_at,
            updated_at=created_at,
        )
        record_payload = record.model_dump()
        store.upsert_edit_plan(
            project_id=record_payload["project_id"],
            plan_id=record_payload["plan_id"],
            analysis_run_id=record_payload["analysis_run_id"],
            generation_id=record_payload["generation_id"],
            requested_duration_ms=record_payload["requested_duration_ms"],
            actual_duration_ms=record_payload["actual_duration_ms"],
            output_index=record_payload["output_index"],
            seed=record_payload["seed"],
            status=record_payload["status"],
            warnings_json=record_payload["warnings"],
            provenance_key=record_payload["provenance_key"],
            schema_version=record_payload["schema_version"],
            items_json=record_payload["items"],
            created_at=record_payload["created_at"],
            updated_at=record_payload["updated_at"],
        )
        record_payload["selection_metadata"] = {
            "body_visual_signature": raw_output.get("body_visual_signature") or [],
            "folder_signature": raw_output.get("folder_signature") or [],
            "nearest_neighbour_distance": raw_output.get("nearest_neighbour_distance"),
            "selected_takes": selected_takes,
        }
        stored_plans.append(record_payload)

    plan_payload = {
        "schema_version": EDIT_PLAN_SCHEMA_VERSION,
        "project_id": project.project_id,
        "analysis_run_id": analysis_run_id,
        "generation_id": generation_id,
        "requested_output_count": requested_output_count,
        "candidate_count": len(all_candidates),
        "selected_count": len(stored_plans),
        "warnings": manifest.get("warnings", []),
        "candidates": all_candidates,
        "selected_plans": stored_plans,
    }
    plan_path = resolved_work_dir / "reports" / "foundation_edit_plan.json"
    plan_path.write_text(json.dumps(plan_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "generation_id": generation_id,
        "candidate_count": len(all_candidates),
        "selected_count": len(stored_plans),
        "plan_path": str(plan_path.relative_to(resolved_work_dir)).replace("\\", "/"),
        "selected_plans": stored_plans,
        "candidate_manifest": all_candidates,
        "warnings": manifest.get("warnings", []),
    }
