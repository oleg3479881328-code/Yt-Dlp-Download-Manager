# Quick Mix Max-Diversity Production Integration Report

Status: review-ready

PR contour:
- PR `#57`
- branch: `agent/quick-mix-max-diversity`
- scope: production integration of the already-added max-diversity planner into real `quick_mix_source_materials()`

What was integrated into the real production path:
- `video_mix/service.py`
  - switched body planning to the canonical max-diversity adapter path;
  - uses `allocate_generation_paths(...)` for generation-scoped exports, segments, reports and plan files;
  - loads previous generation plans through `load_prior_diversity_plans(...)`;
  - records generation history through `record_generation(...)`;
  - writes generation-scoped JSON artifacts through `write_generation_json(...)`;
  - preserves compatibility root report at `reports/quick_mix_plan.json`;
  - excludes pinned opening/closing from body selection by both:
    - `asset_id`
    - `normalize_quick_mix_source_group(asset.path)`
- `video_mix/core/quick_mix_diversity_adapter.py`
  - production adapter kept as the single bridge from `episode_groups/takes` to the max-diversity planner;
  - lint-safe asset path access preserved.
- `tests/test_video_mix_pipeline.py`
  - production regressions updated to validate the real planner contour instead of the legacy variant-attempt path.

Legacy production dependencies removed from the active Quick Mix generation path:
- no production dependency on the old `QUICK_MIX_VARIANT_SEARCH_ATTEMPTS = 192`
- no production dependency on old `used_variant_signatures`
- no silent `duplicate_fallback_plan` path in production rendering

Compatibility preserved:
- music path(s) and `use_music_duration`
- opening / closing media path(s) and `use_closing_duration`
- photos
- existing dashboard/API payload contour, with generation/diversity fields added
- Timeline / Project Materials / Take editor / ZIP intake code paths remain present in the branch contour

Changed repository files in this pass:
- `video_mix/service.py`
- `video_mix/core/quick_mix_diversity_adapter.py`
- `tests/test_video_mix_pipeline.py`
- `workflow-runs/0003-video-mix-reel-mixer/27_QUICK_MIX_ANTI_DUPLICATE_PLANNER_REPORT.md`

Validation commands:

```powershell
python -m pytest tests/test_quick_mix_planner.py tests/test_video_mix_pipeline.py tests/test_video_mix_dashboard_api.py tests/test_video_mix_zip_intake.py tests/test_quick_mix_generation.py tests/test_quick_mix_diversity_adapter.py -q
python -m ruff check app video_mix tests frontend-tests
node --test frontend-tests/video-mix-dashboard.test.mjs
node --check app/static/video-mix-dashboard.js
```

Observed results:
- `pytest`: `94 passed, 1 warning`
- warning source: duplicate ZIP entry fixture in `tests/test_video_mix_zip_intake.py`
- `ruff`: clean
- frontend node tests: `6 passed`
- `node --check`: clean

Real Windows `/video-mix` smoke:
- local server:
  - `http://127.0.0.1:8766/video-mix?lang=ru`
- route status:
  - `/video-mix?lang=ru` -> `200`
- source folder:
  - `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager\Фотографы_video_mix_work\imports\263dd0910e3241e4919fbe746611f383_Фотографы_acafe075`
- smoke work dir:
  - `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-pr57\tmp\pr57_comment_4949177470_smoke`
- scan result:
  - `173 total files`
  - `28 supported videos`
  - `0 photos`
  - `145 ignored / skipped`
- real render request:
  - `duration_seconds = 6`
  - `output_count = 10`
  - `episode_duration_min_seconds = 1.5`
  - `episode_duration_max_seconds = 2.0`
- real render result:
  - `generated_count = 10`
  - `generation_elapsed_ms = 20506`
  - `quick_mix_warning_count = 0`
  - generation-scoped output paths returned under `quick_mix_generations/...`

Plan-only 100-output proof (no mass render):
- requested outputs: `100`
- achieved outputs: `100`
- warnings: `0`
- minimum pairwise distance: `0.6666666666666667`
- average pairwise distance: `0.9303383838383839`
- maximum pairwise distance: `1.0`
- nearest-neighbour min: `0.6666666666666667`
- nearest-neighbour max: `0.7733333333333333`
- source usage min/max: `1 / 25`
- folder usage min/max: `25 / 73`
- pairwise rejection violations among selected plans: `0`
- planner-side rejected near-duplicate candidates during search:
  - `single_position_change = 1893`
  - `common_prefix = 31`

10 rendered MP4 durations via `ffprobe`:
- `quick_mix_001.mp4`: requested `6.0s`, actual `6.033333s`
- `quick_mix_002.mp4`: requested `6.0s`, actual `6.000000s`
- `quick_mix_003.mp4`: requested `6.0s`, actual `6.000000s`
- `quick_mix_004.mp4`: requested `6.0s`, actual `6.000000s`
- `quick_mix_005.mp4`: requested `6.0s`, actual `5.999023s`
- `quick_mix_006.mp4`: requested `6.0s`, actual `6.033333s`
- `quick_mix_007.mp4`: requested `6.0s`, actual `6.000000s`
- `quick_mix_008.mp4`: requested `6.0s`, actual `6.000000s`
- `quick_mix_009.mp4`: requested `6.0s`, actual `6.000000s`
- `quick_mix_010.mp4`: requested `6.0s`, actual `6.033333s`

Production acceptance points covered:
- `quick_mix_source_materials()` now calls the canonical max-diversity planner path
- prior generation plans participate in new diversity selection
- reruns use generation-scoped outputs instead of overwriting older exports
- identical / near-identical patterns are rejected by the selected-plan set
- exhaustion is surfaced explicitly through warning metadata
- output indices in manifests remain 1-based
- pinned opening / closing exclusions use real asset IDs and normalized source groups

Known limits:
- the legacy Quick Mix contour still coexists in the repository for compatibility and tests, but production body selection now runs through the max-diversity contour
- the planner can still report explicit exhaustion warnings on materially tiny datasets; that is expected and now observable instead of silently falling back to duplicates

Ready for review:
- Yes
