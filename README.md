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

## VIDEO MIX Dashboard

One-step local launcher:

```powershell
.\start_video_mix_dashboard.ps1
```

If auto-detection does not find a `VIDEO MIX` work directory:

```powershell
.\start_video_mix_dashboard.ps1 -WorkDir C:\path\to\your\work
```

Diagnostics only:

```powershell
.\start_video_mix_dashboard.ps1 -DiagnosticsOnly
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

Download entrypoints:

- context menu: right click on page/link/video -> `Скачать через yt-dlp` -> immediate download -> output folder opens after completion
- toolbar popup: open the full page when manual controls, metadata preview or transcription options are needed

Standalone extension extras:

- metadata preview before download
- automatic daily `yt-dlp` update check (default channel: `nightly`)
- manual `yt-dlp` update button and installed-version diagnostics
- Instagram single-Reel MP4 video-plus-audio flow
- optional local browser-cookie fallback for login/CAPTCHA cases (disabled by default)
- recent local jobs
- optional transcript generation after download
- local audio/video file upload for transcription in full mode
- open downloads folder
- open last completed file
- local status updates from `_logs\jobs_registry.json`

### Stable Quick Downloader Install And Updates

First installation:

```text
INSTALL_QUICK_DOWNLOADER.cmd
```

The installer:

- validates and installs the version bundled with the downloaded repository ZIP;
- validates the extension/native-host package;
- installs it into `%LOCALAPPDATA%\QuickDownloader`;
- builds the native host;
- opens `chrome://extensions` and the stable extension folder;
- asks for the extension ID once and registers the native host.

Chrome must always load the unpacked extension from:

```text
%LOCALAPPDATA%\QuickDownloader\extension
```

Do not move, rename or delete that folder.

All later updates use only:

```text
%LOCALAPPDATA%\QuickDownloader\UPDATE_QUICK_DOWNLOADER.cmd
```

The updater downloads and validates the latest `master`, replaces only application
files, rebuilds and re-registers the native host, and preserves the saved extension
ID, configuration, downloads and logs. It opens `chrome://extensions` at the end;
press `Reload` for Quick Downloader if Chrome has not reloaded the unpacked
extension automatically.

## Notes

- Downloaded files are stored in `downloads` by default.
- App state is persisted in `data\app.db`.
- `yt-dlp` may require `ffmpeg` in `PATH` for merge and audio extraction.
- Public Instagram Reels should be tested first without cookies. If Instagram requires login or returns a CAPTCHA/403, select the browser where the owner is already signed in under extension settings.
- Local transcription uses `faster-whisper` and creates `.srt` and `.txt` next to the media file.
- UI live state is streamed over WebSocket at `/ws/state`.
- Standalone extension defaults to:
  - `C:\yt-dlp\yt-dlp.exe`
  - `C:\yt-dlp\ffmpeg.exe`
  - `C:\yt-dlp\DOWNLOADS`
