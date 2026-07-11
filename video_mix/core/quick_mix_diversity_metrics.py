from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence

from .quick_mix_diversity_models import DiversityPlan, DiversityPolicy, PairMetrics


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
    folder_transition_overlap = _overlap(transitions(left_folders), transitions(right_folders))
    take_transition_overlap = _overlap(transitions(left_takes), transitions(right_takes))
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
        / max(len(transitions(left_folders)), len(transitions(right_folders)), 1)
        + 0.06
        * take_transition_overlap
        / max(len(transitions(left_takes)), len(transitions(right_takes)), 1)
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


def assess_pair(
    left: DiversityPlan,
    right: DiversityPlan,
    policy: DiversityPolicy,
) -> tuple[str | None, PairMetrics]:
    metrics = compare_plans(left, right)
    if left.body_signature == right.body_signature:
        return "exact_body_duplicate", metrics
    positions = metrics.compared_positions
    if positions == 0:
        return None, metrics
    maximum_length = max(len(left.segments), len(right.segments))
    effective_changes = maximum_length - metrics.same_take_positions
    if policy.reject_single_position_change and maximum_length >= 2 and effective_changes <= 1:
        return "single_position_change", metrics
    if metrics.same_take_positions / positions > policy.max_positional_take_match_ratio:
        return "positional_take_match", metrics
    if metrics.common_prefix_length / positions > policy.max_common_prefix_ratio:
        return "common_prefix", metrics
    if (
        positions >= 3
        and metrics.changed_thirds < policy.min_changed_thirds
        and metrics.same_take_positions / positions >= 0.50
    ):
        return "changes_concentrated_in_one_third", metrics
    return None, metrics


def rejection_reason(left: DiversityPlan, right: DiversityPlan, policy: DiversityPolicy) -> str | None:
    reason, _ = assess_pair(left, right, policy)
    return reason


def transitions(items: Sequence[str]) -> list[str]:
    return [f"{left}->{right}" for left, right in zip(items, items[1:], strict=False)]


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
