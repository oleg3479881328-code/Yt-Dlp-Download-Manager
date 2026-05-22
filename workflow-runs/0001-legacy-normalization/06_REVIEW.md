# 06 REVIEW — Legacy Project Normalization

## Review Date

2026-05-22

## Review Target

Existing private repository `oleg3479881328-code/Yt-Dlp-Download-Manager` after initial inspection under Project Execution OS.

## Evidence Inspected

Committed code and documentation examined during review:

- `README.md`
- `requirements.txt`
- `.gitignore`
- `run.ps1`
- `app/main.py`
- `app/storage.py`
- `app/worker.py`
- `app/yt_service.py`
- `chrome_extension/manifest.json`
- `chrome_extension/background.js`
- `native_host/build_host.ps1`
- `native_host/register_host.ps1`
- `native_host/ytdlp_host.py`

## Confirmed Findings

1. The repository is a real existing local application, not an empty idea stub.
2. The application includes a FastAPI web dashboard (локальная веб-панель), SQLite persistence (локальное сохранение состояния), Chrome extension (расширение Chrome), native messaging host (локальный мост расширения) and optional transcription (необязательная транскрибация).
3. The project is intended for personal local use; public distribution requirements are outside current scope.
4. Before normalization, the repository lacked Project Execution OS source-of-truth artifacts: `PROJECT_ENTRYPOINT.md`, `PROJECT_STATE.md`, `PROJECT_RULES.md`, and `logs/PROJECT_LOG.md`.

## Risk Review

### RISK-001 — Suspected audio output-path defect

The web runtime (веб-исполнитель) configures FFmpeg extraction to MP3 for audio mode, while the worker records `ydl.prepare_filename(info)` as `output_path`. The recorded path may refer to the pre-conversion source file instead of the resulting MP3.

Review status: credible suspected defect; not validated by execution.

### RISK-002 — Dual runtime drift

The web dashboard uses SQLite and Python `YoutubeDL`, while the extension/native host uses a JSON registry and local executable calls. This duplicates some behavior.

Review status: accepted warning because current scope is personal use only. No architecture rewrite is justified now.

## Review Outcome

`accept with warnings`

The project is suitable to remain a personal local tool and to continue in `compact` Project Execution OS mode. Development should be gated by validation of `RISK-001`, not by architectural expansion.

## One Next Action

Run a single local validation: download audio through the web dashboard and verify that the final MP3 file can be opened and downloaded through the web interface.
