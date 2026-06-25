# PROJECT ENTRYPOINT — yt-dlp Download Manager

## Project Goal

Личный локальный Windows-инструмент для полного цикла работы с роликами:

- скачивание медиа через `yt-dlp`;
- управление загрузками из web dashboard (веб-панели) и Chrome extension (расширения Chrome);
- получение или создание субтитров и текста в `SRT + TXT`;
- создание собственных роликов с burned-in animated subtitles (вшитыми анимированными субтитрами), включая karaoke highlighting (караоке-подсветку слов), стили, анимации и позиционирование;
- создание коротких whiteboard-style explainer videos (роликов-объяснялок в стиле рисованной доски) из JSON scene spec (спецификации сцен в JSON);
- future candidate module (будущий кандидат-модуль): `Video Content Analyzer` (модуль анализа содержания видео) для анализа роликов через транскрипт с таймкодами и выбранные кадры.

## Project Mode

- mode: `compact`
- use case: personal local tool only
- repository: private dedicated GitHub repository; this is the only primary video project
- normalization status: existing project normalized into Project Execution OS on 2026-05-25
- accepted scope: `Animated Subtitle Video Maker` inside this repository
- active owner decision from 2026-06-25: bounded `Whiteboard Renderer MVP` is authorized inside this repository through Issue `#16`
- captured future decision: preserve the analyzed video-intelligence donor pattern here as future `Video Content Analyzer`; do not develop a separate parallel video-analysis product

## Required Read Order

1. `PROJECT_STATE.md` — текущее подтверждённое состояние и следующий шаг.
2. `PROJECT_RULES.md` — ограничения и правила работы.
3. `logs/PROJECT_LOG.md` — хронология решений и изменений.
4. `whiteboard_studio/README.md` and active GitHub Issue `#16`.
5. Existing accepted module context: `workflow-runs/0002-animated-subtitle-module/` and GitHub Issue `#1`.
6. Future video-analysis research: `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md`.

## Verified Current Components

- `app/` — FastAPI web dashboard (локальная веб-панель), SQLite state (хранилище состояния), background download worker (фоновый обработчик загрузок).
- `chrome_extension/` — standalone Chrome extension (отдельное расширение Chrome).
- `native_host/` — native messaging host (локальный мост между расширением и Windows-инструментами).
- optional transcription (опциональная транскрибация) through `faster-whisper` into `.srt` and `.txt`.
- `subtitle_studio/` — isolated Remotion implementation (изолированная реализация на Remotion) of the animated subtitle Phase 1 MVP; code exists, validated, and **accepted after owner visual review**.
- `whiteboard_studio/` — isolated Remotion implementation of the Whiteboard Renderer Phase 1 MVP; local sample render exists and awaits owner visual review.

## Accepted Work — Animated Subtitle Video Maker

`Animated Subtitle Video Maker` (модуль создания роликов с анимированными субтитрами) Phase 1 MVP:

- input (вход): собственное видео пользователя;
- timed caption input (вход временных меток субтитров): prepared word-level timing (подготовленные временные метки отдельных слов);
- one karaoke preset (один караоке-пресет);
- preview (предпросмотр);
- export (экспорт) готового MP4 с вшитыми анимированными субтитрами.

Implementation state (статус реализации): **accepted after owner visual review**. Phase 1 MVP завершён. Финальный артефакт: `subtitle_studio/out/karaoke-preview-v5.mp4` (255 frames, 805.8 kB).

Phase 2 transcription integration remains planned, but it is not the active task while `whiteboard_studio` review is pending.

## Active Work — Whiteboard Renderer MVP

Owner decision from 2026-06-25 authorizes a bounded whiteboard-style renderer inside this repository.

Current objective:

```text
JSON scene spec
-> Remotion whiteboard/sketch animation
-> local preview
-> local vertical MP4 render
```

This is a local render proof, not GUI automation, not a SaaS editor, and not a dashboard integration.

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

Project is now ready for owner review of `whiteboard_studio`.

New executor should enter through Issue `#16`, verify the existing sample render in `whiteboard_studio/out/sky-blue-demo.mp4`, and then either:

- accept the bounded MVP as-is after visual review;
- or request small isolated follow-up polish inside `whiteboard_studio/`.

## Canonical State Rule

При конфликте между разговором и репозиторием источником истины являются `PROJECT_STATE.md`, активный workflow run (цикл работы), GitHub Issue/PR thread (ветка GitHub Issue/PR) для текущего исполнения и `logs/PROJECT_LOG.md`.
