---
status: in-progress
project_mode: compact
current_step: 03_PLAN
current_run: workflow-runs/0002-animated-subtitle-module/
last_updated: 2026-05-25
next_action: Prepare an Implementation Handoff Packet for Phase 1 Animated Subtitle Video Maker MVP.
---

# PROJECT STATE — yt-dlp Download Manager

## Current Phase

Личный локальный инструмент нормализован в `compact mode` (компактном режиме) Project Execution OS. Scope (границы проекта) расширен подтверждённым решением владельца: в этот же репозиторий добавляется модуль создания собственных роликов с анимированными субтитрами.

## Purpose

Полный локальный цикл работы с роликами:

- скачивание медиа через `yt-dlp`;
- web dashboard (веб-панель) для очереди, истории, настроек и статусов;
- Chrome extension (расширение Chrome) для быстрого запуска скачивания из браузера;
- local transcription (локальная транскрибация) и получение субтитров;
- `Animated Subtitle Video Maker` (модуль создания роликов с анимированными субтитрами) для собственных видео пользователя.

## Confirmed Existing Repository State

Проверено по committed files (зафиксированным файлам) на ветке `master`:

- `README.md` описывает web dashboard (веб-панель), Chrome extension (расширение Chrome), native host (локальный мост) и транскрибацию;
- `app/main.py` содержит FastAPI API и WebSocket `/ws/state`;
- `app/storage.py` хранит задания, элементы плейлистов, логи и настройки в SQLite `data/app.db`;
- `app/worker.py` выполняет загрузки с retry (повторными попытками);
- `app/yt_service.py` формирует параметры `yt-dlp` и анализирует URL;
- `chrome_extension/` и `native_host/` образуют отдельный локальный контур расширения;
- `.gitignore` исключает окружение, сборки, скачанные файлы и локальную SQLite-базу.

## Confirmed Decisions

1. Проект предназначен для личного использования, а не для Chrome Web Store или продажи.
2. Проект остаётся в отдельном private GitHub repository (приватном репозитории GitHub).
3. Применяется `compact mode` (компактный режим).
4. Существующие два runtime contours (исполнительных контура) — web dashboard (веб-панель) и extension/native host (расширение/локальный мост) — сохраняются как допустимый компромисс личного инструмента.
5. Решение владельца от 2026-05-25: добавить `Animated Subtitle Video Maker` внутрь текущего проекта, а не создавать отдельный репозиторий.
6. Технологическое направление для нового модуля: `Remotion` + `@remotion/captions` для preview/rendering (предпросмотра/отрисовки), `stable-ts` / `faster-whisper` для word-level timing (временных меток слов), `yt-dlp` для получения уже существующих субтитров источника.

## Approved Not Yet Implemented Scope

Новый модуль должен позволить:

- загружать собственный ролик;
- использовать существующие субтитры или создавать новые;
- получать word-level timing (временные метки каждого слова);
- делать karaoke highlighting (караоке-подсветку произносимого слова);
- настраивать цвет, стиль подсветки, анимацию появления, последовательность и положение текста;
- видеть preview (предпросмотр);
- экспортировать MP4 с burned-in subtitles (вшитыми субтитрами).

Implementation status (статус реализации): approved scope only (утверждены только границы); код модуля не создан и не проверен.

## Reviewed Risks

### RISK-001 — Existing web audio output path may be wrong

При audio download (загрузке аудио) web worker (веб-обработчик) использует FFmpeg post-processing (постобработку) в MP3, но сохранённый путь может указывать на исходный файл до конвертации, а не на итоговый `.mp3`.

Status (статус): suspected from code review (подозревается по проверке кода); not validated by execution (не подтверждено запуском).

### RISK-002 — Two runtime contours may drift

Дублирование web и extension/native логики принято для личного использования, но требует внимательной проверки затронутого контура при изменениях.

Status (статус): accepted warning (принятое предупреждение).

### RISK-003 — New video rendering layer increases stack complexity

Добавление `Remotion` создаёт JavaScript/React video-rendering layer (слой рендеринга видео на JavaScript/React) рядом с существующим Python-приложением.

Status (статус): accepted for planned module (принято для запланированного модуля); MVP должен быть узким и не затрагивать существующие загрузки.

## Latest Result

Решение о новом модуле подтверждено владельцем и зафиксировано в проектном состоянии. Реализация ещё не начата.

## Current Next Action

Подготовить `Implementation Handoff Packet` (пакет задания на реализацию) для Codex на Phase 1 MVP (первую минимально рабочую версию): собственный ролик → тайминги слов → один караоке-пресет → предпросмотр → экспорт MP4 с вшитыми субтитрами.
