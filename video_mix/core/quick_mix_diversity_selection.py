from __future__ import annotations

import random
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from statistics import mean

from .quick_mix_diversity_candidates import (
    candidate_budget,
    enumerate_candidates,
    estimate_search_space,
    group_sources,
    sample_candidates,
)
from .quick_mix_diversity_metrics import assess_pair, compare_plans, transitions
from .quick_mix_diversity_models import (
    QUICK_MIX_DIVERSITY_EXHAUSTED,
    DiversityBatch,
    DiversityPlan,
    DiversityPolicy,
    DiversityReport,
)
from .quick_mix_planner import QuickMixSource


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

    grouped = group_sources(eligible)
    estimated_space = estimate_search_space(grouped, target_duration_ms)
    strategy = (
        "enumerate"
        if estimated_space <= active_policy.exact_enumeration_limit
        else "sample"
    )
    budget = candidate_budget(grouped, output_count, estimated_space, active_policy)
    candidates: list[DiversityPlan] = []
    if strategy == "enumerate":
        candidates = enumerate_candidates(
            grouped,
            target_duration_ms,
            active_policy.exact_enumeration_limit,
        )
        if not candidates:
            strategy = "sample"

    selected: list[DiversityPlan] = []
    rejected: Counter[str] = Counter()
    duplicate_count = 0
    candidate_count = 0
    while True:
        if strategy == "sample":
            candidates = sample_candidates(
                grouped,
                target_duration_ms,
                budget,
                seed,
            )
        unique = {candidate.body_signature: candidate for candidate in candidates}
        candidate_count = len(candidates)
        duplicate_count = candidate_count - len(unique)
        selected, rejected = _select_farthest(
            list(unique.values()),
            output_count,
            active_policy,
            list(prior_plans),
            seed,
        )
        if len(selected) >= output_count or strategy != "sample":
            break
        maximum_budget = min(
            active_policy.max_candidate_pool,
            estimated_space,
        )
        if budget >= maximum_budget:
            break
        budget = min(maximum_budget, max(budget * 2, budget + output_count))

    indexed = tuple(
        replace(plan, output_index=index)
        for index, plan in enumerate(selected, start=1)
    )
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
        candidate_count,
        duplicate_count,
        output_count,
        dict(rejected),
    )
    return DiversityBatch(indexed, warnings, report)


@dataclass(slots=True)
class _Usage:
    sources: Counter[str] = field(default_factory=Counter)
    positions: Counter[str] = field(default_factory=Counter)
    transitions: Counter[str] = field(default_factory=Counter)

    def add(self, plan: DiversityPlan) -> None:
        for index, segment in enumerate(plan.segments):
            self.sources[segment.source_id] += 1
            self.positions[f"{index}:{segment.folder_id}"] += 1
        self.transitions.update(transitions(plan.folder_signature))

    def penalty(self, plan: DiversityPlan) -> float:
        values = [
            value
            for index, segment in enumerate(plan.segments)
            for value in (
                self.sources[segment.source_id],
                self.positions[f"{index}:{segment.folder_id}"],
            )
        ]
        values.extend(
            self.transitions[item]
            for item in transitions(plan.folder_signature)
        )
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
            reason, metrics = assess_pair(candidate, previous, policy)
            if reason:
                rejected[reason] += 1
                blocked[index] = True
                break
            nearest[index] = min(nearest[index], metrics.distance)

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
                    nearest[index]
                    - policy.balance_weight * usage.penalty(candidates[index]),
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
            reason, metrics = assess_pair(candidate, chosen, policy)
            if reason:
                rejected[reason] += 1
                blocked[index] = True
            else:
                nearest[index] = min(nearest[index], metrics.distance)
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
    distances_by_output: dict[int, list[float]] = {
        plan.output_index: [] for plan in plans
    }
    all_distances: list[float] = []
    sources: Counter[str] = Counter()
    folders: Counter[str] = Counter()
    positions: Counter[str] = Counter()
    transition_counts: Counter[str] = Counter()
    for left_index, left in enumerate(plans):
        for right in plans[left_index + 1 :]:
            distance = compare_plans(left, right).distance
            all_distances.append(distance)
            distances_by_output[left.output_index].append(distance)
            distances_by_output[right.output_index].append(distance)
        for position, segment in enumerate(left.segments, 1):
            sources[segment.source_id] += 1
            folders[segment.folder_id] += 1
            positions[f"{position}:{segment.folder_id}"] += 1
        transition_counts.update(transitions(left.folder_signature))
    nearest = {
        output_index: min(values) if values else 1.0
        for output_index, values in distances_by_output.items()
    }
    return DiversityReport(
        strategy,
        estimated_space,
        budget,
        candidates_generated,
        duplicates_removed,
        requested,
        len(plans),
        rejected,
        min(all_distances) if all_distances else 1.0,
        mean(all_distances) if all_distances else 1.0,
        max(all_distances) if all_distances else 1.0,
        nearest,
        dict(sorted(sources.items())),
        dict(sorted(folders.items())),
        dict(sorted(positions.items())),
        dict(sorted(transition_counts.items())),
    )
