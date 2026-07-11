# Quick Mix Anti-Duplicate Planner Report

Status: integrated into the actual local `/video-mix` working contour, validated on tests and real media, ready for review.

Active local base branch:
- `codex/issue-41-source-materials-loading`

Integration branch:
- `assistant/quick-mix-anti-duplicates-integration`

Source PR preserved separately:
- `#54 Add Quick Mix anti-duplicate planner core`

Scope kept bounded:
- No merge into `master`.
- No change to PR `#54` head branch.
- Accepted Quick Mix anti-duplicate backend fix was transferred into the real local `/video-mix` contour.
- Existing Timeline / Project Materials / captions / orientation / dashboard/API contour was preserved by integrating on top of the actually running local branch state.

What is integrated:
- `video_mix/core/quick_mix_planner.py`
  - normalized source-group anti-duplicate planning;
  - explicit warning path when unique material is exhausted.
- `video_mix/service.py`
  - planner wiring inside `quick_mix_source_materials()`;
  - `reports/quick_mix_plan.json` generation;
  - warning metadata in report/API payloads;
  - legacy signature protection for already-seen combinations.
- `video_mix/core/media_probe.py`
  - ffprobe decode/probe fix preserved in the integration contour so real media durations reach planning correctly.
- `tests/test_video_mix_pipeline.py`
  - regression coverage for duration backfill.
- `tests/test_video_mix_dashboard_api.py`
  - API payload coverage for warning fields and plan path.

Validation run on integration worktree:

```powershell
python -m pytest tests/test_quick_mix_planner.py tests/test_video_mix_pipeline.py tests/test_video_mix_dashboard_api.py tests/test_video_mix_zip_intake.py -q
python -m ruff check video_mix/core/quick_mix_planner.py video_mix/core/media_probe.py video_mix/service.py tests/test_quick_mix_planner.py tests/test_video_mix_pipeline.py tests/test_video_mix_dashboard_api.py
node --check app/static/video-mix-dashboard.js
```

Observed results:
- `pytest`: `87 passed, 1 warning`
- warning source: duplicate-name fixture inside `tests/test_video_mix_zip_intake.py`
- `ruff`: clean
- `node --check`: clean

Real-media browser/server smoke used for final proof:
- integration server:
  - `http://127.0.0.1:8766/video-mix?lang=ru`
- source folder:
  - `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager\Фотографы_video_mix_work\imports\263dd0910e3241e4919fbe746611f383_Фотографы_acafe075`
- smoke work dir:
  - `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-pr54-integration\tmp\pr54_integration_smoke_wide`
- request:
  - `duration_seconds = 6`
  - `output_count = 2`
  - `episode_duration_min_seconds = 1.5`
  - `episode_duration_max_seconds = 2.0`

Smoke results:
- scan: `172 total / 27 supported video / 0 photo / 145 ignored dirs`
- quick mix: `generated_count = 2`
- `quick_mix_warning_count = 0`
- `quick_mix_plan_path = reports/quick_mix_plan.json`
- `reports/quick_mix_plan.json` present
- warning fields present in payload and report model

ffprobe results:
- `exports/quick_mix_001.mp4` requested `6.0 s`, actual `6.066016 s`
- `exports/quick_mix_002.mp4` requested `6.0 s`, actual `6.033008 s`

Anti-duplicate proof from `quick_mix_plan.json`:
- output 1 normalized source groups:
  - `whatsapp video 2026-07-03 at 10.21.53 pm.mp4`
  - `whatsapp video 2026-07-03 at 10.21.54 pm.mp4`
  - `whatsapp video 2026-07-03 at 10.21.52 pm.mp4`
  - `whatsapp video 2026-07-03 at 10.18.31 pm.mp4`
- output 2 normalized source groups:
  - `whatsapp video 2026-07-03 at 10.21.48 pm.mp4`
  - `новое видео.mp4`
  - `whatsapp video 2026-07-03 at 10.21.53 pm.mp4`
  - `whatsapp video 2026-07-03 at 10.21.49 pm.mp4`
- no duplicated `normalized_source_group` inside either output in the final proof smoke.

Important note from earlier narrow-folder smoke:
- a 7-file subset can still trigger relaxation warnings because unique groups are exhausted too early.
- the final acceptance smoke above used the broader 27-video photographers dataset requested in PR review context and produced `0` warnings.

Changed files in integration pass:
- `app/main.py`
- `app/static/app.js`
- `app/static/styles.css`
- `app/static/video-mix-dashboard.js`
- `app/storage.py`
- `app/templates/index.html`
- `app/templates/video_mix_dashboard.html`
- `app/video_mix_dashboard.py`
- `app/worker.py`
- `app/yt_service.py`
- `chrome_extension/background.js`
- `chrome_extension/options.html`
- `chrome_extension/options.js`
- `docs/README.md`
- `frontend-tests/video-mix-dashboard.test.mjs`
- `native_host/com.oleg.ytdlp.json`
- `native_host/ytdlp_host.py`
- `requirements.txt`
- `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md`
- `subtitle_studio/.gitignore`
- `subtitle_studio/README.md`
- `subtitle_studio/render-props.json`
- `subtitle_studio/src/Root.tsx`
- `tests/test_native_host_upload_limits.py`
- `tests/test_segment_api.py`
- `tests/test_segment_ydl_options.py`
- `tests/test_video_mix_dashboard_api.py`
- `tests/test_video_mix_pipeline.py`
- `tests/test_video_mix_zip_intake.py`
- `video_mix/core/asset_scan.py`
- `video_mix/core/media_probe.py`
- `video_mix/core/zip_intake.py`
- `video_mix/service.py`
- `workflow-runs/0003-video-mix-reel-mixer/27_QUICK_MIX_ANTI_DUPLICATE_PLANNER_REPORT.md`

Blockers:
- None.

Ready for review:
- Yes
