from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .quick_mix_diversity import (
    DiversityBatch,
    DiversityPlan,
    DiversityPolicy,
    build_diverse_batch,
)
from .quick_mix_planner import QuickMixSource, normalize_quick_mix_source_group


@dataclass(frozen=True, slots=True)
class EpisodePlanAdapterResult:
    batch: DiversityBatch
    take_by_source_id: dict[str, dict[str, Any]]
    source_by_source_id: dict[str, QuickMixSource]


def build_episode_group_diversity_plan(
    episode_groups: Sequence[dict[str, Any]],
    *,
    target_duration_ms: int,
    output_count: int,
    seed: int | None = None,
    policy: DiversityPolicy | None = None,
    prior_plans: Sequence[DiversityPlan] = (),
    reserved_asset_ids: set[str] | None = None,
    reserved_source_groups: set[str] | None = None,
) -> EpisodePlanAdapterResult:
    sources: list[QuickMixSource] = []
    take_by_source_id: dict[str, dict[str, Any]] = {}
    source_by_source_id: dict[str, QuickMixSource] = {}
    reserved_ids = set(reserved_asset_ids or ())
    reserved_groups = set(reserved_source_groups or ())

    for group in episode_groups:
        episode_id = str(group.get("episode_id") or "")
        episode_label = str(group.get("episode_label") or episode_id)
        for raw_take in group.get("takes", []):
            if not isinstance(raw_take, dict):
                continue
            asset = raw_take.get("asset")
            if asset is None:
                continue
            take_id = str(raw_take.get("take_id") or "")
            asset_id = str(getattr(asset, "asset_id", "") or "")
            path = Path(asset.path)
            source_group = normalize_quick_mix_source_group(path)
            if (
                not take_id
                or asset_id in reserved_ids
                or source_group in reserved_groups
            ):
                continue

            start_ms = max(0, int(raw_take.get("start_ms") or 0))
            end_ms = max(start_ms, int(raw_take.get("end_ms") or start_ms))
            available_ms = max(0, end_ms - start_ms)
            if available_ms <= 0:
                continue
            media_type = getattr(
                getattr(asset, "media_type", ""),
                "value",
                None,
            )
            media_type = str(media_type or getattr(asset, "media_type", ""))
            source = QuickMixSource(
                source_id=take_id,
                path=path,
                media_type=media_type,
                duration_ms=available_ms,
                source_start_ms=start_ms,
                base_source_id=asset_id or take_id,
                metadata={
                    "folder_group": episode_id or episode_label,
                    "episode_id": episode_id,
                    "episode_label": episode_label,
                    "take_index": int(raw_take.get("take_index") or 0),
                    "marker_split": bool(raw_take.get("marker_split")),
                },
            )
            sources.append(source)
            take_by_source_id[source.source_id] = raw_take
            source_by_source_id[source.source_id] = source

    if not sources:
        raise ValueError(
            "No eligible episode Takes are available for max-diversity planning"
        )

    batch = build_diverse_batch(
        sources,
        target_duration_ms=target_duration_ms,
        output_count=output_count,
        seed=seed,
        policy=policy,
        prior_plans=prior_plans,
    )
    return EpisodePlanAdapterResult(
        batch=batch,
        take_by_source_id=take_by_source_id,
        source_by_source_id=source_by_source_id,
    )


def diversity_batch_manifest(
    batch: DiversityBatch,
    *,
    generation_id: str,
    requested_duration_ms: int,
) -> dict[str, Any]:
    return {
        "generation_id": generation_id,
        "planner": "max_min_farthest_point",
        "requested_duration_ms": requested_duration_ms,
        "requested_output_count": batch.report.requested_output_count,
        "achieved_output_count": batch.report.achieved_output_count,
        "warnings": list(batch.warnings),
        "diversity": asdict(batch.report),
        "outputs": [
            {
                "output_index": plan.output_index,
                "target_duration_ms": plan.target_duration_ms,
                "planned_duration_ms": plan.planned_duration_ms,
                "body_visual_signature": list(plan.body_signature),
                "folder_signature": list(plan.folder_signature),
                "nearest_neighbour_distance": (
                    batch.report.nearest_neighbour_distance_by_output.get(
                        plan.output_index,
                        1.0,
                    )
                ),
                "segments": [
                    {"segment_kind": "body", **asdict(segment)}
                    for segment in plan.segments
                ],
            }
            for plan in batch.plans
        ],
    }


def render_segments_for_plan(
    plan: DiversityPlan,
    adapter: EpisodePlanAdapterResult,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for step_index, segment in enumerate(plan.segments):
        raw_take = adapter.take_by_source_id.get(segment.source_id)
        if raw_take is None:
            raise KeyError(
                "Planned source_id is missing from the production take lookup: "
                f"{segment.source_id}"
            )
        asset = raw_take.get("asset")
        if asset is None:
            raise ValueError(
                f"Planned source_id has no renderable asset: {segment.source_id}"
            )
        result.append(
            {
                "asset": asset,
                "start_ms": segment.source_start_ms,
                "duration_ms": segment.duration_ms,
                "step_index": step_index,
                "segment_kind": "body",
                "source_id": segment.source_id,
                "folder_id": segment.folder_id,
            }
        )
    return result


def selected_take_manifest_for_plan(
    plan: DiversityPlan,
    adapter: EpisodePlanAdapterResult,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for segment in plan.segments:
        raw_take = adapter.take_by_source_id[segment.source_id]
        source = adapter.source_by_source_id[segment.source_id]
        asset = raw_take["asset"]
        result.append(
            {
                "episode_id": str(source.metadata.get("episode_id") or ""),
                "episode_label": str(source.metadata.get("episode_label") or ""),
                "take_id": source.source_id,
                "take_index": int(source.metadata.get("take_index") or 0),
                "marker_split": bool(source.metadata.get("marker_split")),
                "asset_id": str(getattr(asset, "asset_id", "") or ""),
                "media_type": source.media_type,
                "normalized_source_group": source.source_group,
                "source_path": str(source.path.resolve()),
                "source_start_ms": source.source_start_ms,
                "source_end_ms": source.source_start_ms
                + int(source.duration_ms or segment.duration_ms),
                "render_start_ms": segment.source_start_ms,
                "render_end_ms": segment.source_start_ms + segment.duration_ms,
            }
        )
    return result
