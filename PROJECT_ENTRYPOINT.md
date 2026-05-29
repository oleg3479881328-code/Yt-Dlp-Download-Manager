# PROJECT ENTRYPOINT — yt-dlp Download Manager

## Project Goal

Личный локальный Windows-инструмент для полного цикла работы с роликами:

- скачивание медиа через `yt-dlp`;
- управление загрузками из web dashboard (веб-панели) и Chrome extension (расширения Chrome);
- получение или создание субтитров и текста в `SRT + TXT`;
- создание собственных роликов с burned-in animated subtitles (вшитыми анимированными субтитрами), включая karaoke highlighting (караоке-подсветку слов), стили, анимации и позиционирование;
- future candidate module (будущий кандидат-модуль): `Video Content Analyzer` (модуль анализа содержания видео) для анализа роликов через транскрипт с таймкодами и выбранные кадры.

## Project Mode

- mode: `compact`
- use case: personal local tool only
- repository: private dedicated GitHub repository; this is the only primary video project
- normalization status: existing project normalized into Project Execution OS on 2026-05-25
- active scope decision: add `Animated Subtitle Video Maker` (модуль создания роликов с анимированными субтитрами) inside this repository
- captured future decision: preserve the analyzed video-intelligence donor pattern here as future `Video Content Analyzer`; do not develop `Video-Combine-Analyzer` as a parallel primary product

## Required Read Order

1. `PROJECT_STATE.md` — текущее подтверждённое состояние и следующий шаг.
2. `PROJECT_RULES.md` — ограничения и правила работы.
3. `logs/PROJECT_LOG.md` — хронология решений и изменений.
4. Latest active workflow material: `workflow-runs/0002-animated-subtitle-module/` and GitHub Issue `#1`.
5. Future video-analysis research: `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md`.

## Verified Current Components

- `app/` — FastAPI web dashboard (локальная веб-панель), SQLite state (хранилище состояния), background download worker (фоновый обработчик загрузок).
- `chrome_extension/` — standalone Chrome extension (отдельное расширение Chrome).
- `native_host/` — native messaging host (локальный мост между расширением и Windows-инструментами).
- optional transcription (опциональная транскрибация) through `faster-whisper` into `.srt` and `.txt`.
- `subtitle_studio/` — isolated Remotion implementation (изолированная реализация на Remotion) of the animated subtitle Phase 1 MVP; code exists but current review has not accepted it.

## Active Work — Animated Subtitle Video Maker

`Animated Subtitle Video Maker` (модуль создания роликов с анимированными субтитрами) Phase 1 MVP:

- input (вход): собственное видео пользователя;
- timed caption input (вход временных меток субтитров): prepared word-level timing (подготовленные временные метки отдельных слов);
- one karaoke preset (один караоке-пресет);
- preview (предпросмотр);
- export (экспорт) готового MP4 с вшитыми анимированными субтитрами.

Implementation state (статус реализации): code present, but `changes requested` (запрошены изменения). Active blockers are recorded in `PROJECT_STATE.md` and GitHub Issue `#1`, including fixed 8-second duration and missing required execution-report evidence.

## Future Captured Module — Video Content Analyzer

Research only; implementation is not authorized yet.

Captured direction:

- analyze downloaded or local videos using timestamped transcript plus selected visual frames;
- first valuable use case: analysis of competitor short-form videos for hook (крючок внимания), on-screen text, visual structure, product timing and CTA (призыв к действию);
- primary donor pattern: `bradautomates/claude-video`;
- secondary donor ideas: `jordanrendric/claude-video-vision`;
- later ideas only: `thoughtpunch/claudetube`;
- separate `Video-Combine-Analyzer` development is unnecessary after the captured research is retained here.

## Canonical Next Action

Codex must fix the outstanding Phase 1 review blockers in GitHub Issue `#1`, validate an MP4 render with content longer than 8 seconds, and return the required structured `EXECUTION REPORT` (отчёт о выполнении). Do not begin `Video Content Analyzer` implementation before that MVP is accepted and a separate owner decision authorizes the next task.

## Canonical State Rule

При конфликте между разговором и репозиторием источником истины являются `PROJECT_STATE.md`, активный workflow run (цикл работы), GitHub Issue/PR thread (ветка GitHub Issue/PR) для текущего исполнения и `logs/PROJECT_LOG.md`.