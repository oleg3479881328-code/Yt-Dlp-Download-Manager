# Quick Mix Anti-Duplicate Follow-up Report

Status: review-ready

PR contour:
- PR `#57`
- branch: `agent/quick-mix-max-diversity`
- task source: PR comment `#4949617249`
- scope: close two confirmed defects without changing the broader max-diversity architecture

Changed files in this pass:
- `video_mix/core/quick_mix_diversity_models.py`
- `video_mix/core/quick_mix_diversity_metrics.py`
- `video_mix/core/quick_mix_diversity_selection.py`
- `video_mix/core/quick_mix_diversity_candidates.py`
- `video_mix/service.py`
- `tests/test_quick_mix_diversity.py`
- `tests/test_video_mix_pipeline.py`
- `workflow-runs/0003-video-mix-reel-mixer/27_QUICK_MIX_ANTI_DUPLICATE_PLANNER_REPORT.md`

## 1. Three-level similarity and hard rejection

Implemented comparison levels:
- Take-level: `source_id`
- Asset-level: `base_source_id`
- Window-level: `source_id@start:end`

Implemented metric split:
- positional matches:
  - `same_take_positions`
  - `same_asset_positions`
  - `same_window_positions`
- prefix overlap:
  - `common_take_prefix_length`
  - `common_asset_prefix_length`
  - `common_window_prefix_length`
- longest runs:
  - `longest_identical_take_run`
  - `longest_identical_asset_run`
  - `longest_identical_window_run`
- overlaps:
  - `take_overlap`
  - `asset_overlap`
  - `window_overlap`
- transitions:
  - `take_transition_overlap`
  - `asset_transition_overlap`
  - `window_transition_overlap`

Hard rejection now fires on Take-level and Asset-level before window-only differences can mask duplicates:
- `exact_take_duplicate`
- `exact_asset_duplicate`
- `single_position_change`
- `positional_take_match`
- `positional_asset_match`
- `common_prefix`
- `asset_common_prefix`

Window-level remains only an extra diversity signal inside already-different Take / asset plans.

Also tightened candidate generation:
- dedupe key now uses `take_signature`, not window-only signature
- source sampling prefers materially unique `base_source_id` and `source_group`
- when the dataset can support it, repeated asset/group reuse inside one plan is rejected during candidate build

## 2. Full generation manifest

`outputs[].segments` now stores the real full sequence for every output in both:
- generation-scoped `quick_mix_generations/.../reports/quick_mix_plan.json`
- compatibility `reports/quick_mix_plan.json`

Each segment now records:
- `segment_kind`
- `asset_id`
- `base_source_id`
- `source_id`
- `source_group`
- `source_path`
- `source_start_ms`
- `duration_ms`
- `full_timeline_position`
- `folder_id`
- `media_type`

`body_visual_signature` still stays body-only by design.

## Regression tests added / updated

`tests/test_quick_mix_diversity.py`
- same `source_id` sequence with different windows -> `exact_take_duplicate`
- 4 of 5 same Take positions with different windows -> `single_position_change`
- same asset sequence with different Take IDs / windows -> `exact_asset_duplicate`
- truly different Take sequence is farther than same Take sequence with shifted windows

`tests/test_video_mix_pipeline.py`
- compatibility + generation-scoped manifest contain `opening -> body -> closing`
- body signature remains body-only
- opening / closing sources stay absent from body segments
- segment duration sum equals `generated_duration_ms`
- generation-scoped and compatibility output plans are identical
- prior-plan rejection remains independent from different music file / `music_start_ms`

## Validation commands

```powershell
python -m pytest tests/test_quick_mix_planner.py tests/test_quick_mix_diversity.py tests/test_quick_mix_diversity_adapter.py tests/test_quick_mix_generation.py tests/test_video_mix_pipeline.py tests/test_video_mix_dashboard_api.py tests/test_video_mix_zip_intake.py -q
python -m ruff check app video_mix tests frontend-tests
node --test frontend-tests/video-mix-dashboard.test.mjs
node --check app/static/video-mix-dashboard.js
```

Observed:
- `pytest`: `109 passed, 1 warning`
- warning source: duplicate ZIP entry fixture in `tests/test_video_mix_zip_intake.py`
- `ruff`: clean
- frontend node tests: `6 passed`
- `node --check`: clean

## 100-output plan-only proof

Dataset:
- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager\Фотографы_video_mix_work\imports\263dd0910e3241e4919fbe746611f383_Фотографы_acafe075`

Requested / achieved:
- requested outputs: `100`
- achieved outputs: `100`
- warnings: `0`

Distances:
- minimum pairwise distance: `0.5700000000000001`
- average pairwise distance: `0.9411861952861953`
- maximum pairwise distance: `1.0`
- nearest-neighbour min: `0.5700000000000001`
- nearest-neighbour max: `0.695`

Selected-plan violation checks:
- pairwise violation count: `0`
- Take-level violation count: `0`
- Asset-level violation count: `0`

Rejected counts by reason from the selected-set recheck:
- none observed in the final selected 100-plan set

Usage distribution:
- Take usage min/max: `1 / 23`
- Asset usage min/max: `5 / 23`
- Folder usage min/max: `23 / 73`

Interpretation:
- the selected set contains no duplicate Take-level sequences
- changing only start offsets no longer upgrades the same Take plan into a far plan
- asset-level similarity now stays strong even when Take/window IDs differ

## Real Windows smoke: 10 MP4

Smoke work dir:
- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-pr57\tmp\pr57_comment_4949617249_validation_rerun\smoke_work`

Request contour:
- duration source: manual
- requested duration: `6.0s`
- actual generated timeline target with pinned ending: `8.089s`
- body episode window: `1.5s .. 2.0s`
- output count: `10`
- music: none
- opening pinned: yes
- closing pinned: yes
- `use_closing_duration = true`

Real render result:
- generated outputs: `10 / 10`
- generation elapsed: `26835 ms`
- videos in dataset: `28`
- photos in dataset: `0`
- warnings: `0`

`ffprobe` durations:
- `quick_mix_001.mp4`: requested `8.089s`, actual `8.066667s`
- `quick_mix_002.mp4`: requested `8.089s`, actual `8.066667s`
- `quick_mix_003.mp4`: requested `8.089s`, actual `8.065365s`
- `quick_mix_004.mp4`: requested `8.089s`, actual `8.066667s`
- `quick_mix_005.mp4`: requested `8.089s`, actual `8.066667s`
- `quick_mix_006.mp4`: requested `8.089s`, actual `8.033333s`
- `quick_mix_007.mp4`: requested `8.089s`, actual `8.066667s`
- `quick_mix_008.mp4`: requested `8.089s`, actual `8.033333s`
- `quick_mix_009.mp4`: requested `8.089s`, actual `8.100000s`
- `quick_mix_010.mp4`: requested `8.089s`, actual `8.066667s`

## Full manifest proof

Compatibility vs generation-scoped:
- first output identical in both manifests: `true`

Observed segment kinds for first rendered output:
- `opening`
- `body`
- `body`
- `closing`

Body-only signature:
- `asset_1d41cae04044_take_001@6000:9000`
- `asset_5d2ba10596b9_take_002@15000:16000`

Duration consistency:
- `generated_duration_ms = 8089`
- `sum(outputs[0].segments[].duration_ms) = 8089`

Body manifest proof:
- opening absent from body segments: `true`
- closing absent from body segments: `true`

## Notes / limitations

- This fix deliberately does not add visual-content analysis; it only corrects structural anti-duplicate logic across Take / asset / window levels.
- The validation dataset is video-only (`0` photos), so photo-specific diversity was not expanded in this pass.
- The selected-set recheck produced zero final-policy violations; therefore the new rejection categories are demonstrated by regression tests rather than by non-zero selected-set counts in the 100-plan audit.

Ready for review:
- Yes
