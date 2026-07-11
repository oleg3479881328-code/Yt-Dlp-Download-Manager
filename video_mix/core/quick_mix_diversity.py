from __future__ import annotations

import itertools
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from statistics import mean
from typing import Iterable, Sequence

from .quick_mix_planner import QuickMixSource, preferred_quick_mix_segment_ms

QUICK_MIX_DIVERSITY_EXHAUSTED = "quick_mix_diversity_exhausted"


@dataclass(frozen=True, slots=True)
class DiversityPolicy:
    max_positional_take_match_ratio: float = 0.74
    max_common_prefix_ratio: float = 0.50
    min_changed_thirds: int = 2
    reject_single_position_change: bool = True
    exact_enumeration_limit: int = 10_000
    max_candidate_pool: int = 20_000
    minimum_candidates_per_output: int = 24
    dimensions_per_output_multiplier: int = 1
    balance_weight: float = 0.02

    def __post_init__(self) -> None:
        if not 0 <= self.max_positional_take_match_ratio < 1:
            raise ValueError("max_positional_take_match_ratio must be in [0, 1)")
        if not 0 <= self.max_common_prefix_ratio < 1:
            raise ValueError("max_common_prefix_ratio must be in [0, 1)")
        if self.min_changed_thirds not in {1, 2, 3}:
            raise ValueError("min_changed_thirds must be 1, 2, or 3")
        if min(
            self.exact_enumeration_limit,
            self.max_candidate_pool,
            self.minimum_candidates_per_output,
            self.dimensions_per_output_multiplier,
        ) <= 0:
            raise ValueError("planner limits must be greater than zero")


@dataclass(frozen=True, slots=True)
class DiversitySegment:
    source_id: str
    base_source_id: str
    source_group: str
    folder_id: str
    source_path: str
    media_type: str
    source_start_ms: int
    duration_ms: int

    @property
    def window_id(self) -> str:
        return f"{self.source_id}@{self.source_start_ms}:{self.source_start_ms + self.duration_ms}"


@dataclass(frozen=True, slots=True)
class DiversityPlan:
    output_index: int
    target_duration_ms: int
    segments: tuple[DiversitySegment, ...]

    @property
    def planned_duration_ms(self) -> int:
        return sum(segment.duration_ms for segment in self.segments)

    @property
    def body_signature(self) -> tuple[str, ...]:
        return tuple(segment.window_id for segment in self.segments)

    @property
    def folder_signature(self) -> tuple[str, ...]:
        return tuple(segment.folder_id for segment in self.segments)


@dataclass(frozen=True, slots=True)
class PairMetrics:
    compared_positions: int
    same_take_positions: int
    same_folder_positions: int
    common_prefix_length: int
    longest_identical_run: int
    take_overlap: int
    folder_overlap: int
    folder_transition_overlap: int
    take_transition_overlap: int
    changed_thirds: int
    similarity: float
    distance: float


@dataclass(frozen=True, slots=True)
class DiversityReport:
    strategy: str
    estimated_search_space: int
    candidate_budget: int
    candidates_generated: int
    duplicate_candidates_removed: int
    requested_output_count: int
    achieved_output_count: int
    rejected_by_reason: dict[str, int]
    minimum_pairwise_distance: float
    average_pairwise_distance: float
    maximum_pairwise_distance: float
    nearest_neighbour_distance_by_output: dict[int, float]
    source_usage: dict[str, int]
    folder_usage: dict[str, int]
    folder_position_usage: dict[str, int]
    folder_transition_usage: dict[str, int]


@dataclass(frozen=True, slots=True)
class DiversityBatch:
    plans: tuple[DiversityPlan, ...]
    warnings: tuple[dict, ...]
    report: DiversityReport


def source_folder_id(source: QuickMixSource) -> str:
    for key in ("folder_group", "group_id", "episode_id", "folder_id"):
        value = source.metadata.get(key)
        if value not in (None, ""):
            return str(value)
    parent = source.path.parent.name.strip()
    return parent.casefold() if parent else source.unique_base_id


def compare_plans(left: DiversityPlan, right: DiversityPlan) -> PairMetrics:
    left_takes = list(left.body_signature)
    right_takes = list(right.body_signature)
    left_folders = list(left.folder_signature)
    right_folders = list(right.folder_signature)
    positions = min(len(left_takes), len(right_takes))
    if positions == 0:
        return PairMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 1.0)

    same_takes = sum(left_takes[index] == right_takes[index] for index in range(positions))
    same_folders = sum(left_folders[index] == right_folders[index] for index in range(positions))
    prefix = _common_prefix(left_takes, right_takes)
    run = _longest_run(left_takes, right_takes)
    take_overlap = _overlap(left_takes, right_takes)
    folder_overlap = _overlap(left_folders, right_folders)
    folder_transition_overlap = _overlap(_transitions(left_folders), _transitions(right_folders))
    take_transition_overlap = _overlap(_transitions(left_takes), _transitions(right_takes))
    changed_thirds = _changed_thirds(left_takes, right_takes)

    similarity = min(
        1.0,
        0.28 * same_takes / positions
        + 0.16 * same_folders / positions
        + 0.16 * prefix / positions
        + 0.10 * run / positions
        + 0.10 * take_overlap / max(len(left_takes), len(right_takes), 1)
        + 0.04 * folder_overlap / max(len(left_folders), len(right_folders), 1)
        + 0.08
        * folder_transition_overlap
        / max(len(_transitions(left_folders)), len(_transitions(right_folders)), 1)
        + 0.06
        * take_transition_overlap
        / max(len(_transitions(left_takes)), len(_transitions(right_takes)), 1)
        + 0.02 * (changed_thirds <= 1 and left_takes != right_takes),
    )
    return PairMetrics(
        positions,
        same_takes,
        same_folders,
        prefix,
        run,
        take_overlap,
        folder_overlap,
        folder_transition_overlap,
        take_transition_overlap,
        changed_thirds,
        similarity,
        max(0.0, 1.0 - similarity),
    )


def rejection_reason(left: DiversityPlan, right: DiversityPlan, policy: DiversityPolicy) -> str | None:
    if left.body_signature == right.body_signature:
        return "exact_body_duplicate"
    metrics = compare_plans(left, right)
    positions = metrics.compared_positions
    if positions == 0 or len(left.segments) != len(right.segments):
        return None
    if policy.reject_single_position_change and positions >= 2 and metrics.same_take_positions >= positions - 1:
        return "single_position_change"
    if metrics.same_take_positions / positions > policy.max_positional_take_match_ratio:
        return "positional_take_match"
    if metrics.common_prefix_length / positions > policy.max_common_prefix_ratio:
        return "common_prefix"
    if (
        positions >= 3
        and metrics.changed_thirds < policy.min_changed_thirds
        and metrics.same_take_positions / positions >= 0.50
    ):
        return "changes_concentrated_in_one_third"
    return None


def build_diverse_batch(
    sources: Sequence[QuickMixSource],
    *,
    target_duration_ms: int,
    output_count: int,
    seed: int | None = None,
    policy: DiversityPolicy | None = None,
    prior_plans: Sequence[DiversityPlan] = (),
    excluded_source_ids: Iterable[str] = (),
    excluded_source_groups: Iterable[str] = (),
) -> DiversityBatch:
    if target_duration_ms <= 0:
        raise ValueError("target_duration_ms must be greater than zero")
    if output_count <= 0:
        raise ValueError("output_count must be greater than zero")
    if not sources:
        raise ValueError("At least one Quick Mix source is required")

    active_policy = policy or DiversityPolicy()
    blocked_ids = set(excluded_source_ids)
    blocked_groups = set(excluded_source_groups)
    eligible = [
        source
        for source in sources
        if source.source_id not in blocked_ids
        and source.unique_base_id not in blocked_ids
        and source.source_group not in blocked_groups
    ]
    if not eligible:
        raise ValueError("No eligible Quick Mix sources remain after exclusions")

    grouped = _group_sources(eligible)
    estimated_space = estimate_search_space(grouped, target_duration_ms)
    strategy = "enumerate" if estimated_space <= active_policy.exact_enumeration_limit else "sample"
    budget = _candidate_budget(grouped, output_count, estimated_space, active_policy)
    candidates = (
        _enumerate_candidates(grouped, target_duration_ms, active_policy.exact_enumeration_limit)
        if strategy == "enumerate"
        else []
    )
    if not candidates:
        strategy = "sample"
        candidates = _sample_candidates(grouped, target_duration_ms, budget, seed)

    unique = {candidate.body_signature: candidate for candidate in candidates}
    duplicate_count = len(candidates) - len(unique)
    selected, rejected = _select_farthest(
        list(unique.values()),
        output_count,
        active_policy,
        list(prior_plans),
        seed,
    )
    indexed = tuple(replace(plan, output_index=index) for index, plan in enumerate(selected, start=1))
    warnings: tuple[dict, ...] = ()
    if len(indexed) < output_count:
        warnings = (
            {
                "code": QUICK_MIX_DIVERSITY_EXHAUSTED,
                "requested_output_count": output_count,
                "achieved_output_count": len(indexed),
                "rejected_by_reason": dict(rejected),
            },
        )
    report = _report(
        indexed,
        strategy,
        estimated_space,
        budget,
        len(unique),
        duplicate_count,
        output_count,
        dict(rejected),
    )
    return DiversityBatch(indexed, warnings, report)


def estimate_search_space(grouped: dict[str, list[QuickMixSource]], target_duration_ms: int) -> int:
    nominal = _nominal_duration(grouped, target_duration_ms)
    segment_count = max(1, math.ceil(target_duration_ms / nominal))
    first_cycle = min(segment_count, len(grouped))
    total = sum(
        math.prod(len(grouped[group_id]) for group_id in order)
        for order in itertools.permutations(grouped, first_cycle)
    )
    extra = max(0, segment_count - first_cycle)
    if extra:
        average_takes = max(1, round(mean(len(items) for items in grouped.values())))
        total *= (len(grouped) * average_takes) ** extra
    return min(total, 10**18)


def _group_sources(sources: Sequence[QuickMixSource]) -> dict[str, list[QuickMixSource]]:
    grouped: dict[str, list[QuickMixSource]] = defaultdict(list)
    for source in sources:
        grouped[source_folder_id(source)].append(source)
    return {
        group_id: sorted(items, key=lambda item: (item.source_id, str(item.path).casefold()))
        for group_id, items in sorted(grouped.items())
    }


def _candidate_budget(
    grouped: dict[str, list[QuickMixSource]],
    output_count: int,
    estimated_space: int,
    policy: DiversityPolicy,
) -> int:
    dimensions = len(grouped) + sum(len(items) for items in grouped.values())
    per_output = max(policy.minimum_candidates_per_output, policy.dimensions_per_output_multiplier * dimensions)
    return max(
        output_count,
        min(policy.max_candidate_pool, estimated_space, output_count * per_output),
    )


def _nominal_duration(grouped: dict[str, list[QuickMixSource]], target_duration_ms: int) -> int:
    durations = [
        preferred_quick_mix_segment_ms(source, target_duration_ms)
        for items in grouped.values()
        for source in items
    ]
    return max(1, round(mean(durations)))


def _enumerate_candidates(
    grouped: dict[str, list[QuickMixSource]],
    target_duration_ms: int,
    limit: int,
) -> list[DiversityPlan]:
    nominal = _nominal_duration(grouped, target_duration_ms)
    if target_duration_ms % nominal:
        return []
    segment_count = target_duration_ms // nominal
    if segment_count <= 0 or segment_count > len(grouped):
        return []
    if any(
        preferred_quick_mix_segment_ms(source, target_duration_ms) != nominal
        for items in grouped.values()
        for source in items
    ):
        return []

    result: list[DiversityPlan] = []
    for order in itertools.permutations(grouped, segment_count):
        for selected_sources in itertools.product(*(grouped[group_id] for group_id in order)):
            result.append(
                DiversityPlan(
                    0,
                    target_duration_ms,
                    tuple(_segment(source, nominal, 0) for source in selected_sources),
                )
            )
            if len(result) >= limit:
                return result
    return result


def _sample_candidates(
    grouped: dict[str, list[QuickMixSource]],
    target_duration_ms: int,
    budget: int,
    seed: int | None,
) -> list[DiversityPlan]:
    base_seed = seed if seed is not None else random.SystemRandom().randrange(2**63)
    group_ids = list(grouped)
    result: list[DiversityPlan] = []
    for candidate_index in range(budget):
        rng = random.Random((base_seed + 1) * 1_000_003 + candidate_index * 97_409)
        remaining = target_duration_ms
        segments: list[DiversitySegment] = []
        source_orders: dict[str, list[QuickMixSource]] = {}
        source_positions: Counter[str] = Counter()
        source_uses: Counter[str] = Counter()
        last_source: dict[str, str] = {}
        last_folder: str | None = None

        while remaining > 0:
            cycle = list(group_ids)
            rng.shuffle(cycle)
            if len(cycle) > 1 and cycle[0] == last_folder:
                swap = next(index for index, group_id in enumerate(cycle[1:], 1) if group_id != last_folder)
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
                    if len(order) > 1 and previous is not None and order[0].source_id == previous:
                        swap = next(index for index, source in enumerate(order[1:], 1) if source.source_id != previous)
                        order[0], order[swap] = order[swap], order[0]
                    source_orders[folder_id] = order
                    source_positions[folder_id] = 0
                    position = 0
                source = order[position]
                source_positions[folder_id] += 1
                last_source[folder_id] = source.source_id
                duration = preferred_quick_mix_segment_ms(source, remaining)
                start = _sample_start(source, duration, candidate_index, source_uses[source.source_id], rng)
                segments.append(_segment(source, duration, start))
                source_uses[source.source_id] += 1
                remaining -= duration
                last_folder = folder_id
        result.append(DiversityPlan(0, target_duration_ms, tuple(segments)))
    return result


def _sample_start(
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


def _segment(source: QuickMixSource, duration_ms: int, source_start_ms: int) -> DiversitySegment:
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


@dataclass(slots=True)
class _Usage:
    sources: Counter[str] = field(default_factory=Counter)
    positions: Counter[str] = field(default_factory=Counter)
    transitions: Counter[str] = field(default_factory=Counter)

    def add(self, plan: DiversityPlan) -> None:
        for index, segment in enumerate(plan.segments):
            self.sources[segment.source_id] += 1
            self.positions[f"{index}:{segment.folder_id}"] += 1
        self.transitions.update(_transitions(plan.folder_signature))

    def penalty(self, plan: DiversityPlan) -> float:
        values = [
            value
            for index, segment in enumerate(plan.segments)
            for value in (
                self.sources[segment.source_id],
                self.positions[f"{index}:{segment.folder_id}"],
            )
        ]
        values.extend(self.transitions[item] for item in _transitions(plan.folder_signature))
        return mean(values) if values else 0.0


def _select_farthest(
    candidates: list[DiversityPlan],
    output_count: int,
    policy: DiversityPolicy,
    prior: list[DiversityPlan],
    seed: int | None,
) -> tuple[list[DiversityPlan], Counter[str]]:
    if not candidates:
        return [], Counter()
    rng = random.Random(seed)
    blocked = [False] * len(candidates)
    nearest = [1.0] * len(candidates)
    rejected: Counter[str] = Counter()
    for index, candidate in enumerate(candidates):
        for previous in prior:
            reason = rejection_reason(candidate, previous, policy)
            if reason:
                rejected[reason] += 1
                blocked[index] = True
                break
            nearest[index] = min(nearest[index], compare_plans(candidate, previous).distance)

    selected: list[DiversityPlan] = []
    usage = _Usage()
    while len(selected) < output_count:
        available = [index for index, value in enumerate(blocked) if not value]
        if not available:
            break
        if not selected and not prior:
            chosen_index = available[rng.randrange(len(available))]
        else:
            chosen_index = max(
                available,
                key=lambda index: (
                    nearest[index] - policy.balance_weight * usage.penalty(candidates[index]),
                    nearest[index],
                    -usage.penalty(candidates[index]),
                    -index,
                ),
            )
        chosen = candidates[chosen_index]
        selected.append(chosen)
        prior.append(chosen)
        usage.add(chosen)
        blocked[chosen_index] = True
        for index, candidate in enumerate(candidates):
            if blocked[index]:
                continue
            reason = rejection_reason(candidate, chosen, policy)
            if reason:
                rejected[reason] += 1
                blocked[index] = True
            else:
                nearest[index] = min(nearest[index], compare_plans(candidate, chosen).distance)
    return selected, rejected


def _report(
    plans: Sequence[DiversityPlan],
    strategy: str,
    estimated_space: int,
    budget: int,
    candidates_generated: int,
    duplicates_removed: int,
    requested: int,
    rejected: dict[str, int],
) -> DiversityReport:
    distances: list[float] = []
    nearest: dict[int, float] = {}
    sources: Counter[str] = Counter()
    folders: Counter[str] = Counter()
    positions: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    for left_index, left in enumerate(plans):
        local = [
            compare_plans(left, right).distance
            for right_index, right in enumerate(plans)
            if right_index != left_index
        ]
        nearest[left.output_index] = min(local) if local else 1.0
        distances.extend(
            compare_plans(left, right).distance for right in plans[left_index + 1 :]
        )
        for position, segment in enumerate(left.segments, 1):
            sources[segment.source_id] += 1
            folders[segment.folder_id] += 1
            positions[f"{position}:{segment.folder_id}"] += 1
        transitions.update(_transitions(left.folder_signature))
    return DiversityReport(
        strategy,
        estimated_space,
        budget,
        candidates_generated,
        duplicates_removed,
        requested,
        len(plans),
        rejected,
        min(distances) if distances else 1.0,
        mean(distances) if distances else 1.0,
        max(distances) if distances else 1.0,
        nearest,
        dict(sorted(sources.items())),
        dict(sorted(folders.items())),
        dict(sorted(positions.items())),
        dict(sorted(transitions.items())),
    )


def _common_prefix(left: Sequence[str], right: Sequence[str]) -> int:
    result = 0
    for left_item, right_item in zip(left, right, strict=False):
        if left_item != right_item:
            break
        result += 1
    return result


def _longest_run(left: Sequence[str], right: Sequence[str]) -> int:
    longest = current = 0
    for left_item, right_item in zip(left, right, strict=False):
        current = current + 1 if left_item == right_item else 0
        longest = max(longest, current)
    return longest


def _overlap(left: Iterable[str], right: Iterable[str]) -> int:
    return sum((Counter(left) & Counter(right)).values())


def _transitions(items: Sequence[str]) -> list[str]:
    return [f"{left}->{right}" for left, right in zip(items, items[1:], strict=False)]


def _changed_thirds(left: Sequence[str], right: Sequence[str]) -> int:
    compared = min(len(left), len(right))
    if not compared:
        return 0
    result = {
        min(2, index * 3 // compared)
        for index in range(compared)
        if left[index] != right[index]
    }
    if len(left) != len(right):
        result.add(2)
    return len(result)
