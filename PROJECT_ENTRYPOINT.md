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
- active run: `workflow-runs/0003-video-mix-reel-mixer/`

## Required Read Order

1. `PROJECT_STATE.md`
2. `PROJECT_RULES.md`
3. `logs/PROJECT_LOG.md`
4. `workflow-runs/0003-video-mix-reel-mixer/`
5. `workflow-runs/0003-video-mix-reel-mixer/22_DASHBOARD_LAUNCHER_EXECUTION_REPORT.md`
6. GitHub Issue `#34`
7. `workflow-runs/0002-animated-subtitle-module/` only if subtitle/rendering context is needed.
8. `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md` only if needed.

## Verified Current Components

- `app/` — FastAPI web dashboard, SQLite state and download worker.
- `chrome_extension/` — standalone Chrome extension.
- `native_host/` — native messaging host.
- local transcription through `faster-whisper`.
- `subtitle_studio/` — accepted Remotion Phase 1 MVP.
- `video_mix/` — local Stage 1 VIDEO MIX implementation with review thumbnails.
- `app/video_mix_dashboard.py` + `/video-mix` — local dashboard MVP for VIDEO MIX review.
- `start_video_mix_dashboard.ps1` — one-click Windows launcher for VIDEO MIX dashboard.
- `workflow-runs/0003-video-mix-reel-mixer/` — active VIDEO MIX planning and execution package.

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

## Completed Previous Work

`Animated Subtitle Video Maker` Phase 1 MVP is accepted after owner visual review.

## Future Captured Module — Video Content Analyzer

Research only. Implementation is not authorized.

## Canonical Next Action

Review the Stage 1.4 one-click dashboard launcher through GitHub Issue `#34`, the linked PR and `22_DASHBOARD_LAUNCHER_EXECUTION_REPORT.md`.

If accepted, keep `.\start_video_mix_dashboard.ps1` as the owner-facing entrypoint for the local dashboard and choose the next narrow follow-up only.

## Canonical State Rule

If there is conflict between conversation and repository, use:

1. `PROJECT_STATE.md`;
2. active workflow run;
3. GitHub Issue/PR thread;
4. `logs/PROJECT_LOG.md`.
