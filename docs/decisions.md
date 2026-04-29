# Decisions

- Title: Downloader yt-dlp Decisions
- Status: Draft
- Owner: Кодер
- Last Updated: 2026-03-20
- Tags: decisions, yt-dlp, chrome-extension

## Decision 1

Использовать два параллельных интерфейса:

- web dashboard для полного локального управления;
- standalone Chrome extension для quick/full browser flow.

## Decision 2

Для независимого расширения использовать Chrome Native Messaging Host, потому что обычное расширение не может напрямую запускать `C:\yt-dlp\yt-dlp.exe`.

## Decision 3

Использовать `C:\yt-dlp` как дефолтную локальную инфраструктуру:

- `C:\yt-dlp\yt-dlp.exe`
- `C:\yt-dlp\ffmpeg.exe`
- `C:\yt-dlp\DOWNLOADS`

## Decision 4

Для standalone UX хранить lightweight job registry в `C:\yt-dlp\DOWNLOADS\_logs\jobs_registry.json`, чтобы extension мог показывать статусы и открывать последний готовый файл без постоянного backend-процесса.

## Decision 5

Для richer standalone UX расширять native host, а не поднимать отдельный always-on backend:

- `analyze` для preview;
- `status` для recent jobs;
- `open_job_file` и `open_job_folder` для быстрых действий;
- popup показывает lightweight summary, а full mode — richer preview и controls.

## Decision 6

Для транскрибации использовать локальный post-download шаг внутри native host runner:

- сначала скачать медиа через `yt-dlp`;
- затем, если включен флаг транскрибации, создать `SRT + TXT` рядом с файлом через `faster-whisper`;
- не требовать отдельный постоянно запущенный backend только ради транскриптов.
