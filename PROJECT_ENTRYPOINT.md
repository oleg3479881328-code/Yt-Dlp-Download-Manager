# PROJECT ENTRYPOINT — yt-dlp Download Manager

## Project Goal

Личный локальный Windows-инструмент для скачивания медиа через `yt-dlp`, управления загрузками из web dashboard (веб-панели) и Chrome extension (расширения Chrome), а также локальной транскрибации в `SRT + TXT`.

## Project Mode

- mode: `compact`
- use case: personal local tool only
- repository: private dedicated GitHub repository
- normalization status: existing project normalized into Project Execution OS on 2026-05-22

## Required Read Order

1. `PROJECT_STATE.md` — текущее подтверждённое состояние и следующий шаг.
2. `PROJECT_RULES.md` — ограничения и правила работы.
3. `logs/PROJECT_LOG.md` — хронология решений и изменений.
4. Latest workflow run: `workflow-runs/0001-legacy-normalization/07_RESULT.md`.

## Verified Current Components

- `app/` — FastAPI web dashboard (локальная веб-панель), SQLite state (хранилище состояния), background download worker (фоновый обработчик загрузок).
- `chrome_extension/` — standalone Chrome extension (отдельное расширение Chrome).
- `native_host/` — native messaging host (локальный мост между расширением и Windows-инструментами).
- optional transcription (опциональная транскрибация) through `faster-whisper` into `.srt` and `.txt`.

## Current Next Action

Проверить локально один критический сценарий: audio download (загрузка аудио) через web dashboard с итоговым MP3-файлом и корректной работой открытия/скачивания результата.

## Canonical State Rule

При конфликте между разговором и репозиторием источником истины являются `PROJECT_STATE.md`, последний workflow run (цикл работы) и `logs/PROJECT_LOG.md`.
