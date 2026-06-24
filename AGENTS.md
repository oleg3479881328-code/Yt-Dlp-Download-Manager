# AGENTS.md

## Purpose

This repository is prepared for AI handoff directly from the folder or GitHub repository without extra chat context.

If you are an AI coding agent, start from the repository itself and follow the read order below before making changes.

## Required Read Order

1. `PROJECT_ENTRYPOINT.md`
2. `PROJECT_STATE.md`
3. `PROJECT_RULES.md`
4. `logs/PROJECT_LOG.md`
5. Active workflow materials under `workflow-runs/0003-science-video-assembly-mvp/`
6. Active executor PR `#3 EXECUTOR PACKET: Science Video Assembly MVP`

## Canonical Current Task

Current priority:

- Phase 1 Animated Subtitle Video Maker MVP is accepted after owner visual review.
- Owner decision on 2026-06-20 authorizes a bounded draft / MVP track for `Science Video Assembly MVP` inside this repository.
- Active work is PR `#3`: validate and harden the isolated `science_assembly/` scaffold.
- Phase 2 transcription integration remains planned but not the active task while PR `#3` is open.

Do not implement automatic YouTube downloading for publication. Do not treat `science_assembly/` as a full `Video Content Analyzer`; it is a rights-aware script-to-stock-B-roll assembly MVP.

## State Rules

- Treat repository files as the source of truth.
- If conversation context conflicts with repository state, follow `PROJECT_STATE.md`, active workflow artifacts, GitHub Issue or PR thread for the active task, and `logs/PROJECT_LOG.md`.
- Do not claim something works unless it was actually validated by execution.

## Scope Rules

- Keep the project as a personal local Windows tool.
- Do not turn it into a public product or Chrome Web Store extension.
- Do not refactor unrelated downloader, extension, native-host, or `subtitle_studio` code unless the active task requires it.
- Keep `science_assembly/` isolated until validated and accepted.

## Practical Start Rule

If you were given only the repository folder, begin with `PROJECT_ENTRYPOINT.md` and derive the current task from there rather than from chat memory or guesses.
