# Composite Video + Photo Take Execution Report

Status: review-ready

Task source:
- GitHub Issue `#58`
- branch: `codex/issue-58-composite-takes`
- target base branch: `codex/issue-41-source-materials-loading`

## 1. Scope delivered

Implemented a new editable composite Take type for VIDEO MIX:

```json
{
  "take_type": "video_photo_composite",
  "video_asset_id": "...",
  "photo_asset_ids": ["...", "..."],
  "photo_duration_ms": 1200,
  "photo_motion_mode": "static"
}
```

Delivered behavior:
- one full selected video Take as the base
- manually ordered photos appended only after the full video
- shared photo duration for the full photo tail
- motion mode per composite Take:
  - `static`
  - `ken_burns`
- persistent editable composite structure in `project_materials_state.json`
- Quick Mix treats the composite as one atomic body Take
- body uniqueness includes:
  - selected video asset
  - ordered photo asset IDs
  - shared photo duration
  - motion mode
- music / opening / closing are excluded from body uniqueness
- opening / closing are not injected into the middle of the composite body Take

## 2. Changed files

- `app/main.py`
- `app/static/styles.css`
- `app/static/video-mix-dashboard.js`
- `app/templates/video_mix_dashboard.html`
- `app/video_mix_dashboard.py`
- `tests/test_video_mix_dashboard_api.py`
- `tests/test_video_mix_pipeline.py`
- `video_mix/core/quick_mix_diversity_adapter.py`
- `video_mix/core/quick_mix_planner.py`
- `video_mix/service.py`
- `workflow-runs/0003-video-mix-reel-mixer/28_COMPOSITE_VIDEO_PHOTO_TAKE_EXECUTION_REPORT.md`

## 3. Data model and persistence

Backend now persists and reloads both:
- simple asset Take: `asset_take`
- composite Take: `video_photo_composite`

Composite persistence stores:
- base video asset ID
- ordered photo asset IDs
- shared photo duration
- shared motion mode

Composite reload behavior:
- invalid composite entries are rejected if video/photo assets are missing
- conversion back from composite to simple Take is supported
- duration for composite Take is recomputed as:

```text
full video duration + photo_count × photo_duration_ms
```

## 4. UI flow

Composite creation stays inside the existing Episode / Take editor flow:

1. choose Episode
2. assign a base video asset into the Episode
3. open the existing Take editor
4. switch Take type to `Видео + фото`
5. choose base video
6. add photos from Project Materials
7. reorder photos manually
8. remove photos manually
9. set shared photo duration
10. choose `Static` or `Ken Burns`
11. save the Take

Visible composite summary now carries:
- video file name
- photo count
- shared photo duration
- photo motion mode

## 5. Quick Mix / render integration

Quick Mix integration changes:
- composite Take is exported into episode groups as one atomic Take
- planner uses the full composite duration instead of slicing it into ordinary body windows
- render path creates:
  - full video segment first
  - then one rendered segment per photo in saved order
  - then concatenates them into one composite body segment

Photo render modes:
- `static` produces repeated still frames for the selected duration
- `ken_burns` applies FFmpeg `zoompan`-based motion with safe normalization into the existing vertical output pipeline

Uniqueness integration:
- composite body signature uses:
  - `video_asset_id`
  - ordered `photo_asset_ids`
  - `photo_duration_ms`
  - `photo_motion_mode`
- opening / closing / music are still excluded from body signature generation

## 6. Regression coverage

Added / updated regression coverage for:
- composite Take creation and persistence
- ordered photo list retention
- conversion composite -> simple Take
- signature change when photo order changes
- body signature ignoring music / markers for composite body uniqueness
- short-tail Quick Mix duration backfill still honoring requested output duration

## 7. Validation commands

Executed:

```powershell
pytest -q
ruff check app tests video_mix
node --test frontend-tests\video-mix-dashboard.test.mjs
node --check app\static\video-mix-dashboard.js
Invoke-WebRequest "http://127.0.0.1:8765/video-mix?lang=ru"
Invoke-WebRequest "http://127.0.0.1:8765/api/video-mix/dashboard?work_dir=C%3A%5CUsers%5Coleg3%5COneDrive%5CDocuments%5CYt-Dlp-Download-Manager-issue58%5Ctmp%5Cissue58_smoke%5Cwork_static"
```

Observed:
- `pytest -q` -> `140 passed, 1 warning`
- `ruff check app tests video_mix` -> clean
- `node --test frontend-tests\video-mix-dashboard.test.mjs` -> `6 passed`
- `node --check app\static\video-mix-dashboard.js` -> clean
- `/video-mix` -> HTTP `200`
- `/api/video-mix/dashboard` on smoke work_dir -> HTTP `200`

Note:
- repository-wide `ruff check` still reports pre-existing archive issues under `workflow-runs/0003-video-mix-reel-mixer/draft-code/`
- the implementation paths touched for Issue `#58` are clean

## 8. Real media smoke

Synthetic but real local FFmpeg/ffprobe media pack:
- one generated vertical MP4 base video
- two generated vertical JPG photos

Smoke root:
- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_smoke`

### Static composite

Work dir:
- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_smoke\work_static`

Output:
- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_smoke\work_static\quick_mix_generations\quick_mix_20260717T031947354991Z\exports\quick_mix_001.mp4`

Requested duration:
- `5.4s`

Actual `ffprobe` duration:
- `5.4s`

Saved summary:
- `video_file_name = base_video.mp4`
- `photo_count = 2`
- `photo_duration_ms = 1200`
- `photo_motion_mode = static`

Visual-order probes:
- `t=0.5s` center RGB -> `[0, 0, 254]` (blue video)
- `t=3.2s` center RGB -> `[254, 0, 0]` (first red photo)
- `t=4.5s` center RGB -> `[0, 128, 0]` (second green photo)

Static proof inside first photo segment:
- frame md5 at `3.15s` -> `da5918fbc11fb4eeb117bd8cb9fae685`
- frame md5 at `4.05s` -> `da5918fbc11fb4eeb117bd8cb9fae685`

### Ken Burns composite

Work dir:
- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_smoke\work_ken_burns`

Output:
- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_smoke\work_ken_burns\quick_mix_generations\quick_mix_20260717T031950671458Z\exports\quick_mix_001.mp4`

Requested duration:
- `5.4s`

Actual `ffprobe` duration:
- `5.4s`

Saved summary:
- `video_file_name = base_video.mp4`
- `photo_count = 2`
- `photo_duration_ms = 1200`
- `photo_motion_mode = ken_burns`

Visual-order probes:
- `t=0.5s` center RGB -> `[0, 0, 254]` (blue video)
- `t=3.2s` center RGB -> `[254, 0, 0]` (first red photo)
- `t=4.5s` center RGB -> `[0, 128, 0]` (second green photo)

Ken Burns proof inside first photo segment:
- frame md5 at `3.15s` -> `4a53f17cdc18486eedfce41c5e5ae11e`
- frame md5 at `4.05s` -> `73833364d07a519ccbb09bff3a1f63f4`

Interpretation:
- `static` keeps the repeated photo frame visually identical across the same photo interval
- `ken_burns` changes decoded frames over time inside the photo interval

## 9. Limits / non-goals preserved

Not added in this pass:
- random photo selection
- per-photo individual duration
- base video trim UI
- photo transitions beyond technical concat-safe rendering
- external cloud render / AI media analysis

## 10. Ready for review

Ready for review:
- Yes
