# PROJECT ENTRYPOINT — yt-dlp Download Manager

## Project Goal

Личный локальный Windows-инструмент для полного цикла работы с роликами:

- скачивание медиа через `yt-dlp`;
- управление загрузками из web dashboard (веб-панели) и Chrome extension (расширения Chrome);
- получение или создание субтитров и текста в `SRT + TXT`;
- создание собственных роликов с burned-in animated subtitles (вшитыми анимированными субтитрами), включая karaoke highlighting (караоке-подсветку слов), стили, анимации и позиционирование.

## Project Mode

- mode: `compact`
- use case: personal local tool only
- repository: private dedicated GitHub repository
- normalization status: existing project normalized into Project Execution OS on 2026-05-25
- active scope decision: add `Animated Subtitle Video Maker` (модуль создания роликов с анимированными субтитрами) inside this repository

## Required Read Order

1. `PROJECT_STATE.md` — текущее подтверждённое состояние и следующий шаг.
2. `PROJECT_RULES.md` — ограничения и правила работы.
3. `logs/PROJECT_LOG.md` — хронология решений и изменений.
4. Latest workflow run: `workflow-runs/0002-animated-subtitle-module/07_RESULT.md`.

## Verified Current Components

- `app/` — FastAPI web dashboard (локальная веб-панель), SQLite state (хранилище состояния), background download worker (фоновый обработчик загрузок).
- `chrome_extension/` — standalone Chrome extension (отдельное расширение Chrome).
- `native_host/` — native messaging host (локальный мост между расширением и Windows-инструментами).
- optional transcription (опциональная транскрибация) through `faster-whisper` into `.srt` and `.txt`.

## Approved Not Yet Implemented Module

`Animated Subtitle Video Maker` (модуль создания роликов с анимированными субтитрами):

- input (вход): собственное видео пользователя;
- subtitle source (источник субтитров): готовые субтитры, загруженный текст или локальное распознавание речи;
- word-level timing (временные метки отдельных слов) for karaoke highlighting (для караоке-подсветки);
- configurable styling (настраиваемое оформление): цвет, подсветка, анимация появления, последовательность слов, позиция на экране;
- preview (предпросмотр) before export (перед экспортом);
- export (экспорт) готового MP4 с вшитыми анимированными субтитрами.

Planned technology direction (планируемое технологическое направление): `Remotion` + `@remotion/captions` for rendering and preview (для отрисовки и предпросмотра), `stable-ts` / `faster-whisper` for word-level timing (для временных меток слов), `yt-dlp` for available source subtitles (для получения существующих субтитров источника).

## Current Next Action

Подготовить `Implementation Handoff Packet` (пакет задания на реализацию) для Codex на Phase 1 MVP (первую минимально рабочую версию): загрузить собственный ролик, получить тайминги слов, выбрать один караоке-пресет, увидеть предпросмотр и экспортировать MP4 с вшитыми субтитрами.

## Canonical State Rule

При конфликте между разговором и репозиторием источником истины являются `PROJECT_STATE.md`, последний workflow run (цикл работы) и `logs/PROJECT_LOG.md`.
