# AGENTS.md

## Purpose

This repository is prepared for AI handoff (передачи ИИ) directly from the folder or GitHub repository without extra chat context.

If you are an AI coding agent, start from the repository itself and follow the read order below before making changes.

## Required Read Order

1. `PROJECT_ENTRYPOINT.md`
2. `PROJECT_STATE.md`
3. `PROJECT_RULES.md`
4. `logs/PROJECT_LOG.md`
5. `whiteboard_studio/README.md`
6. GitHub Issue `#16 Implement Phase 1 Whiteboard Renderer MVP`

## Canonical Current Task

Current priority:

- `subtitle_studio` Phase 1 remains **accepted** after owner visual review.
- Owner decision from 2026-06-25 authorizes a bounded `whiteboard_studio` MVP inside this repository.
- Current task is local validation and owner review of the rendered whiteboard sample MP4 from Issue `#16`.

Do not begin `Video Content Analyzer` implementation. That future module is research-only and not approved for execution.

## State Rules

- Treat repository files as the source of truth (источник истины).
- If conversation context conflicts with repository state, follow `PROJECT_STATE.md`, active workflow artifacts, GitHub Issue or PR thread for the active task, and `logs/PROJECT_LOG.md`.
- Do not claim something works unless it was actually validated by execution.

## Scope Rules

- Keep the project as a personal local Windows tool.
- Do not turn it into a public product or Chrome Web Store extension.
- Keep `whiteboard_studio/` isolated from downloader, extension, native host, and accepted `subtitle_studio`.
- Do not refactor unrelated downloader, extension, or native-host code unless the active task requires it.

## Practical Start Rule

If you were given only the repository folder, begin with `PROJECT_ENTRYPOINT.md` and derive the current task from there rather than from chat memory or guesses.
