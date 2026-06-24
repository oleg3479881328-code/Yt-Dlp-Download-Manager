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
- stabilization status: PR `#4` (`Stabilize dashboard safety before Phase 2`) was merged on 2026-06-24 before any Phase 2 work
- captured future decision: preserve the analyzed video-intelligence donor pattern here as future `Video Content Analyzer`; do not develop a separate parallel video-analysis product

## Required Read Order

1. `PROJECT_STATE.md` — текущее подтверждённое состояние и следующий шаг.
2. `PROJECT_RULES.md` — ограничения и правила работы.
3. `logs/PROJECT_LOG.md` — хронология решений и изменений.
4. Latest accepted module workflow material: `workflow-runs/0002-animated-subtitle-module/` and GitHub Issue `#1`.
5. Latest stabilization evidence before Phase 2: merged PR `#4`, GitHub Issue `#5`, and GitHub Issue `#6`.
6. Future video-analysis research: `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md`.

## Verified Current Components

- `app/` — FastAPI web dashboard (локальная веб-панель), SQLite state (хранилище состояния), background download worker (фоновый обработчик загрузок).
- `chrome_extension/` — standalone Chrome extension (отдельное расширение Chrome).
- `native_host/` — native messaging host (локальный мост между расширением и Windows-инструментами).
- optional transcription (опциональная транскрибация) through `faster-whisper` into `.srt` and `.txt`.
- `subtitle_studio/` — isolated Remotion implementation (изолированная реализация на Remotion) of the animated subtitle Phase 1 MVP; code exists, validated, and **accepted after owner visual review**.
- merged PR `#4` hardens the pre-Phase-2 runtime with dashboard path safety, escaped external metadata rendering, fixed audio final output path handling, bounded native-host upload limits, and green safety CI.

## Active Work — Animated Subtitle Video Maker

`Animated Subtitle Video Maker` (модуль создания роликов с анимированными субтитрами) Phase 1 MVP:

- input (вход): собственное видео пользователя;
- timed caption input (вход временных меток субтитров): prepared word-level timing (подготовленные временные метки отдельных слов);
- one karaoke preset (один караоке-пресет);
- preview (предпросмотр);
- export (экспорт) готового MP4 с вшитыми анимированными субтитрами.

Implementation state (статус реализации): **accepted after owner visual review**. Phase 1 MVP завершён. Финальный артефакт: `subtitle_studio/out/karaoke-preview-v5.mp4` (255 frames, 805.8 kB).

Следующий шаг: либо отдельная full browser-driven Chrome extension/native-host end-to-end validation (полная сквозная проверка через браузер) для снятия остаточного runtime риска, либо только Phase 2A planning (планирование Phase 2A) после отдельного решения владельца.

## Future Captured Module — Video Content Analyzer

Research only; implementation is not authorized yet.

Captured direction:

- analyze downloaded or local videos using timestamped transcript plus selected visual frames;
- first valuable use case: analysis of competitor short-form videos for hook (крючок внимания), on-screen text, visual structure, product timing and CTA (призыв к действию);
- primary donor pattern: `bradautomates/claude-video`;
- secondary donor ideas: `jordanrendric/claude-video-vision`;
- later ideas only: `thoughtpunch/claudetube`;
- separate parallel video-analysis development is unnecessary after the captured research is retained here.

## Canonical Next Action

PR `#4` merged and the stabilization pass before Phase 2 is complete.

Next safe action:

- if the owner wants to reduce residual runtime risk first, run a full browser-driven Chrome extension/native-host end-to-end validation and report it;
- otherwise do only Phase 2A planning after separate owner approval.

Do not start Phase 2 implementation yet. Do not start `Video Content Analyzer` without separate owner approval.

## Canonical State Rule

При конфликте между разговором и репозиторием источником истины являются `PROJECT_STATE.md`, активный workflow run (цикл работы), GitHub Issue/PR thread (ветка GitHub Issue/PR) для текущего исполнения и `logs/PROJECT_LOG.md`.
