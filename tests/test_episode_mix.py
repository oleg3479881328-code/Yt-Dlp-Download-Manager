from video_mix.core.episode_mix import (
    Episode,
    EpisodeTake,
    MixSettings,
    TakeMediaType,
    build_mix_plan,
    duplicate_episode,
)


def _take(take_id: str, media_item_id: str | None = None, **overrides) -> EpisodeTake:
    payload = {
        "take_id": take_id,
        "label": take_id,
        "media_item_id": media_item_id or take_id,
        "source_start_ms": 0,
        "source_end_ms": 3_000,
    }
    payload.update(overrides)
    return EpisodeTake(**payload)


def test_build_mix_plan_is_deterministic_with_seed() -> None:
    episodes = [
        Episode(
            episode_id="episode_1",
            label="Opening",
            position=1,
            takes=[_take("take_1"), _take("take_2"), _take("take_3")],
        ),
        Episode(
            episode_id="episode_2",
            label="Details",
            position=2,
            takes=[_take("take_4"), _take("take_5"), _take("take_6")],
        ),
    ]

    first = build_mix_plan(episodes, MixSettings(reel_count=3, seed=42))
    second = build_mix_plan(episodes, MixSettings(reel_count=3, seed=42))

    assert [[item.take_id for item in recipe.items] for recipe in first.recipes] == [
        [item.take_id for item in recipe.items] for recipe in second.recipes
    ]
    assert first.seed == 42


def test_disabled_take_is_not_used_and_forced_take_goes_to_all_reels() -> None:
    episodes = [
        Episode(
            episode_id="episode_1",
            label="Opening",
            position=1,
            takes=[
                _take("forced", use_in_all_reels=True),
                _take("disabled", enabled_for_mix=False),
                _take("normal"),
            ],
        )
    ]

    plan = build_mix_plan(episodes, MixSettings(reel_count=4, seed=7))

    assert all(recipe.items[0].take_id == "forced" for recipe in plan.recipes)
    assert "disabled" not in {item.take_id for recipe in plan.recipes for item in recipe.items}


def test_take_can_be_excluded_from_specific_reel() -> None:
    episodes = [
        Episode(
            episode_id="episode_1",
            label="Opening",
            position=1,
            takes=[
                _take("only_for_other_reels", excluded_from_reel_ids=["reel_002"]),
                _take("fallback"),
            ],
        )
    ]

    plan = build_mix_plan(episodes, MixSettings(reel_count=2, seed=1))
    reel_2_take_ids = {item.take_id for item in plan.recipes[1].items}

    assert "only_for_other_reels" not in reel_2_take_ids


def test_audio_and_extracted_audio_are_valid_takes_but_do_not_extend_visual_duration_metric() -> None:
    episodes = [
        Episode(
            episode_id="episode_1",
            label="Opening",
            position=1,
            takes=[_take("video", media_type=TakeMediaType.VIDEO, source_end_ms=3_000)],
        ),
        Episode(
            episode_id="episode_music",
            label="Music",
            position=2,
            takes=[_take("music", media_type=TakeMediaType.AUDIO, source_end_ms=10_000)],
        ),
        Episode(
            episode_id="episode_extracted_audio",
            label="Extracted audio",
            position=3,
            takes=[_take("extracted", media_type=TakeMediaType.EXTRACTED_AUDIO, source_end_ms=8_000)],
        ),
    ]

    plan = build_mix_plan(episodes, MixSettings(reel_count=1, seed=11))
    recipe = plan.recipes[0]

    assert {item.media_type for item in recipe.items} == {
        TakeMediaType.VIDEO,
        TakeMediaType.AUDIO,
        TakeMediaType.EXTRACTED_AUDIO,
    }
    assert recipe.total_known_duration_ms == 3_000


def test_duplicate_episode_creates_independent_take_ids() -> None:
    original = Episode(
        episode_id="episode_1",
        label="Opening",
        position=1,
        takes=[_take("take_1"), _take("take_2")],
    )

    duplicate = duplicate_episode(original, "episode_2", label="Opening copy", position=2)

    assert duplicate.episode_id == "episode_2"
    assert duplicate.label == "Opening copy"
    assert duplicate.position == 2
    assert [take.take_id for take in duplicate.takes] == ["episode_2_take_1", "episode_2_take_2"]
    assert [take.take_id for take in original.takes] == ["take_1", "take_2"]


def test_missing_required_episode_produces_warning() -> None:
    episodes = [
        Episode(
            episode_id="episode_empty",
            label="Empty required episode",
            position=1,
            takes=[_take("disabled", enabled_for_mix=False)],
        )
    ]

    plan = build_mix_plan(episodes, MixSettings(reel_count=1, seed=5))

    assert "missing_required_episode:episode_empty" in plan.recipes[0].warnings
