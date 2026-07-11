from pathlib import Path
from types import SimpleNamespace

from video_mix.core.quick_mix_diversity import DiversityPolicy
from video_mix.core.quick_mix_diversity_adapter import (
    build_episode_group_diversity_plan,
    diversity_batch_manifest,
)


def asset(asset_id: str, folder: str, name: str):
    return SimpleNamespace(
        asset_id=asset_id,
        path=Path(folder) / name,
        media_type=SimpleNamespace(value="video"),
    )


def episode_groups():
    groups = []
    for folder_index, take_count in enumerate((3, 2, 4, 3), start=1):
        episode_id = f"episode_{folder_index}"
        takes = []
        for take_index in range(1, take_count + 1):
            current_asset = asset(
                f"asset_{folder_index}_{take_index}",
                f"folder_{folder_index}",
                f"take_{take_index}.mp4",
            )
            takes.append(
                {
                    "take_id": f"take_{folder_index}_{take_index}",
                    "take_index": take_index,
                    "asset": current_asset,
                    "start_ms": 1000,
                    "end_ms": 7000,
                    "marker_split": False,
                }
            )
        groups.append(
            {
                "episode_id": episode_id,
                "episode_label": f"Folder {folder_index}",
                "takes": takes,
            }
        )
    return groups


def test_adapter_maps_episode_groups_and_preserves_take_lookup() -> None:
    result = build_episode_group_diversity_plan(
        episode_groups(),
        target_duration_ms=8000,
        output_count=20,
        seed=29,
        policy=DiversityPolicy(
            exact_enumeration_limit=100,
            max_candidate_pool=400,
            minimum_candidates_per_output=8,
        ),
    )
    assert len(result.batch.plans) == 20
    assert set(result.take_by_source_id) == {
        f"take_{folder_index}_{take_index}"
        for folder_index, count in enumerate((3, 2, 4, 3), start=1)
        for take_index in range(1, count + 1)
    }
    for plan in result.batch.plans:
        for segment in plan.segments:
            assert segment.source_id in result.take_by_source_id
            assert segment.source_start_ms >= 1000


def test_adapter_excludes_reserved_opening_and_closing_assets() -> None:
    groups = episode_groups()
    reserved_take = groups[0]["takes"][0]
    result = build_episode_group_diversity_plan(
        groups,
        target_duration_ms=8000,
        output_count=12,
        seed=31,
        reserved_asset_ids={reserved_take["asset"].asset_id},
        policy=DiversityPolicy(
            exact_enumeration_limit=100,
            max_candidate_pool=300,
            minimum_candidates_per_output=8,
        ),
    )
    selected_ids = {
        segment.source_id
        for plan in result.batch.plans
        for segment in plan.segments
    }
    assert reserved_take["take_id"] not in selected_ids


def test_manifest_contains_complete_diversity_evidence() -> None:
    result = build_episode_group_diversity_plan(
        episode_groups(),
        target_duration_ms=8000,
        output_count=10,
        seed=37,
        policy=DiversityPolicy(
            exact_enumeration_limit=100,
            max_candidate_pool=250,
            minimum_candidates_per_output=8,
        ),
    )
    manifest = diversity_batch_manifest(
        result.batch,
        generation_id="generation_20260711_001",
        requested_duration_ms=8000,
    )
    assert manifest["generation_id"] == "generation_20260711_001"
    assert manifest["planner"] == "max_min_farthest_point"
    assert manifest["achieved_output_count"] == 10
    assert manifest["diversity"]["minimum_pairwise_distance"] > 0
    assert len(manifest["outputs"]) == 10
    assert all(output["body_visual_signature"] for output in manifest["outputs"])
    assert all(output["segments"] for output in manifest["outputs"])
