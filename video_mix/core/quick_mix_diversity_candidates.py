from __future__ import annotations

import itertools
import math
import random
from collections import Counter, defaultdict
from collections.abc import Sequence
from statistics import mean

from .quick_mix_diversity_models import (
    DiversityPlan,
    DiversityPolicy,
    DiversitySegment,
    source_folder_id,
)
from .quick_mix_planner import QuickMixSource, preferred_quick_mix_segment_ms


def group_sources(sources: Sequence[QuickMixSource]) -> dict[str, list[QuickMixSource]]:
    grouped: dict[str, list[QuickMixSource]] = defaultdict(list)
    for source in sources:
        grouped[source_folder_id(source)].append(source)
    return {
        group_id: sorted(items, key=lambda item: (item.source_id, str(item.path).casefold()))
        for group_id, items in sorted(grouped.items())
    }


def estimate_search_space(
    grouped: dict[str, list[QuickMixSource]],
    target_duration_ms: int,
) -> int:
    nominal = nominal_duration(grouped, target_duration_ms)
    segment_count = max(1, math.ceil(target_duration_ms / nominal))
    first_cycle = min(segment_count, len(grouped))
    take_counts = [
        sum(source_variant_count(source, target_duration_ms) for source in items)
        for items in grouped.values()
    ]

    weighted_subsets = [0] * (first_cycle + 1)
    weighted_subsets[0] = 1
    for take_count in take_counts:
        for size in range(first_cycle, 0, -1):
            weighted_subsets[size] += weighted_subsets[size - 1] * take_count
    total = math.factorial(first_cycle) * weighted_subsets[first_cycle]

    extra = max(0, segment_count - first_cycle)
    if extra:
        average_takes = max(1, round(mean(take_counts)))
        total *= (len(grouped) * average_takes) ** extra
    return min(total, 10**18)


def source_variant_count(
    source: QuickMixSource,
    target_duration_ms: int,
) -> int:
    segment_ms = preferred_quick_mix_segment_ms(source, target_duration_ms)
    if (
        source.media_type != "video"
        or not source.duration_ms
        or segment_ms <= 0
    ):
        return 1
    return max(1, math.ceil(source.duration_ms / segment_ms))


def candidate_budget(
    grouped: dict[str, list[QuickMixSource]],
    output_count: int,
    estimated_space: int,
    policy: DiversityPolicy,
) -> int:
    dimensions = len(grouped) + sum(len(items) for items in grouped.values())
    per_output = max(
        policy.minimum_candidates_per_output,
        policy.dimensions_per_output_multiplier * dimensions,
    )
    desired = max(output_count, output_count * per_output)
    return max(1, min(policy.max_candidate_pool, estimated_space, desired))


def enumerate_candidates(
    grouped: dict[str, list[QuickMixSource]],
    target_duration_ms: int,
    limit: int,
) -> list[DiversityPlan]:
    nominal = nominal_duration(grouped, target_duration_ms)
    if target_duration_ms % nominal:
        return []
    segment_count = target_duration_ms // nominal
    enforce_unique_materials = _can_enforce_unique_materials(grouped, segment_count)
    if segment_count <= 0 or segment_count > len(grouped):
        return []
    if any(
        preferred_quick_mix_segment_ms(source, target_duration_ms) != nominal
        or (
            source.media_type == "video"
            and bool(source.duration_ms)
            and int(source.duration_ms or 0) > nominal
        )
        for items in grouped.values()
        for source in items
    ):
        return []

    result: list[DiversityPlan] = []
    for order in itertools.permutations(grouped, segment_count):
        for selected_sources in itertools.product(*(grouped[group_id] for group_id in order)):
            if enforce_unique_materials and not _sources_are_materially_unique(selected_sources):
                continue
            result.append(
                DiversityPlan(
                    0,
                    target_duration_ms,
                    tuple(
                        segment(source, nominal, source.source_start_ms)
                        for source in selected_sources
                    ),
                )
            )
            if len(result) >= limit:
                return result
    return result


def sample_candidates(
    grouped: dict[str, list[QuickMixSource]],
    target_duration_ms: int,
    budget: int,
    seed: int | None,
) -> list[DiversityPlan]:
    base_seed = seed if seed is not None else random.SystemRandom().randrange(2**63)
    group_ids = list(grouped)
    nominal = nominal_duration(grouped, target_duration_ms)
    planned_segments = max(1, math.ceil(target_duration_ms / nominal))
    enforce_unique_materials = _can_enforce_unique_materials(grouped, planned_segments)
    result: list[DiversityPlan] = []
    candidate_index = 0
    attempt_index = 0
    maximum_attempts = max(budget * 8, budget + 1)
    while len(result) < budget and attempt_index < maximum_attempts:
        attempt_index += 1
        rng = random.Random((base_seed + 1) * 1_000_003 + candidate_index * 97_409)
        remaining = target_duration_ms
        segments: list[DiversitySegment] = []
        source_orders: dict[str, list[QuickMixSource]] = {}
        source_positions: Counter[str] = Counter()
        source_uses: Counter[str] = Counter()
        used_base_source_ids: set[str] = set()
        used_source_groups: set[str] = set()
        last_source: dict[str, str] = {}
        last_folder: str | None = None

        while remaining > 0 and len(segments) < planned_segments:
            cycle = list(group_ids)
            rng.shuffle(cycle)
            if len(cycle) > 1 and cycle[0] == last_folder:
                swap = next(
                    index
                    for index, group_id in enumerate(cycle[1:], 1)
                    if group_id != last_folder
                )
                cycle[0], cycle[swap] = cycle[swap], cycle[0]
            for folder_id in cycle:
                if remaining <= 0:
                    break
                order = source_orders.get(folder_id)
                position = source_positions[folder_id]
                if order is None or position >= len(order):
                    order = list(grouped[folder_id])
                    rng.shuffle(order)
                    previous = last_source.get(folder_id)
                    if (
                        len(order) > 1
                        and previous is not None
                        and order[0].source_id == previous
                    ):
                        swap = next(
                            index
                            for index, source in enumerate(order[1:], 1)
                            if source.source_id != previous
                        )
                        order[0], order[swap] = order[swap], order[0]
                    source_orders[folder_id] = order
                    source_positions[folder_id] = 0
                    position = 0
                source, next_position = _choose_source_for_plan_step(
                    order,
                    position,
                    used_base_source_ids=used_base_source_ids,
                    used_source_groups=used_source_groups,
                )
                source_positions[folder_id] = next_position
                last_source[folder_id] = source.source_id
                duration = preferred_quick_mix_segment_ms(source, remaining)
                start = sample_start(
                    source,
                    duration,
                    candidate_index,
                    source_uses[source.source_id],
                    rng,
                )
                segments.append(segment(source, duration, start))
                source_uses[source.source_id] += 1
                used_base_source_ids.add(source.unique_base_id)
                used_source_groups.add(source.source_group)
                remaining -= duration
                last_folder = folder_id
        if enforce_unique_materials and not _segments_are_materially_unique(segments):
            candidate_index += 1
            continue
        result.append(DiversityPlan(0, target_duration_ms, tuple(segments)))
        candidate_index += 1
    return result


def nominal_duration(
    grouped: dict[str, list[QuickMixSource]],
    target_duration_ms: int,
) -> int:
    durations = [
        preferred_quick_mix_segment_ms(source, target_duration_ms)
        for items in grouped.values()
        for source in items
    ]
    return max(1, round(mean(durations)))


def sample_start(
    source: QuickMixSource,
    duration_ms: int,
    candidate_index: int,
    source_use_index: int,
    rng: random.Random,
) -> int:
    if source.media_type != "video" or not source.duration_ms:
        return source.source_start_ms
    max_start = max(0, source.duration_ms - duration_ms)
    if not max_start:
        return source.source_start_ms
    windows = max(1, math.ceil(source.duration_ms / max(1, duration_ms)))
    index = (candidate_index + source_use_index + rng.randrange(windows)) % windows
    return source.source_start_ms + min(max_start, index * duration_ms)


def segment(
    source: QuickMixSource,
    duration_ms: int,
    source_start_ms: int,
) -> DiversitySegment:
    return DiversitySegment(
        source.source_id,
        source.unique_base_id,
        source.source_group,
        source_folder_id(source),
        str(source.path),
        source.media_type,
        source_start_ms,
        duration_ms,
    )


def _sources_are_materially_unique(sources: Sequence[QuickMixSource]) -> bool:
    base_ids = [source.unique_base_id for source in sources]
    source_groups = [source.source_group for source in sources]
    return len(base_ids) == len(set(base_ids)) and len(source_groups) == len(set(source_groups))


def _segments_are_materially_unique(segments: Sequence[DiversitySegment]) -> bool:
    base_ids = [segment.base_source_id for segment in segments]
    source_groups = [segment.source_group for segment in segments]
    return len(base_ids) == len(set(base_ids)) and len(source_groups) == len(set(source_groups))


def _can_enforce_unique_materials(
    grouped: dict[str, list[QuickMixSource]],
    segment_count: int,
) -> bool:
    sources = [source for items in grouped.values() for source in items]
    unique_asset_count = len({source.unique_base_id for source in sources})
    unique_group_count = len({source.source_group for source in sources})
    return segment_count <= unique_asset_count and segment_count <= unique_group_count


def _choose_source_for_plan_step(
    order: Sequence[QuickMixSource],
    position: int,
    *,
    used_base_source_ids: set[str],
    used_source_groups: set[str],
) -> tuple[QuickMixSource, int]:
    indexed_sources = list(enumerate(order[position:], start=position))
    indexed_sources.extend((index, source) for index, source in enumerate(order[:position]))
    stages = (
        lambda source: source.unique_base_id not in used_base_source_ids and source.source_group not in used_source_groups,
        lambda source: source.unique_base_id not in used_base_source_ids,
        lambda source: source.source_group not in used_source_groups,
        lambda _source: True,
    )
    for predicate in stages:
        for index, source in indexed_sources:
            if predicate(source):
                return source, index + 1
    return order[position], position + 1
