---
status: review-ready
project_mode: compact
current_step: 23_VIDEO_MIX_STAGE_1_8_SIMPLIFIED_SOURCE_TO_MP4_READY_FOR_REVIEW
current_run: workflow-runs/0003-video-mix-reel-mixer/
last_updated: 2026-06-27
next_action: Owner reviews the Stage 1.8 simplified source-to-MP4 execution report and PR linked from GitHub Issue #41.
---

# PROJECT STATE — yt-dlp Download Manager

VIDEO MIX Stage 1.1 Review UX is accepted and merged.

New active follow-up:

- Stage 1.2 review thumbnails
- GitHub Issue `#25`

Merged PR:

- #24 Add VIDEO MIX Stage 1.1 review UX

Merge commit:

- d827caa25e616a448d2ef483860d7823015e5056

Accepted current flow:

scan -> probe -> segment -> candidate manifests -> review -> approve -> MP4 export

Accepted module state:

- video_mix CLI now includes plan, review, approve, reject and export.
- review command creates a local static reports/review.html artifact.
- review.html shows candidate id, template id, status, score, duration, warnings, source clips, source filenames, tags and approve/reject instructions.

Execution artifacts:

- workflow-runs/0003-video-mix-reel-mixer/16_REVIEW_UX_TASK.md
- workflow-runs/0003-video-mix-reel-mixer/17_REVIEW_UX_EXECUTION_REPORT.md

Validation result:

- pytest passed
- ruff passed
- plan passed on synthetic media
- review passed
- local artifact created at video_mix_validation/work/reports/review.html
- generated artifacts remain ignored and uncommitted

Boundaries:

- no SaaS
- no posting automation
- no AI tagging
- no Remotion rendering
- no full dashboard
- no segmentation changes in this pass

Current Stage 1.2 focus:

- extend `video_mix review`
- generate local thumbnail JPGs for candidate clips
- render those thumbnails inside `reports/review.html`
- keep thumbnails local and ignored by git

Execution artifacts:

- `workflow-runs/0003-video-mix-reel-mixer/19_REVIEW_THUMBNAILS_EXECUTION_REPORT.md`

Validation result:

- pytest passed
- ruff passed
- plan passed on synthetic media
- review passed
- `review.html` created
- `10` local thumbnails created in `reports/thumbnails/`
- generated artifacts remain ignored and uncommitted

Boundaries:

- no dashboard UI
- no AI tagging
- no segmentation changes in this pass
- no export behavior changes except what review thumbnail generation needs

Current Stage 1.3 focus:

- add a local browser dashboard for existing `video_mix` work_dir state
- show pipeline steps, summary counts, candidate cards, thumbnails and export paths
- allow approve/reject directly from the dashboard
- keep the dashboard local-only and reuse the existing FastAPI app route pattern

Execution artifacts:

- `workflow-runs/0003-video-mix-reel-mixer/21_DASHBOARD_MVP_EXECUTION_REPORT.md`

Validation result:

- pytest passed
- ruff passed
- plan passed on synthetic media
- review passed
- FastAPI app imports and launches without `yt_dlp` installed unless downloader/analyze features are used
- `/video-mix` returned `200`
- `/api/video-mix/dashboard` returned live JSON for the synthetic work_dir

Boundaries:

- local dashboard only
- no SaaS
- no login/account system
- no AI tagging
- no segmentation changes in this pass
- no export logic redesign beyond calling the existing export flow

Current Stage 1.4 focus:

- add a one-click Windows launcher for the local VIDEO MIX dashboard
- auto-detect or accept a `work_dir`
- start the FastAPI server on `127.0.0.1:8765`
- open the browser automatically
- provide a first-run diagnostics mode with clear next steps

Execution artifacts:

- `workflow-runs/0003-video-mix-reel-mixer/22_DASHBOARD_LAUNCHER_EXECUTION_REPORT.md`

Validation result:

- pytest passed
- ruff passed
- launcher diagnostics mode passed
- launcher auto-detected `video_mix_validation/work`
- launcher started local FastAPI server and returned the expected dashboard URL
- dashboard URL returned `200`

Boundaries:

- local Windows helper only
- no SaaS
- no dashboard redesign
- no segmentation or export changes in this pass
- no AI tagging or Remotion work

Current next action:

Owner reviews Issue `#34`, the linked PR and `22_DASHBOARD_LAUNCHER_EXECUTION_REPORT.md`, then either accepts this launcher baseline or requests one isolated next pass.

Current Stage 1.6 focus:

- add dashboard-side filtering, sorting, selection and bulk actions for fast candidate triage
- keep the workflow local-only and reuse the existing review/export flow
- preserve single approve/reject behavior while adding bulk approve/reject

Execution artifacts:

- `workflow-runs/0003-video-mix-reel-mixer/23_DASHBOARD_REVIEW_CONTROLS_EXECUTION_REPORT.md`

Validation result:

- pytest passed
- ruff passed
- synthetic `plan` passed
- synthetic `review` passed
- launcher/dashboard smoke check passed
- dashboard URL returned `200`
- dashboard API returned `assets=5`, `clips=10`, `candidates=10`

Boundaries:

- dashboard review controls only
- local-only behavior
- no segmentation redesign
- no export redesign beyond calling the existing export flow
- no AI tagging or Remotion work

Current next action:

Owner reviews Issue `#37`, the linked PR and `23_DASHBOARD_REVIEW_CONTROLS_EXECUTION_REPORT.md`, then either accepts this dashboard review baseline or requests one isolated next pass.

Current Stage 1.7 focus:

- translate the owner-facing VIDEO MIX dashboard UI into Russian
- keep route paths, API values, enum values and existing dashboard behavior unchanged
- preserve the existing local review, bulk approve/reject and export-approved flow

Execution artifacts:

- `workflow-runs/0003-video-mix-reel-mixer/24_RUSSIAN_DASHBOARD_UI_EXECUTION_REPORT.md`

Validation result:

- frontend node tests passed
- dashboard API tests passed
- broader VIDEO MIX/dashboard pytest set passed
- `ruff` passed
- local launcher/dashboard smoke check passed
- dashboard URL returned `200`
- dashboard API returned `assets=5`, `clips=10`, `candidates=10`

Boundaries:

- Russian UI only
- no backend API contract changes
- no segmentation redesign
- no export redesign beyond the existing flow
- no AI tagging or Remotion work

Current next action:

Owner reviews Issue `#39`, the linked PR and `24_RUSSIAN_DASHBOARD_UI_EXECUTION_REPORT.md`, then either accepts this Russian dashboard baseline or requests one isolated next pass.

Current Stage 1.8 focus:

- keep the existing materials scan and work_dir flows intact
- add a direct `Quick Mix` path from source materials to finished MP4 outputs
- allow owner inputs:
  - source folder
  - duration seconds per output video
  - output count
- generate ready MP4 exports without forcing manual approve/reject first

Execution artifacts:

- `workflow-runs/0003-video-mix-reel-mixer/25_SIMPLIFIED_SOURCE_TO_MP4_MVP_EXECUTION_REPORT.md`

Validation result:

- frontend node tests passed
- broader VIDEO MIX/dashboard pytest set passed
- `ruff` passed
- live quick-mix endpoint smoke returned HTTP `200`
- local smoke generated `2` finished MP4 outputs
- both outputs were probeable:
  - `1080x1920`
  - `30fps`
  - `6.000000s`
- smoke source included both videos and a photo asset

Boundaries:

- local Windows dashboard only
- direct source-to-MP4 MVP only
- no SaaS
- no login
- no posting automation
- no AI tagging or Remotion work
- no `whiteboard_studio/` changes

Current next action:

Owner reviews Issue `#41`, the linked PR and `25_SIMPLIFIED_SOURCE_TO_MP4_MVP_EXECUTION_REPORT.md`, then either accepts this Quick Mix baseline or requests one isolated next pass.
