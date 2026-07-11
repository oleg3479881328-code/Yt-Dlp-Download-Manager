from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

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
    """Adapt production episode/take dictionaries to the diversity planner.

    This function is intentionally independent from FFmpeg. The service layer can
    resolve each selected ``source_id`` back to its original take dictionary and
    render only the accepted batch.
    """

    sources: list[QuickMixSource] = []
    take_by_source_id: dict[str, dict[str, Any]] = {}
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
            path = Path(getattr(asset, "path"))
            source_group = normalize_quick_mix_source_group(path)
            if not take_id or asset_id in reserved_ids or source_group in reserved_groups:
                continue

            start_ms = max(0, int(raw_take.get("start_ms") or 0))
            end_ms = max(start_ms, int(raw_take.get("end_ms") or start_ms))
            available_ms = max(0, end_ms - start_ms)
            if available_ms <= 0:
                continue
            media_type = getattr(getattr(asset, "media_type", ""), "value", None)
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

    if not sources:
        raise ValueError("No eligible episode Takes are available for max-diversity planning")

    batch = build_diverse_batch(
        sources,
        target_duration_ms=target_duration_ms,
        output_count=output_count,
        seed=seed,
        policy=policy,
        prior_plans=prior_plans,
    )
    return EpisodePlanAdapterResult(batch=batch, take_by_source_id=take_by_source_id)


def diversity_batch_manifest(
    batch: DiversityBatch,
    *,
    generation_id: str,
    requested_duration_ms: int,
) -> dict[str, Any]:
    """Serialize a complete generation-scoped planning report."""

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
                "nearest_neighbour_distance": batch.report.nearest_neighbour_distance_by_output.get(
                    plan.output_index,
                    1.0,
                ),
                "segments": [asdict(segment) for segment in plan.segments],
            }
            for plan in batch.plans
        ],
    }
