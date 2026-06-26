---
status: in-progress
project_mode: compact
current_step: 10_VIDEO_MIX_DRAFT_CODE_PREPARED
current_run: workflow-runs/0003-video-mix-reel-mixer/
last_updated: 2026-06-26
next_action: Review VIDEO MIX planning and draft-code package, then decide whether to authorize Stage 1 implementation.
---

# PROJECT STATE — yt-dlp Download Manager

## Current Phase

The project remains the primary local Windows video tool.

`Animated Subtitle Video Maker` Phase 1 MVP was completed and accepted after owner visual review.

New active direction:

- `VIDEO MIX` / `Reel Mixer Engine`;
- module inside this repository;
- scalable batch Reel generation from local user media;
- first pilot industry pack: wedding photographer;
- future design must support other industries through industry packs.

## Current Focus

Assistant has completed planning and created draft code under the active workflow run.

Codex should receive only future implementation/local execution work after owner approval.

## Confirmed Existing State

- `app/` — FastAPI web dashboard, SQLite state and download worker.
- `chrome_extension/` — standalone Chrome extension.
- `native_host/` — native messaging host.
- local transcription exists through `faster-whisper` into `.srt` and `.txt`.
- `subtitle_studio/` exists as accepted Remotion MVP for animated subtitles.
- `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md` stores future video-analysis research only.
- `workflow-runs/0003-video-mix-reel-mixer/` stores active VIDEO MIX planning artifacts and draft code.

## Confirmed Decisions

1. The project is a personal local Windows tool.
2. The repository remains the durable source of truth.
3. `Yt-Dlp-Download-Manager` remains the only primary video project.
4. `Animated Subtitle Video Maker` Phase 1 is accepted.
5. Phase 2 transcription integration is not started.
6. `Video Content Analyzer` remains research-only until separately authorized.
7. `VIDEO MIX` belongs inside this repository, not as a separate product.
8. Wedding photographer is the first pilot vertical only.
9. `VIDEO MIX` must be a reusable Reel Mixer Engine with industry packs.
10. Source media, derived clips, local databases and rendered exports must not be committed.
11. Draft code is reference material only; it is not integrated or validated.

## VIDEO MIX Planning Model

```text
VIDEO MIX
├── Reel Mixer Core
│   └── industry-neutral asset, clip, candidate, review and export engine
└── Industry Packs
    └── vertical-specific tags, templates, scoring and overlay rules
```

First MVP target:

```text
local media folder
→ asset scan
→ micro-clip extraction
→ basic scoring
→ wedding pilot pack templates
→ candidate Reels
→ preview/review
→ approved MP4 exports
```

## Active Workflow Run

`workflow-runs/0003-video-mix-reel-mixer/`

Created planning artifacts:

- `01_OWNER_BRIEF.md`
- `02_MVP_SCOPE.md`
- `03_ARCHITECTURE_PLAN.md`
- `04_DATA_MODEL_AND_PACK_SCHEMA.md`
- `05_REVIEW_RULES.md`
- `06_ROADMAP.md`
- `07_FUTURE_HANDOFF.md`
- `08_PLANNING_REPORT.md`
- `09_DRAFT_CODE_REPORT.md`

Draft code folder:

- `workflow-runs/0003-video-mix-reel-mixer/draft-code/`

Coordination issue:

- GitHub Issue `#20` — `VIDEO MIX — scalable reels mixer engine with wedding photographer pilot`

## Current Boundaries

Do not treat the draft code as validated implementation.

Do not build:

- public product work;
- posting automation;
- GPU-generation dependency;
- full editor timeline;
- industry marketplace;
- unrelated downloader/runtime refactor.

## Current Next Action

Review the planning and draft-code package. If approved, open a narrow Stage 1 implementation task for Codex/local coding agent.
