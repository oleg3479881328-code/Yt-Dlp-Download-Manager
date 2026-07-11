from pathlib import Path

from video_mix.core.quick_mix_diversity import (
    DiversityPlan,
    DiversityPolicy,
    DiversitySegment,
    build_diverse_batch,
    compare_plans,
    estimate_search_space,
    group_sources,
    rejection_reason,
)
from video_mix.core.quick_mix_planner import QuickMixSource


def sources(
    folder_counts: list[int],
    media_type: str = "photo",
) -> list[QuickMixSource]:
    return [
        QuickMixSource(
            source_id=f"{chr(65 + folder_index)}{take_index}",
            path=Path(chr(65 + folder_index)) / f"take_{take_index}.jpg",
            media_type=media_type,
            duration_ms=9000 if media_type == "video" else None,
            metadata={"folder_group": chr(65 + folder_index)},
        )
        for folder_index, take_count in enumerate(folder_counts)
        for take_index in range(1, take_count + 1)
    ]


def manual_plan(*source_ids: str) -> DiversityPlan:
    return DiversityPlan(
        1,
        len(source_ids) * 2000,
        tuple(
            DiversitySegment(
                source_id,
                source_id,
                f"{source_id.lower()}.jpg",
                source_id[0],
                f"{source_id[0]}/{source_id}.jpg",
                "photo",
                0,
                2000,
            )
            for source_id in source_ids
        ),
    )


def test_rejects_four_identical_positions_and_changed_tail() -> None:
    left = manual_plan("A1", "B1", "C1", "D1", "E1")
    right = manual_plan("A1", "B1", "C1", "D1", "E2")
    assert rejection_reason(left, right, DiversityPolicy()) == "single_position_change"


def test_rejects_identical_prefix_with_only_one_extra_tail_segment() -> None:
    left = manual_plan("A1", "B1", "C1", "D1", "E1")
    right = manual_plan("A1", "B1", "C1", "D1", "E1", "F2")
    assert rejection_reason(left, right, DiversityPolicy()) == "single_position_change"


def test_long_identical_prefix_is_scored_as_more_similar() -> None:
    reference = manual_plan("A1", "B1", "C1", "D1", "E1")
    close = manual_plan("A1", "B1", "C1", "D4", "E5")
    far = manual_plan("C2", "E3", "A4", "B5", "D2")
    assert compare_plans(reference, far).distance > compare_plans(
        reference,
        close,
    ).distance


def test_five_by_five_generates_100_separated_plans() -> None:
    policy = DiversityPolicy(
        exact_enumeration_limit=500,
        max_candidate_pool=1000,
        minimum_candidates_per_output=10,
    )
    result = build_diverse_batch(
        sources([5, 5, 5, 5, 5]),
        target_duration_ms=10_000,
        output_count=100,
        seed=17,
        policy=policy,
    )
    assert len(result.plans) == 100
    assert len({plan.body_signature for plan in result.plans}) == 100
    assert result.report.minimum_pairwise_distance > 0
    for left_index, left in enumerate(result.plans):
        assert len(set(left.folder_signature)) == 5
        for right in result.plans[left_index + 1 :]:
            assert rejection_reason(left, right, DiversityPolicy()) is None


def test_supports_four_and_ten_uneven_folders() -> None:
    policy = DiversityPolicy(
        exact_enumeration_limit=300,
        max_candidate_pool=500,
        minimum_candidates_per_output=8,
    )
    for counts in ([2, 3, 4, 5], [1, 2, 3, 4, 5, 2, 3, 1, 4, 2]):
        result = build_diverse_batch(
            sources(list(counts)),
            target_duration_ms=8_000,
            output_count=24,
            seed=23,
            policy=policy,
        )
        assert len(result.plans) == 24
        assert all(plan.planned_duration_ms == 8_000 for plan in result.plans)


def test_large_folder_search_space_avoids_permutation_enumeration() -> None:
    grouped = group_sources(sources([1] * 20))
    assert estimate_search_space(grouped, 20_000) == 670_442_572_800


def test_uses_folder_subset_when_more_folders_than_positions() -> None:
    result = build_diverse_batch(
        sources([2] * 10),
        target_duration_ms=8_000,
        output_count=10,
        seed=41,
        policy=DiversityPolicy(
            exact_enumeration_limit=100,
            max_candidate_pool=400,
            minimum_candidates_per_output=8,
        ),
    )
    assert all(len(plan.segments) == 4 for plan in result.plans)
    assert all(len(set(plan.folder_signature)) == 4 for plan in result.plans)


def test_folder_and_take_cycles_exhaust_before_reuse() -> None:
    folder_result = build_diverse_batch(
        sources([3, 3, 3, 3]),
        target_duration_ms=12_000,
        output_count=8,
        seed=59,
        policy=DiversityPolicy(
            exact_enumeration_limit=100,
            max_candidate_pool=400,
            minimum_candidates_per_output=8,
        ),
    )
    for plan in folder_result.plans:
        assert len(set(plan.folder_signature[:4])) == 4
        assert plan.folder_signature[3] != plan.folder_signature[4]

    take_result = build_diverse_batch(
        sources([3]),
        target_duration_ms=8_000,
        output_count=1,
        seed=71,
        policy=DiversityPolicy(exact_enumeration_limit=2),
    )
    take_ids = [segment.source_id for segment in take_result.plans[0].segments]
    assert len(set(take_ids[:3])) == 3
    assert take_ids[2] != take_ids[3]


def test_exclusions_keep_opening_and_closing_out_of_body() -> None:
    material = sources([3, 3, 3])
    result = build_diverse_batch(
        material,
        target_duration_ms=6_000,
        output_count=12,
        seed=73,
        excluded_source_ids={material[0].source_id},
        excluded_source_groups={material[1].source_group},
        policy=DiversityPolicy(
            exact_enumeration_limit=100,
            max_candidate_pool=300,
            minimum_candidates_per_output=8,
        ),
    )
    selected = {
        segment.source_id
        for plan in result.plans
        for segment in plan.segments
    }
    assert material[0].source_id not in selected
    assert material[1].source_id not in selected


def test_seed_is_deterministic() -> None:
    policy = DiversityPolicy(
        exact_enumeration_limit=100,
        max_candidate_pool=500,
        minimum_candidates_per_output=8,
    )
    kwargs = {
        "sources": sources([3, 3, 3, 3, 3]),
        "target_duration_ms": 10_000,
        "output_count": 30,
        "seed": 101,
        "policy": policy,
    }
    left = build_diverse_batch(**kwargs)
    right = build_diverse_batch(**kwargs)
    assert [plan.body_signature for plan in left.plans] == [
        plan.body_signature for plan in right.plans
    ]
