from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TakeMediaType(StrEnum):
    VIDEO = "video"
    PHOTO = "photo"
    AUDIO = "audio"
    EXTRACTED_AUDIO = "extracted_audio"
    TITLE_CARD = "title_card"


@dataclass(slots=True)
class EpisodeTake:
    """One concrete media option inside an episode/block.

    A take is intentionally media-neutral: video, photo, standalone audio,
    audio extracted from video, and title cards can all participate in the
    same episode/take/mix flow.
    """

    take_id: str
    label: str
    media_item_id: str
    media_type: TakeMediaType = TakeMediaType.VIDEO
    source_start_ms: int = 0
    source_end_ms: int | None = None
    enabled_for_mix: bool = True
    use_in_all_reels: bool = False
    excluded_from_reel_ids: list[str] = field(default_factory=list)
    allowed_reel_ids: list[str] = field(default_factory=list)
    locked_to_reel_ids: list[str] = field(default_factory=list)
    weight: int = 1
    max_uses: int | None = None
    volume: float = 1.0
    muted: bool = False
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> int:
        if self.source_end_ms is None:
            return 0
        return max(0, self.source_end_ms - self.source_start_ms)


@dataclass(slots=True)
class Episode:
    """A meaningful reel block containing alternative takes."""

    episode_id: str
    label: str
    position: int
    takes: list[EpisodeTake] = field(default_factory=list)
    required: bool = True
    min_takes_per_reel: int = 1
    max_takes_per_reel: int = 1
    target_duration_ms: int | None = None
    min_duration_ms: int | None = None
    max_duration_ms: int | None = None
    shuffle_enabled: bool = True
    allow_repeat_across_reels: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReelRecipeItem:
    reel_id: str
    episode_id: str
    episode_label: str
    take_id: str
    take_label: str
    media_item_id: str
    media_type: TakeMediaType
    source_start_ms: int
    source_end_ms: int | None
    role: str = "selected"
    volume: float = 1.0
    muted: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> int:
        if self.source_end_ms is None:
            return 0
        return max(0, self.source_end_ms - self.source_start_ms)


@dataclass(slots=True)
class ReelRecipe:
    reel_id: str
    items: list[ReelRecipeItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_known_duration_ms(self) -> int:
        """Best-effort duration sum for ordered visual episodes.

        Audio can overlap the visual track later, so this is only a simple MVP
        recipe metric, not a final render-duration guarantee.
        """

        return sum(item.duration_ms for item in self.items if item.media_type != TakeMediaType.AUDIO)


@dataclass(slots=True)
class MixPlan:
    seed: int
    recipes: list[ReelRecipe]
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MixSettings:
    reel_count: int
    seed: int | None = None
    reel_id_prefix: str = "reel"
    avoid_same_media_item_in_reel: bool = True


class MixPlanError(ValueError):
    pass


def duplicate_episode(
    episode: Episode,
    new_episode_id: str,
    *,
    label: str | None = None,
    position: int | None = None,
) -> Episode:
    """Duplicate an episode while making take ids independent."""

    duplicate = deepcopy(episode)
    duplicate.episode_id = new_episode_id
    duplicate.label = label or f"{episode.label} copy"
    duplicate.position = episode.position if position is None else position
    for take in duplicate.takes:
        take.take_id = f"{new_episode_id}_{take.take_id}"
    return duplicate


def build_mix_plan(episodes: list[Episode], settings: MixSettings) -> MixPlan:
    """Create deterministic reel recipes from episode/take rules.

    This function is intentionally render-free. It only produces a dry-run
    recipe plan that can be reviewed, locked/regenerated later, and then handed
    to the FFmpeg export layer.
    """

    if settings.reel_count <= 0:
        raise MixPlanError("reel_count must be greater than zero")

    seed = settings.seed if settings.seed is not None else random.SystemRandom().randint(1, 999_999_999)
    rng = random.Random(seed)
    ordered_episodes = sorted(episodes, key=lambda episode: episode.position)
    usage_counts: dict[str, int] = {}
    recipes: list[ReelRecipe] = []
    plan_warnings: list[str] = []

    for reel_index in range(1, settings.reel_count + 1):
        reel_id = f"{settings.reel_id_prefix}_{reel_index:03d}"
        recipe = ReelRecipe(reel_id=reel_id)
        used_media_item_ids: set[str] = set()

        for episode in ordered_episodes:
            picked = _pick_episode_takes(
                episode,
                reel_id=reel_id,
                rng=rng,
                usage_counts=usage_counts,
                used_media_item_ids=used_media_item_ids,
                avoid_same_media_item_in_reel=settings.avoid_same_media_item_in_reel,
            )
            recipe.warnings.extend(picked.warnings)
            if not picked.takes:
                if episode.required:
                    recipe.warnings.append(f"missing_required_episode:{episode.episode_id}")
                continue

            for take, role in picked.takes:
                recipe.items.append(_build_recipe_item(reel_id, episode, take, role))
                usage_counts[take.take_id] = usage_counts.get(take.take_id, 0) + 1
                used_media_item_ids.add(take.media_item_id)

        recipes.append(recipe)
        plan_warnings.extend(recipe.warnings)

    return MixPlan(seed=seed, recipes=recipes, warnings=plan_warnings)


@dataclass(slots=True)
class _PickedTakes:
    takes: list[tuple[EpisodeTake, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _pick_episode_takes(
    episode: Episode,
    *,
    reel_id: str,
    rng: random.Random,
    usage_counts: dict[str, int],
    used_media_item_ids: set[str],
    avoid_same_media_item_in_reel: bool,
) -> _PickedTakes:
    result = _PickedTakes()
    if episode.max_takes_per_reel < 1:
        result.warnings.append(f"invalid_max_takes:{episode.episode_id}")
        return result

    locked = [take for take in episode.takes if reel_id in take.locked_to_reel_ids and _take_allowed_for_reel(take, reel_id)]
    forced = [take for take in episode.takes if take.use_in_all_reels and _take_allowed_for_reel(take, reel_id)]

    selected: list[tuple[EpisodeTake, str]] = []
    for take in locked:
        _append_unique_take(selected, take, "locked")
    for take in forced:
        _append_unique_take(selected, take, "forced")

    if len(selected) > episode.max_takes_per_reel:
        result.warnings.append(f"too_many_forced_or_locked_takes:{episode.episode_id}")
        selected = selected[: episode.max_takes_per_reel]

    needed = max(episode.min_takes_per_reel, 0) - len(selected)
    slots_left = episode.max_takes_per_reel - len(selected)
    pick_count = min(max(needed, 0), max(slots_left, 0))

    candidates = [
        take
        for take in episode.takes
        if _take_allowed_for_reel(take, reel_id)
        and take.take_id not in {selected_take.take_id for selected_take, _ in selected}
        and _take_allowed_by_usage(take, episode, usage_counts)
        and (
            not avoid_same_media_item_in_reel
            or take.media_item_id not in used_media_item_ids
            or take.use_in_all_reels
        )
    ]

    for _ in range(pick_count):
        if not candidates:
            result.warnings.append(f"not_enough_enabled_takes:{episode.episode_id}")
            break
        take = _weighted_choice(candidates, rng)
        _append_unique_take(selected, take, "selected")
        candidates = [candidate for candidate in candidates if candidate.take_id != take.take_id]

    for take, _ in selected:
        _append_duration_warnings(result.warnings, episode, take)

    result.takes = selected
    return result


def _take_allowed_for_reel(take: EpisodeTake, reel_id: str) -> bool:
    if not take.enabled_for_mix:
        return False
    if reel_id in take.excluded_from_reel_ids:
        return False
    if take.allowed_reel_ids and reel_id not in take.allowed_reel_ids:
        return False
    return True


def _take_allowed_by_usage(take: EpisodeTake, episode: Episode, usage_counts: dict[str, int]) -> bool:
    current_uses = usage_counts.get(take.take_id, 0)
    if take.use_in_all_reels:
        return True
    if take.max_uses is not None and current_uses >= take.max_uses:
        return False
    if not episode.allow_repeat_across_reels and current_uses > 0:
        return False
    return True


def _weighted_choice(takes: list[EpisodeTake], rng: random.Random) -> EpisodeTake:
    weights = [max(0, take.weight) for take in takes]
    if not any(weights):
        weights = [1 for _ in takes]
    return rng.choices(takes, weights=weights, k=1)[0]


def _append_unique_take(selected: list[tuple[EpisodeTake, str]], take: EpisodeTake, role: str) -> None:
    if take.take_id in {existing.take_id for existing, _ in selected}:
        return
    selected.append((take, role))


def _append_duration_warnings(warnings: list[str], episode: Episode, take: EpisodeTake) -> None:
    if take.source_end_ms is None:
        return
    if episode.min_duration_ms is not None and take.duration_ms < episode.min_duration_ms:
        warnings.append(f"take_too_short:{episode.episode_id}:{take.take_id}")
    if episode.max_duration_ms is not None and take.duration_ms > episode.max_duration_ms:
        warnings.append(f"take_too_long:{episode.episode_id}:{take.take_id}")


def _build_recipe_item(reel_id: str, episode: Episode, take: EpisodeTake, role: str) -> ReelRecipeItem:
    return ReelRecipeItem(
        reel_id=reel_id,
        episode_id=episode.episode_id,
        episode_label=episode.label,
        take_id=take.take_id,
        take_label=take.label,
        media_item_id=take.media_item_id,
        media_type=take.media_type,
        source_start_ms=take.source_start_ms,
        source_end_ms=take.source_end_ms,
        role=role,
        volume=take.volume,
        muted=take.muted,
        metadata={"take_notes": take.notes, **take.metadata},
    )
