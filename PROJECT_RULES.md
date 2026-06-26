# PROJECT RULES — yt-dlp Download Manager

## Scope

This project is Oleg's personal local Windows tool for:

- downloading media through `yt-dlp`;
- managing downloads through a web dashboard;
- launching downloads through Chrome extension/native host;
- local transcription into `.srt` and `.txt`;
- creating videos with burned-in animated subtitles;
- planning `VIDEO MIX`, a scalable Reel Mixer Engine for batch Reels from local media.

Do not treat the project as a public product unless the owner separately decides that.

## Operating Mode

- Project Execution OS mode: `compact`.
- Repository is the durable source of truth.
- Current state lives in `PROJECT_STATE.md`.
- Historical sequence lives in `logs/PROJECT_LOG.md`.
- Active workflow lives in `workflow-runs/0003-video-mix-reel-mixer/`.
- Each substantial change should leave one concrete next action.

## State Separation Rules

Always distinguish:

- proposed state — discussed but not recorded or tested;
- committed state — recorded in the repository;
- validated state — confirmed by real run or test;
- reviewed state — evaluated as accepted, warning or blocked.

Do not claim that download, transcription, rendering, VIDEO MIX generation or export works unless validated by execution.

## Current Architecture Rules

1. Web dashboard and Chrome extension/native host remain allowed as separate runtime contours for personal use.
2. Do not unify or rewrite existing runtime contours without a separate task.
3. `Animated Subtitle Video Maker` is accepted after Phase 1 MVP.
4. `Video Content Analyzer` remains research-only until separately authorized.
5. `VIDEO MIX` is planned as a module inside this repository.
6. `VIDEO MIX` must separate reusable core logic from industry packs.
7. Wedding photographer is the first pilot pack only; do not hardcode wedding assumptions into the core.
8. Source media, derived clips, local databases and rendered exports must stay out of GitHub.

## VIDEO MIX Planning Boundary

Current active task is planning only.

Allowed now:

- owner brief;
- MVP scope;
- architecture plan;
- data model;
- pack schema;
- review/scoring rules;
- roadmap;
- future implementation handoff boundary.

Not allowed until owner approval:

- code implementation;
- local execution claims;
- UI implementation;
- ffmpeg/ffprobe integration work;
- adding new industry packs beyond the pilot;
- unrelated refactors.

## Quality Rules

1. MVP-first.
2. One verifiable step at a time.
3. Any suspected bug must be marked as suspected until validated.
4. After implementation, run the scenario that proves the result.
5. Do not store user media, generated clips, exports, local database, build outputs or virtual environment in GitHub.
6. Batch generation must still include a human review gate before final export.

## Local Safety Rules

- Keep local app behavior on loopback unless separately changed.
- Do not publish local paths, private URLs, user media, rendered videos or local database contents.
- Check native-host changes carefully because it can interact with local files and programs.

## Current Next Action

Review `workflow-runs/0003-video-mix-reel-mixer/`. If approved, open a narrow Stage 1 implementation task for Codex/local coding agent.
