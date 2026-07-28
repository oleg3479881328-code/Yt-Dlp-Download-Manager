# Local AI Reels Workbench Run

## Goal

Start the existing local FastAPI Workbench with one obvious Windows action and open it in the browser.

Default local URL:

```text
http://127.0.0.1:8012/
```

## Recommended launch options

### Option 1: double-click launcher

From the repository root, double-click:

```text
start-workbench.bat
```

What it does:

1. runs `start-workbench.ps1`;
2. creates `.venv` if missing;
3. installs `requirements.txt` when needed;
4. opens the Workbench URL in the default browser;
5. keeps the terminal open with live server logs.

### Option 2: PowerShell launcher

From the repository root:

```powershell
.\start-workbench.ps1
```

Optional flags:

```powershell
.\start-workbench.ps1 -NoBrowser
.\start-workbench.ps1 -Port 8013
```

## What you should see

The browser should open `AI Reels Workbench` with:

- Source block;
- Selected range block;
- Transcript / Episode Picker block;
- Recent clip jobs block.

## Troubleshooting

### Port 8012 is busy

Symptom:

```text
Port 8012 is already in use on 127.0.0.1
```

Fix:

```powershell
.\start-workbench.ps1 -Port 8013
```

Or stop the process already using `8012`.

### Python is missing

Symptom:

```text
Python 3.12+ was not found
```

Fix:

- install Python for Windows;
- ensure `py` or `python` is available in `PATH`;
- rerun the launcher.

### Dependencies are missing

The launcher creates `.venv` and installs `requirements.txt` automatically when needed.

If install fails:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then rerun:

```powershell
.\start-workbench.ps1
```

### ffmpeg is missing

The Workbench UI can still open without `ffmpeg`, but clip creation/cutting may fail.

Expected local paths:

- `ffmpeg` in `PATH`; or
- `C:\yt-dlp\ffmpeg.exe`

### Browser does not open automatically

Start the launcher, then open this URL manually:

```text
http://127.0.0.1:8012/
```
