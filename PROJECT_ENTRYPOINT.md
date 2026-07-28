# PROJECT ENTRYPOINT — yt-dlp Download Manager

## Project

Personal local Windows video toolkit.

Repository:

- `oleg3479881328-code/Yt-Dlp-Download-Manager`

## Project Goal

Local tool for:

- media download through `yt-dlp`;
- web dashboard and Chrome extension download control;
- subtitle/text creation;
- animated subtitle video creation;
- future bounded video analysis;
- active planning: `VIDEO MIX` / scalable Reel Mixer Engine.

## Project Mode

- mode: `compact`
- use case: personal local tool only
- source of truth: this GitHub repository
- active run: `workflow-runs/0004-instagram-extension-refresh/`

## Required Read Order

1. `PROJECT_STATE.md`
2. `PROJECT_RULES.md`
3. `logs/PROJECT_LOG.md`
4. `workflow-runs/0004-instagram-extension-refresh/`
5. `workflow-runs/0004-instagram-extension-refresh/03_ONE_CLICK_CONTEXT_MENU_EXECUTION_REPORT.md`
6. `workflow-runs/0004-instagram-extension-refresh/04_STABLE_UPDATER_EXECUTION_REPORT.md`
7. Draft GitHub PR `#71` and Issues `#69` and `#70`
8. `workflow-runs/0002-animated-subtitle-module/` only if subtitle/rendering context is needed.
9. `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md` only if needed.

## Verified Current Components

- `app/` — FastAPI web dashboard, SQLite state and download worker.
- `chrome_extension/` — standalone Chrome extension.
- `native_host/` — native messaging host.
- local transcription through `faster-whisper`.
- `subtitle_studio/` — accepted Remotion Phase 1 MVP.
- `video_mix/` — local Stage 1 VIDEO MIX implementation with review thumbnails.
- `app/video_mix_dashboard.py` + `/video-mix` — local dashboard MVP for VIDEO MIX review.
- `start_video_mix_dashboard.ps1` — one-click Windows launcher for VIDEO MIX dashboard.
- dashboard review controls — filters, sorting, selection and bulk approve/reject actions.
- Russian dashboard UI — localized labels, messages and visible statuses for owner-facing review work.
- simplified Quick Mix workflow — source folder + seconds + count -> ready MP4 outputs.
- `workflow-runs/0003-video-mix-reel-mixer/` — active VIDEO MIX planning and execution package.
- `workflow-runs/0004-instagram-extension-refresh/` — current Chrome extension/native host Instagram compatibility refresh.

## Active Work — Instagram Extension Refresh

The current owner-authorized task is a narrow refresh of the existing standalone Chrome extension/native host:

- keep `yt-dlp.exe` current through a rate-limited update check
- expose manual update and installed-version diagnostics
- use a current MP4 video-plus-audio command for Instagram Reels
- support explicit browser-cookie and request-impersonation fallbacks without enabling them by default
- preserve non-Instagram playlist behavior
- make context-menu download immediate and open the output folder after successful completion
- provide a stable local installation and one-command GitHub updater

Coordination and validation:

- GitHub Issues `#68`, `#69` and `#70`
- Draft GitHub PR `#71`
- `workflow-runs/0004-instagram-extension-refresh/03_ONE_CLICK_CONTEXT_MENU_EXECUTION_REPORT.md`
- `workflow-runs/0004-instagram-extension-refresh/04_STABLE_UPDATER_EXECUTION_REPORT.md`

## Active Work — VIDEO MIX

`VIDEO MIX` is a local Stage 1 module inside this repository.

Purpose:

- batch-generate short vertical Reels from local media packages;
- first pilot: wedding photographer materials;
- long-term design: reusable core plus industry packs.

Core architecture:

```text
VIDEO MIX
├── Reel Mixer Core
└── Industry Packs
```

The first pack is only a pilot. The core must remain reusable.

## Current VIDEO MIX Artifacts

- `workflow-runs/0003-video-mix-reel-mixer/01_OWNER_BRIEF.md`
- `workflow-runs/0003-video-mix-reel-mixer/02_MVP_SCOPE.md`
- `workflow-runs/0003-video-mix-reel-mixer/03_ARCHITECTURE_PLAN.md`
- `workflow-runs/0003-video-mix-reel-mixer/04_DATA_MODEL_AND_PACK_SCHEMA.md`
- `workflow-runs/0003-video-mix-reel-mixer/05_REVIEW_RULES.md`
- `workflow-runs/0003-video-mix-reel-mixer/06_ROADMAP.md`
- `workflow-runs/0003-video-mix-reel-mixer/07_FUTURE_HANDOFF.md`
- `workflow-runs/0003-video-mix-reel-mixer/13_STAGE_1_CODEX_EXECUTION_TASK.md`
- `workflow-runs/0003-video-mix-reel-mixer/14_STAGE_1_EXECUTION_REPORT.md`
- `workflow-runs/0003-video-mix-reel-mixer/16_REVIEW_UX_TASK.md`
- `workflow-runs/0003-video-mix-reel-mixer/17_REVIEW_UX_EXECUTION_REPORT.md`
- `workflow-runs/0003-video-mix-reel-mixer/19_REVIEW_THUMBNAILS_EXECUTION_REPORT.md`
- `workflow-runs/0003-video-mix-reel-mixer/21_DASHBOARD_MVP_EXECUTION_REPORT.md`
- `workflow-runs/0003-video-mix-reel-mixer/22_DASHBOARD_LAUNCHER_EXECUTION_REPORT.md`
- `workflow-runs/0003-video-mix-reel-mixer/23_DASHBOARD_REVIEW_CONTROLS_EXECUTION_REPORT.md`
- `workflow-runs/0003-video-mix-reel-mixer/24_RUSSIAN_DASHBOARD_UI_EXECUTION_REPORT.md`
- `workflow-runs/0003-video-mix-reel-mixer/25_SIMPLIFIED_SOURCE_TO_MP4_MVP_EXECUTION_REPORT.md`

## Completed Previous Work

`Animated Subtitle Video Maker` Phase 1 MVP is accepted after owner visual review.

## Future Captured Module — Video Content Analyzer

Research only. Implementation is not authorized.

## Canonical Next Action

Review draft PR `#71`, run the stable Quick Downloader installer/updater on the owner's Windows machine using Issue `#70`, then test the one-click flow from Issue `#69`.

## Canonical State Rule

If there is conflict between conversation and repository, use:

1. `PROJECT_STATE.md`;
2. active workflow run;
3. GitHub Issue/PR thread;
4. `logs/PROJECT_LOG.md`.
