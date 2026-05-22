---
status: in-progress
project_mode: compact
current_step: 07_RESULT
current_run: workflow-runs/0001-legacy-normalization/
last_updated: 2026-05-22
next_action: Validate web-dashboard audio download output path against the resulting MP3 file.
---

# PROJECT STATE — yt-dlp Download Manager

## Current Phase

Личный локальный инструмент уже существует в виде работающего codebase (кодовой базы) и приведён к `compact` project mode (компактному проектному режиму) Project Execution OS.

## Purpose

Скачивать медиа локально через `yt-dlp` с двумя пользовательскими входами:

- web dashboard (веб-панель) для очереди, истории, настроек и статусов;
- Chrome extension (расширение Chrome) для быстрого запуска скачивания из браузера.

Дополнительная личная функция: local transcription (локальная транскрибация) медиа в `.srt` и `.txt`.

## Confirmed Repository State

Проверено по committed files (зафиксированным файлам) на ветке `master`:

- `README.md` описывает web dashboard, Chrome extension, native host и транскрибацию;
- `app/main.py` содержит FastAPI API и WebSocket `/ws/state`;
- `app/storage.py` хранит задания, элементы плейлистов, логи и настройки в SQLite `data/app.db`;
- `app/worker.py` выполняет одиночные и playlist (плейлист) загрузки с retry (повторными попытками);
- `app/yt_service.py` формирует параметры `yt-dlp` и анализирует URL;
- `chrome_extension/manifest.json` описывает Manifest V3 extension (расширение Chrome стандарта MV3);
- `chrome_extension/background.js` связывает действия расширения с native messaging host (локальным мостом);
- `native_host/ytdlp_host.py` выполняет отдельные локальные задания загрузки и транскрибации;
- `.gitignore` исключает окружение, сборки, скачанные файлы и локальную SQLite-базу.

## Confirmed Decisions

1. Проект предназначен для личного использования, а не для Chrome Web Store или продажи.
2. Проект остаётся в отдельном private GitHub repository (приватном репозитории GitHub).
3. Применяется `compact mode` (компактный режим), а не тяжёлая полная структура проекта.
4. Существующие два runtime contour (исполнительных контура) — web dashboard и standalone extension/native host — сохраняются как допустимый компромисс личного инструмента; их объединение сейчас не является задачей.
5. Новые функции не являются приоритетом до проверки основного подозреваемого дефекта.

## Reviewed Risks

### RISK-001 — Web audio output path may be wrong

При audio download (загрузке аудио) web worker (веб-обработчик) использует FFmpeg post-processing (постобработку) в MP3, но сохраняет путь результата через `ydl.prepare_filename(info)`. Этот путь может указывать на исходный файл до конвертации, а не на итоговый `.mp3`.

Status: suspected from code review; not yet validated by execution.
Impact: кнопки открыть/скачать файл в web dashboard могут не находить успешно созданный MP3.

### RISK-002 — Two runtime contours may drift

Веб-панель хранит состояние в SQLite и использует Python `YoutubeDL`; расширение хранит историю/статусы через JSON registry (JSON-реестр) и запускает отдельный executable (исполняемый файл). Для личного использования это допустимо, но изменения нужно проверять отдельно в обоих контурах.

Status: accepted warning for personal-use scope.

## Latest Result

Legacy project normalization (нормализация существующего проекта) начата: репозиторий получает явные state artifacts (артефакты состояния), правила и журнал в соответствии с Project Execution OS.

## Open Questions

- Подтверждается ли `RISK-001` при реальной загрузке аудио через web dashboard?
- Работает ли локальная установленная цепочка `yt-dlp + ffmpeg + faster-whisper` на текущей Windows-машине без дополнительной настройки?

## Current Next Action

Выполнить один validation run (проверочный запуск): скачать аудио через web dashboard, убедиться, что итоговый `.mp3` существует, а действия открытия и скачивания файла работают через web interface (веб-интерфейс).
