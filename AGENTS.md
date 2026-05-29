# AGENTS.md

## Purpose

This repository is prepared for AI handoff (передачи ИИ) directly from the folder or GitHub repository without extra chat context.

If you are an AI coding agent, start from the repository itself and follow the read order below before making changes.

## Required Read Order

1. `PROJECT_ENTRYPOINT.md`
2. `PROJECT_STATE.md`
3. `PROJECT_RULES.md`
4. `logs/PROJECT_LOG.md`
5. Active workflow materials under `workflow-runs/0002-animated-subtitle-module/`

## Canonical Current Task

Current priority:

- fix the blocked `subtitle_studio` Phase 1 MVP review issues;
- validate an MP4 render with content longer than 8 seconds;
- return the required `EXECUTION REPORT` (отчёт о выполнении).

Do not begin `Video Content Analyzer` implementation. That future module is research-only and not approved for execution.

## State Rules

- Treat repository files as the source of truth (источник истины).
- If conversation context conflicts with repository state, follow `PROJECT_STATE.md`, active workflow artifacts, GitHub Issue or PR thread for the active task, and `logs/PROJECT_LOG.md`.
- Do not claim something works unless it was actually validated by execution.

## Scope Rules

- Keep the project as a personal local Windows tool.
- Do not turn it into a public product or Chrome Web Store extension.
- Do not expand `subtitle_studio` beyond the approved Phase 1 MVP before the current review blockers are closed.
- Do not refactor unrelated downloader, extension, or native-host code unless the active task requires it.

## Practical Start Rule

If you were given only the repository folder, begin with `PROJECT_ENTRYPOINT.md` and derive the current task from there rather than from chat memory or guesses.
