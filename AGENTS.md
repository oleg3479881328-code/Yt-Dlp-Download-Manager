# AGENTS.md

## Purpose

This repository is prepared for AI handoff directly from the folder or GitHub repository without extra chat context.

If you are an AI coding agent, start from the repository itself and follow the read order below before making changes.

## Required Read Order

1. `PROJECT_ENTRYPOINT.md`
2. `PROJECT_STATE.md`
3. `PROJECT_RULES.md`
4. `logs/PROJECT_LOG.md`
5. `workflow-runs/0003-video-mix-reel-mixer/`
6. `workflow-runs/0002-animated-subtitle-module/` only if subtitle/rendering context is needed.

## Canonical Current Task

Current priority:

- `VIDEO MIX` planning is active.
- `VIDEO MIX` is a future scalable Reel Mixer Engine inside this repository.
- Wedding photographer content is only the first pilot industry pack.
- The architecture must separate reusable core logic from industry packs.
- Implementation is not authorized yet; planning and handoff preparation are current.

Previous state:

- `Animated Subtitle Video Maker` Phase 1 MVP is accepted.
- Phase 2 transcription integration is not started.

Do not begin `Video Content Analyzer` implementation unless separately authorized.

## State Rules

- Repository files are the source of truth.
- Follow `PROJECT_STATE.md`, active workflow artifacts, Issue/PR thread, and `logs/PROJECT_LOG.md`.
- Do not claim something works unless validated by execution.

## Scope Rules

- Keep this as a personal local Windows tool.
- Do not turn it into a public product.
- Do not refactor unrelated downloader, extension, or native-host code unless required.
- Do not store raw media, derived clips, local databases, private logs, or rendered exports in GitHub.
- Keep `VIDEO MIX` core industry-neutral.

## Practical Start Rule

If you were given only the repository folder, begin with `PROJECT_ENTRYPOINT.md` and derive the current task from repository state.
