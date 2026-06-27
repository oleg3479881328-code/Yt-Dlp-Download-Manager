# VIDEO MIX Stage 1.4 — One-Click Dashboard Launcher Execution Report

## Scope

Add a Windows-friendly one-click launcher and first-run diagnostics for the local `VIDEO MIX` dashboard.

## Files Changed

- `start_video_mix_dashboard.ps1`
- `video_mix/dashboard_launcher.py`
- `tests/test_video_mix_dashboard_launcher.py`
- `README.md`
- `PROJECT_ENTRYPOINT.md`
- `PROJECT_STATE.md`
- `PROJECT_RULES.md`
- `logs/latest.md`
- `logs/PROJECT_LOG.md`
- `workflow-runs/0003-video-mix-reel-mixer/22_DASHBOARD_LAUNCHER_EXECUTION_REPORT.md`

## Delivered

- Added `start_video_mix_dashboard.ps1` as the owner-facing launcher.
- Launcher now:
  - auto-detects a `VIDEO MIX` work_dir when possible
  - accepts `-WorkDir` when auto-detection is not enough
  - starts the FastAPI server on `127.0.0.1:8765`
  - opens the browser automatically unless `-NoBrowser` is passed
  - prints clear Russian-friendly next steps on failure
- Added diagnostics logic in `video_mix/dashboard_launcher.py`.
- Added diagnostics-only mode:
  - `.\start_video_mix_dashboard.ps1 -DiagnosticsOnly`

## Owner-Facing Launch Step

```powershell
.\start_video_mix_dashboard.ps1
```

If auto-detection does not find the correct `work_dir`:

```powershell
.\start_video_mix_dashboard.ps1 -WorkDir C:\path\to\your\work
```

Diagnostics only:

```powershell
.\start_video_mix_dashboard.ps1 -DiagnosticsOnly
```

## Expected Dashboard URL

```text
http://127.0.0.1:8765/video-mix?work_dir=<encoded_work_dir>
```

Validated synthetic URL:

```text
http://127.0.0.1:8765/video-mix?work_dir=C%3A%5CUsers%5Coleg3%5COneDrive%5CDocuments%5CYt-Dlp-Download-Manager%5Cvideo_mix_validation%5Cwork
```

## Validation Commands

```powershell
python -m pytest tests/test_video_mix_pipeline.py tests/test_segment_api.py tests/test_video_mix_dashboard_api.py tests/test_video_mix_dashboard_launcher.py
python -m ruff check app video_mix tests
python -m video_mix.cli plan video_mix_validation/input --project-name "Wedding Validation" --work-dir video_mix_validation/work
python -m video_mix.cli review video_mix_validation/work
powershell -ExecutionPolicy Bypass -File .\start_video_mix_dashboard.ps1 -WorkDir .\video_mix_validation\work -DiagnosticsOnly
powershell -ExecutionPolicy Bypass -File .\start_video_mix_dashboard.ps1 -WorkDir .\video_mix_validation\work -NoBrowser
powershell -ExecutionPolicy Bypass -File .\start_video_mix_dashboard.ps1 -NoBrowser
Invoke-WebRequest "http://127.0.0.1:8765/video-mix?work_dir=C%3A%5CUsers%5Coleg3%5COneDrive%5CDocuments%5CYt-Dlp-Download-Manager%5Cvideo_mix_validation%5Cwork"
```

## Validation Result

- `pytest` passed
- `ruff` passed
- synthetic `plan` passed
- synthetic `review` passed
- diagnostics mode passed
- launcher start mode passed
- one-step no-argument launcher path passed
- dashboard URL returned HTTP `200`

## Known Limitations

- Launcher is Windows/PowerShell oriented by design.
- Auto-detection currently prefers repository-local known paths such as `video_mix_validation/work` and `_video_mix_work`.
- The launcher keeps the local FastAPI server running after start; it does not manage shutdown for the owner.
- Downloader routes still require their own runtime dependencies when used.

## Next Recommendation

If this launcher baseline is accepted, the next isolated pass should focus on one of:

1. a small desktop shortcut / `.bat` companion for non-PowerShell users, or
2. a safer server-status / stop-server helper around the launcher flow.
