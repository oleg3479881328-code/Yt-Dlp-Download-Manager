from __future__ import annotations

from dataclasses import dataclass

from .quick_mix_planner import QuickMixSource

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
    content_identity: str = ""

    @property
    def window_id(self) -> str:
        return f"{self.source_id}@{self.source_start_ms}:{self.source_start_ms + self.duration_ms}"

    @property
    def material_identity(self) -> str:
        return self.content_identity or self.base_source_id

    @property
    def body_identity(self) -> str:
        return self.content_identity or self.window_id


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
        return tuple(segment.body_identity for segment in self.segments)

    @property
    def take_signature(self) -> tuple[str, ...]:
        return tuple(segment.source_id for segment in self.segments)

    @property
    def asset_signature(self) -> tuple[str, ...]:
        return tuple(segment.material_identity for segment in self.segments)

    @property
    def window_signature(self) -> tuple[str, ...]:
        return tuple(segment.window_id for segment in self.segments)

    @property
    def folder_signature(self) -> tuple[str, ...]:
        return tuple(segment.folder_id for segment in self.segments)


@dataclass(frozen=True, slots=True)
class PairMetrics:
    compared_positions: int
    same_take_positions: int
    same_asset_positions: int
    same_window_positions: int
    same_folder_positions: int
    common_take_prefix_length: int
    common_asset_prefix_length: int
    common_window_prefix_length: int
    longest_identical_take_run: int
    longest_identical_asset_run: int
    longest_identical_window_run: int
    take_overlap: int
    asset_overlap: int
    window_overlap: int
    folder_overlap: int
    folder_transition_overlap: int
    take_transition_overlap: int
    asset_transition_overlap: int
    window_transition_overlap: int
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
    asset_usage: dict[str, int]
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
