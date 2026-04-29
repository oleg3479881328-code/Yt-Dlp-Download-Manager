# Troubleshooting

- Title: Downloader yt-dlp Troubleshooting
- Status: Draft
- Owner: Кодер
- Last Updated: 2026-03-20
- Tags: troubleshooting, yt-dlp, chrome-extension

## Problem

Chrome extension cannot directly execute local binaries.

## Resolution

Использовать Native Messaging Host и зарегистрировать его в Chrome.

## Problem

Native host is not detected by extension.

## Resolution

- собрать `dist\ytdlp_host.exe`
- подставить реальный extension id в `native_host\com.oleg.ytdlp.json`
- зарегистрировать manifest в `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.oleg.ytdlp`

## Problem

`PyInstaller --clean` может падать на Windows из-за lock во временной папке `build`.

## Resolution

Для повторяемой локальной сборки использовать обычную пересборку без `--clean`.

## Problem

Playlist preview может не появиться, если источник удален, приватный или сам playlist URL больше не существует.

## Resolution

- показывать пользователю явную analyze error;
- не скрывать ошибку;
- отдельно проверять single-item flow, если нужен быстрый sanity-check.
