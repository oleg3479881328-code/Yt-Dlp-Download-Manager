# Quick Mix Anti-Duplicate Planner Report

Status: implemented, wired into backend Quick Mix generation, validated on tests and real media.

Branch:
- `assistant/quick-mix-anti-duplicates`

PR:
- `#54 Add Quick Mix anti-duplicate planner core`

Scope kept bounded:
- No merge into `master`.
- No force-push.
- Work stayed inside the Quick Mix backend path and its tests.
- Dashboard JS was validation-only (`node --check`), no new dashboard behavior was introduced in this fix pass.

What is implemented:
- `video_mix/core/quick_mix_planner.py`
  - normalized source-group planning for WhatsApp-style duplicates;
  - per-output anti-duplicate selection;
  - explicit relaxation warnings only when unique material is exhausted.
- `video_mix/service.py`
  - planner is wired into `quick_mix_source_materials()`;
  - serialized plan is written to `reports/quick_mix_plan.json`;
  - warning metadata is returned in `reports/quick_mix.json` and API payload.

Critical follow-up fix completed in this pass:
- `video_mix/core/media_probe.py`
  - fixed ffprobe JSON decoding / probing path so real media durations are preserved in planning instead of silently falling back to generic segment defaults.
- `tests/test_video_mix_pipeline.py`
  - added regression coverage for duration backfill with one short clip so planned output still reaches the requested total duration.

Root cause of the shortened-output defect:
- Real smoke previously produced `quick_mix_002.mp4 = 4.666667 s` while the request was `6.0 s`.
- The planner itself was already trying to fill to the requested duration, but some source assets arrived with `duration_ms = null`.
- When `duration_ms` was missing, the planner treated those sources as generic video segments and assigned a default full segment instead of respecting the real short-file duration.
- During actual render, FFmpeg could only output the real available frames from the short file, so the concatenated MP4 became shorter than planned.

Why the defect is fixed now:
- `probe_assets(...)` now records the real source duration correctly for the short file used in smoke (`696 ms`).
- Backfill planning now uses the real values.
- Verified plan example after the fix:
  - output 1 = `3000 + 2666 + 334 = 6000 ms`
  - output 2 = `3000 + 3000 = 6000 ms`
- Verified final exports by `ffprobe`:
  - `quick_mix_001.mp4 = 6.000000 s`
  - `quick_mix_002.mp4 = 6.000000 s`

Tests and validation run:
- `python -m pytest tests/test_quick_mix_planner.py -q`
- `python -m pytest tests/test_video_mix_pipeline.py -q`
- `python -m pytest tests/test_video_mix_dashboard_api.py -q`
- `python -m ruff check video_mix/core/quick_mix_planner.py tests/test_quick_mix_planner.py video_mix/service.py tests/test_video_mix_pipeline.py video_mix/core/media_probe.py`
- `node --check app/static/video-mix-dashboard.js`

Observed results:
- `tests/test_quick_mix_planner.py`: `5 passed`
- `tests/test_video_mix_pipeline.py`: `15 passed`
- `tests/test_video_mix_dashboard_api.py`: `13 passed`
- `ruff`: clean
- `node --check`: clean

Real-media smoke used for proof:
- Source folder:
  - `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager\Фотографы_video_mix_work\imports\263dd0910e3241e4919fbe746611f383_Фотографы_acafe075`
- Smoke work dir:
  - `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-pr54\tmp\pr54_quick_mix_smoke_work_2`
- Request:
  - `duration_seconds = 6`
  - `output_count = 2`

Real-media smoke proof:
- All 27 assets probed successfully: `27 ok / 0 failed`
- `quick_mix_warning_count = 0`
- `quick_mix_001.mp4 = 6.000000 s`
- `quick_mix_002.mp4 = 6.000000 s`

Current limitations:
- Reuse is still allowed when unique material is exhausted, but only via the existing explicit warning path.
- This report covers Quick Mix backend planning/generation only; it is not a broader VIDEO MIX UX report.

Ready for owner review:
- Yes
