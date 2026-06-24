# PROJECT ENTRYPOINT — yt-dlp Download Manager

## Project Goal

Личный локальный Windows-инструмент для полного цикла работы с роликами:

- скачивание медиа через `yt-dlp`;
- управление загрузками из web dashboard и Chrome extension;
- получение или создание субтитров и текста в `SRT + TXT`;
- создание собственных роликов с burned-in animated subtitles, включая karaoke highlighting, стили, анимации и позиционирование;
- rights-aware science video assembly MVP: script -> visual beats -> stock source candidates -> manual approval -> timeline/source ledger;
- future candidate module: `Video Content Analyzer` для анализа локальных или разрешённых видео через транскрипт с таймкодами и выбранные кадры.

## Project Mode

- mode: `compact`
- use case: personal local tool only
- repository: dedicated GitHub repository; this is the only primary video project
- normalization status: existing project normalized into Project Execution OS on 2026-05-25
- accepted scope: `Animated Subtitle Video Maker` inside this repository
- active owner decision from 2026-06-20: bounded `Science Video Assembly MVP` draft track is authorized inside this repository through PR `#3`
- captured future decision: preserve video-intelligence donor patterns here as future `Video Content Analyzer`; do not develop a separate parallel product

## Required Read Order

1. `PROJECT_STATE.md` — текущее подтверждённое состояние и следующий шаг.
2. `PROJECT_RULES.md` — ограничения и правила работы.
3. `logs/PROJECT_LOG.md` — хронология решений и изменений.
4. Active PR `#3 EXECUTOR PACKET: Science Video Assembly MVP`.
5. Active workflow materials: `workflow-runs/0003-science-video-assembly-mvp/`.
6. Existing accepted module context: `workflow-runs/0002-animated-subtitle-module/`.
7. Future video-analysis research: `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md`.

## Verified Current Components

- `app/` — FastAPI web dashboard, SQLite state, background download worker.
- `chrome_extension/` — standalone Chrome extension.
- `native_host/` — native messaging host between extension and Windows tool.
- optional transcription through `faster-whisper` into `.srt` and `.txt`.
- `subtitle_studio/` — isolated Remotion implementation of animated subtitle Phase 1 MVP; code exists, validated, and accepted after owner visual review.
- `science_assembly/` — draft scaffold in PR `#3`; not accepted until validation and execution report.

## Accepted Work — Animated Subtitle Video Maker

Phase 1 MVP is accepted after owner visual review. Final artifact: `subtitle_studio/out/karaoke-preview-v5.mp4`.

Phase 2 transcription integration remains planned but is not active while PR `#3` is under review.

## Active Work — Science Video Assembly MVP

Research/planning/code scaffold exists in PR `#3`.

Current objective:

```text
short script
-> DeepSeek visual beats JSON
-> stock source candidates
-> DeepSeek candidate ranking JSON
-> manual approval file
-> timeline JSON
-> source ledger JSON
```

This is a rights-aware stock/source-ledger workflow, not a YouTube scraping or republishing tool.

## Future Captured Module — Video Content Analyzer

Research only unless separately authorized. Captured direction:

- analyze downloaded or local videos using timestamped transcript plus selected visual frames;
- first valuable use case: competitor short-form video analysis;
- primary donor pattern: `bradautomates/claude-video`;
- secondary donor ideas: `jordanrendric/claude-video-vision`;
- later ideas only: `thoughtpunch/claudetube`.

## Canonical Next Action

Resolve PR `#3` review blockers, run offline smoke test and pytest, return execution report. Do not start automatic YouTube publication downloading. After PR `#3` is accepted or closed, return to Phase 2 transcription planning.

## Canonical State Rule

При конфликте между разговором и репозиторием источником истины являются `PROJECT_STATE.md`, active workflow run, active GitHub Issue/PR thread and `logs/PROJECT_LOG.md`.
