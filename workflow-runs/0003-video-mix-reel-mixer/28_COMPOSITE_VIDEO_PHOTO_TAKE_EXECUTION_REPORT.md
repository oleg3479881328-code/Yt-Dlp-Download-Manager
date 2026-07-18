# Composite Video Photo Take Execution Report

Status: review-ready

Task source:
- GitHub Issue `#58`
- PR `#60`
- owner review comment:
  - `https://github.com/oleg3479881328-code/Yt-Dlp-Download-Manager/pull/60#issuecomment-5009072287`

Branch:
- `codex/issue-58-composite-takes`

Base branch:
- `codex/issue-41-source-materials-loading`

## 1. Scope of this follow-up pass

This pass fixes the standalone photo `asset_take` regression introduced during the composite Project Materials work.

Required outcome:

- ordinary `asset_take` must work for both video and photo assets
- strict media-type validation must remain only for `video_photo_composite`
- saved photo simple takes must remain plain `asset_take` records without composite-only fields
- existing video simple-take trim behavior must remain intact
- Quick Mix must continue accepting standalone photo material

No work from Issue `#59` or Issue `#61` was started.

## 2. Delivered behavior

### 2.1 Simple `asset_take` validation

`app/video_mix_dashboard.py` now separates simple-take validation from composite validation:

- simple `asset_take` allows:
  - `MediaType.VIDEO`
  - `MediaType.PHOTO`
- simple `asset_take` rejects only unsupported asset kinds outside that set
- the old video-only guard is removed from the simple-take branch

### 2.2 Composite validation remains strict

`video_photo_composite` behavior is unchanged:

- `video_asset_id` must resolve to a video asset
- every `photo_asset_ids` entry must resolve to a photo asset
- invalid photo-as-video or video-inside-photo-list requests still fail with HTTP `400`

### 2.3 Standalone photo Take persistence

Saved and re-saved photo simple takes now:

- stay `take_type = "asset_take"`
- keep `asset_id` pointing to the photo asset
- preserve `source_start_ms` / `source_end_ms`
- persist expected `duration_ms`
- do not gain composite-only fields

Confirmed absent from saved standalone photo simple takes:

- `video_asset_id`
- `photo_asset_ids`
- `photo_duration_ms`
- `photo_motion_mode`

## 3. Changed files

- `app/video_mix_dashboard.py`
- `tests/test_video_mix_dashboard_api.py`
- `tests/test_video_mix_pipeline.py`

## 4. Implementation details

### 4.1 Backend fix

Inside `update_project_material_take(...)`:

- simple-take asset lookup remains the same
- `_default_take_source_end_ms(asset)` is now used for both video and photo assets
- supported simple-take media types are checked with:
  - `VIDEO`
  - `PHOTO`
- trim-range validation remains active against the computed allowed end boundary

This means:

- video simple takes still validate against their existing duration rules
- photo simple takes now validate against the existing photo default duration path instead of failing the old video-only guard

### 4.2 Quick Mix compatibility

Project-material episode grouping continues to accept standalone photo `asset_take` entries and exposes them as valid body-source takes for Quick Mix.

## 5. Regression coverage

Added or extended regression coverage for:

1. standalone photo `asset_take` saves successfully
2. existing standalone photo `asset_take` re-saves successfully after editing allowed fields
3. photo simple take remains `asset_take`
4. saved photo simple take contains no composite-only fields
5. composite still rejects photo asset in `video_asset_id`
6. composite still rejects video asset inside `photo_asset_ids`
7. project-material state builder still accepts standalone photo take for Quick Mix
8. existing video simple-take trim path remains green through the full suite
9. prior composite / atomic / max-diversity regressions remain green through the full suite

## 6. Validation commands

Executed on Windows in the issue worktree:

```powershell
pytest -q
ruff check app tests video_mix
node --test frontend-tests\video-mix-dashboard.test.mjs
node --check app\static\video-mix-dashboard.js
```

Observed:

- `pytest -q` -> `152 passed, 1 warning`
- `ruff check app tests video_mix` -> clean
- `node --test frontend-tests\video-mix-dashboard.test.mjs` -> `6 passed`
- `node --check app\static\video-mix-dashboard.js` -> clean

Pytest warning:

- `tests/test_video_mix_zip_intake.py::test_zip_rejects_duplicate_normalized_destinations`
- underlying Python `zipfile` duplicate-name warning only

## 7. Local HTTP smoke

Verified with temporary local uvicorn run on `127.0.0.1:8876`:

- `/` -> HTTP `200`
- `/video-mix?lang=ru&work_dir=...` -> HTTP `200`
- `/api/video-mix/dashboard?work_dir=...` -> HTTP `200`

Smoke artifact:

- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_photo_take_smoke\http_smoke_result.json`

## 8. Photo `asset_take` live API smoke

Smoke workdir:

- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_photo_take_smoke\work`

Live HTTP flow:

1. create temporary workdir with photo asset `photo_1`
2. POST assign into `episode_001`
3. save simple photo take with:
   - `source_start_ms = 100`
   - `source_end_ms = 900`
4. reopen via returned `take_id`
5. re-save with:
   - `source_start_ms = 200`
   - `source_end_ms = 800`

Observed result:

- first save -> HTTP `200`
- second save -> HTTP `200`
- final take fields:
  - `take_type = "asset_take"`
  - `asset_id = "photo_1"`
  - `media_type = "photo"`
  - `source_start_ms = 200`
  - `source_end_ms = 800`
  - `duration_ms = 600`
- composite-only fields absent:
  - `video_asset_id = false`
  - `photo_asset_ids = false`
  - `photo_duration_ms = false`
  - `photo_motion_mode = false`

## 9. Notes

This follow-up does not change:

- composite content identity
- atomic composite planning
- max-diversity logic
- `video -> photos` composite structure

Those remain as delivered in the previous PR `#60` pass.

## 10. Ready state

Ready for review: Yes
