# yt-dlp Download Manager

## AI Start

If this repository is opened by an AI coding agent, start with `PROJECT_ENTRYPOINT.md` before using this README as operational context.

Single-user local toolkit for `yt-dlp` with:

- web dashboard
- standalone Chrome extension
- native messaging host for direct local downloads
- optional local transcription to `SRT + TXT`
- local `C:\yt-dlp` toolchain defaults

## Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`

Or just run:

```powershell
.\run.ps1
```

Or:

```bat
start.bat
```

## Standalone Chrome Extension

Files:

- `chrome_extension/`
- `native_host/`

Flow:

1. Build native host:

```powershell
.\native_host\build_host.ps1
```

2. Load `chrome_extension` as unpacked extension in Chrome.
3. Copy the extension id.
4. Register host:

```powershell
.\native_host\register_host.ps1 -ExtensionId YOUR_EXTENSION_ID
```

Build output:

- `dist_v2\ytdlp_host\ytdlp_host.exe`

Modes:

- `Mini`: right click on page/link/video -> `Скачать через yt-dlp`
- `Full`: the same action opens the extension full page with manual controls

Standalone extension extras:

- metadata preview before download
- recent local jobs
- optional transcript generation after download
- local audio/video file upload for transcription in full mode
- open downloads folder
- open last completed file
- local status updates from `_logs\jobs_registry.json`

## Notes

- Downloaded files are stored in `downloads` by default.
- App state is persisted in `data\app.db`.
- `yt-dlp` may require `ffmpeg` in `PATH` for merge and audio extraction.
- Local transcription uses `faster-whisper` and creates `.srt` and `.txt` next to the media file.
- UI live state is streamed over WebSocket at `/ws/state`.
- Standalone extension defaults to:
  - `C:\yt-dlp\yt-dlp.exe`
  - `C:\yt-dlp\ffmpeg.exe`
  - `C:\yt-dlp\DOWNLOADS`
