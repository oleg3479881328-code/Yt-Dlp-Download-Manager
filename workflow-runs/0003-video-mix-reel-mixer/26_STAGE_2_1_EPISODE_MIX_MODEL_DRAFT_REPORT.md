# Stage 2.1 Draft Report — Episode Mix Model

## Status

Draft implementation prepared for review.

This pass intentionally adds only the pure backend planning layer for the new VIDEO MIX model:

```text
Episode -> Takes -> Mix Plan -> Reel Recipes
```

It does not modify the current dashboard, Quick Mix export behavior, FFmpeg rendering, or existing Stage 1 flows.

## Owner requirement captured

The owner clarified that VIDEO MIX must introduce the concept of an `Episode`:

- an episode is a meaningful block in a reel;
- each episode contains multiple `Takes` / дублей;
- the mix algorithm selects takes from episodes to create many unique reels;
- individual takes can be enabled, disabled, forced into all reels, excluded from selected reels, or locked later.

The owner also clarified that audio must use the same model:

- standalone audio files;
- audio extracted from video files;
- music/audio slots as episode-like blocks.

## Files added

- `video_mix/core/episode_mix.py`
- `tests/test_episode_mix.py`

## Implemented model

### `TakeMediaType`

Supported media-neutral take types:

- `video`
- `photo`
- `audio`
- `extracted_audio`
- `title_card`

### `EpisodeTake`

A concrete media option inside an episode.

Important fields:

- `enabled_for_mix`
- `use_in_all_reels`
- `excluded_from_reel_ids`
- `allowed_reel_ids`
- `locked_to_reel_ids`
- `weight`
- `max_uses`
- `volume`
- `muted`

### `Episode`

A meaningful block containing multiple takes.

Important fields:

- `position`
- `required`
- `min_takes_per_reel`
- `max_takes_per_reel`
- `min_duration_ms`
- `max_duration_ms`
- `allow_repeat_across_reels`

### `MixSettings`

Dry-run settings:

- `reel_count`
- `seed`
- `reel_id_prefix`
- `avoid_same_media_item_in_reel`

### `MixPlan` / `ReelRecipe`

The output is a dry-run recipe plan, not rendered media.

This keeps Stage 2.1 non-destructive and reviewable before FFmpeg export.

## Implemented behavior

- Deterministic recipe generation with a stored seed.
- Episode ordering by `position`.
- Forced takes via `use_in_all_reels`.
- Disabled takes ignored.
- Per-reel exclusion through `excluded_from_reel_ids`.
- Optional allow-list through `allowed_reel_ids`.
- Locked take support through `locked_to_reel_ids`.
- Weight-biased selection.
- `max_uses` support.
- Required-episode warning when no eligible take is found.
- Simple duration warnings.
- Audio and extracted audio can participate in mix recipes.
- Audio/extracted audio do not inflate the simple visual duration metric.
- Episode duplication helper creates independent take ids.

## Tests added

`tests/test_episode_mix.py` covers:

- deterministic generation with a fixed seed;
- disabled take is never used;
- forced take appears in all reels;
- take exclusion from a specific reel;
- audio and extracted audio as valid takes;
- duplicated episode has independent take ids;
- missing required episode warning.

## Validation status

Not locally executed in this ChatGPT session.

Recommended executor command:

```powershell
pytest tests/test_episode_mix.py
ruff check video_mix/core/episode_mix.py tests/test_episode_mix.py
```

Then run the existing broader VIDEO MIX checks before merge.

## What this enables next

This draft gives the executor a concrete backend foundation for:

1. episode rows in the UI;
2. take cards inside each episode;
3. checkboxes for `use in mix`, `use in all reels`, `exclude`;
4. dry-run mix plan preview;
5. later FFmpeg export from selected recipe plans.

## Explicit non-goals in this pass

- No full timeline UI.
- No React migration.
- No FFmpeg renderer changes.
- No Quick Mix behavior changes.
- No dashboard route changes.
- No public-product or SaaS work.
