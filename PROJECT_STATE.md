---
status: in-progress
project_mode: compact
current_step: 11_VIDEO_MIX_DEEP_DONOR_RESEARCH_DONE
current_run: workflow-runs/0003-video-mix-reel-mixer/
last_updated: 2026-06-26
next_action: Review deep donor research, then revise draft code before any Stage 1 implementation approval.
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

Assistant has completed planning, created draft code, and added deep donor research for VIDEO MIX as a general production combiner.

Codex should receive only future implementation/local execution work after owner approval.

## Confirmed Existing State

- `app/` — FastAPI web dashboard, SQLite state and download worker.
- `chrome_extension/` — standalone Chrome extension.
- `native_host/` — native messaging host.
- local transcription exists through `faster-whisper` into `.srt` and `.txt`.
- `subtitle_studio/` exists as accepted Remotion MVP for animated subtitles.
- `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md` stores future video-analysis research only.
- `workflow-runs/0003-video-mix-reel-mixer/` stores active VIDEO MIX planning artifacts, draft code and donor research.

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
12. Donor research shows VIDEO MIX should be a layered production engine, not a clone of any single SaaS product.

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
→ pilot pack templates
→ candidate Reels
→ preview/review
→ approved MP4 exports
```

## Deep Donor Research Result

Deep donor research is stored at:

- `workflow-runs/0003-video-mix-reel-mixer/11_DEEP_DONOR_RESEARCH_PRODUCTION_ENGINE.md`

Recommended stack:

- Stage 1: `ffprobe + ffmpeg + Python orchestration + candidate manifests + review gate`.
- Stage 1.5: PySceneDetect, perceptual hashing, OpenCV quality scoring.
- Stage 2: Remotion for branded templates and overlays.
- Stage 3: optional CLIP/OpenCLIP or YOLO-style visual intelligence after licensing and performance review.
- SaaS donors such as OpusClip, quso.ai, Klap, Munch, Creatomate, Shotstack and JSON2Video are product/architecture references, not first local dependencies.

## Active Workflow Run

`workflow-runs/0003-video-mix-reel-mixer/`

Created artifacts:

- `01_OWNER_BRIEF.md`
- `02_MVP_SCOPE.md`
- `03_ARCHITECTURE_PLAN.md`
- `04_DATA_MODEL_AND_PACK_SCHEMA.md`
- `05_REVIEW_RULES.md`
- `06_ROADMAP.md`
- `07_FUTURE_HANDOFF.md`
- `08_PLANNING_REPORT.md`
- `09_DRAFT_CODE_REPORT.md`
- `10_DONOR_RESEARCH.md`
- `11_DEEP_DONOR_RESEARCH_PRODUCTION_ENGINE.md`

Draft code folder:

- `workflow-runs/0003-video-mix-reel-mixer/draft-code/`

Coordination issue:

- GitHub Issue `#20` — `VIDEO MIX — scalable reels mixer engine with wedding photographer pilot`

## Current Boundaries

Do not treat the draft code as validated implementation.

Do not approve Stage 1 before reviewing the donor research and revising the draft code to reflect the donor decisions.

Do not build:

- public product work;
- posting automation;
- GPU-generation dependency;
- full editor timeline;
- industry marketplace;
- unrelated downloader/runtime refactor.

## Current Next Action

Review deep donor research, then revise the draft code/handoff so Codex receives a better Stage 1 task.
