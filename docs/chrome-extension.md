# Chrome Extension

- Title: yt-dlp Chrome Extension Notes
- Status: Draft
- Owner: Кодер
- Last Updated: 2026-03-20
- Tags: chrome-extension, native-messaging, yt-dlp

## Modes

- `Mini`: правый клик по видео, ссылке или странице -> `Скачать через yt-dlp` -> немедленный старт загрузки.
- `Full`: та же команда открывает встроенную full-page форму расширения с URL, режимом и быстрыми действиями.

## Current Full Mode Features

- metadata preview до старта загрузки;
- опциональная локальная транскрибация в `SRT + TXT`;
- thumbnail, title, extractor, duration;
- preview первых playlist items, если extractor их возвращает;
- live status polling по локальному job registry;
- recent jobs list;
- быстрые действия `Open File` / `Open Folder` по конкретному recent job;
- `Open Last File`;
- `Open Folder`;
- `Probe` для проверки `yt-dlp`, `ffmpeg` и output directory.

## Current Popup Features

- переключение `Mini` / `Full`;
- дефолтная локальная транскрибация через настройки расширения;
- `Open Folder`;
- `Open Last File`;
- mini recent jobs block с кратким статусом без открытия full page.

## Components

- `chrome_extension/` — само расширение
- `native_host/` — native messaging host
- `C:\yt-dlp` — локальные бинарники и папка загрузок
