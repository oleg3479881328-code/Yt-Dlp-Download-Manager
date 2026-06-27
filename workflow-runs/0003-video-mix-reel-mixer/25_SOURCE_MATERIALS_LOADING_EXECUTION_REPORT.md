# VIDEO MIX Stage 1.8 — Source Materials Loading Execution Report

## Files Changed

- `app/main.py`
- `app/static/styles.css`
- `app/static/video-mix-dashboard.js`
- `app/templates/video_mix_dashboard.html`
- `app/video_mix_dashboard.py`
- `tests/test_video_mix_dashboard_api.py`
- `video_mix/cli.py`
- `video_mix/service.py`
- `PROJECT_ENTRYPOINT.md`
- `PROJECT_RULES.md`
- `PROJECT_STATE.md`
- `logs/latest.md`
- `logs/PROJECT_LOG.md`

## UX Delivered

- added a new `Материалы` section to the VIDEO MIX dashboard
- owner can type or paste a source folder path
- owner can open a native Windows folder picker for source materials
- owner can scan the selected folder before planning
- scan result shows:
  - total files
  - supported media count
  - video count
  - photo count
  - ignored or unsupported count
  - first file names as preview
- owner can keep the auto-generated `work_dir` or override it manually
- owner can click `Создать / обновить проект`
- after success, the dashboard auto-loads the resulting work_dir and preserves the existing review controls

## Backend Endpoints Delivered

- `POST /api/video-mix/pick-workdir`
- `POST /api/video-mix/pick-source-folder`
- `POST /api/video-mix/source/scan`
- `POST /api/video-mix/source/plan`

## Work_dir Picker Status

The `work_dir` picker had to be added in this local branch and is now available alongside the new source-folder picker.

## Source Loading Versus Work_dir Loading

- `work_dir` loading opens an already prepared VIDEO MIX project state
- source-materials loading starts from a raw folder of videos or photos, scans it, plans clips and candidates, generates `review.html` plus thumbnails, creates or updates a work_dir, and then auto-loads the dashboard payload

## Validation Commands / Results

```powershell
node --test frontend-tests\video-mix-dashboard.test.mjs
python -m pytest tests/test_video_mix_pipeline.py tests/test_segment_api.py tests/test_video_mix_dashboard_api.py tests/test_video_mix_dashboard_launcher.py
python -m ruff check app video_mix tests frontend-tests
@'
from pathlib import Path
from tempfile import gettempdir
import json
import shutil

from fastapi.testclient import TestClient
from app.main import app

source_dir = Path('video_mix_validation/input').resolve()
work_dir = Path(gettempdir()) / 'yt_dlp_video_mix_issue41_smoke'
if work_dir.exists():
    shutil.rmtree(work_dir)

client = TestClient(app)
scan_response = client.post('/api/video-mix/source/scan', json={'source_dir': str(source_dir)})
plan_response = client.post('/api/video-mix/source/plan', json={
    'source_dir': str(source_dir),
    'project_name': 'Issue 41 Smoke',
    'work_dir': str(work_dir),
})

print(json.dumps({
    'scan_status': scan_response.status_code,
    'scan_json': scan_response.json(),
    'plan_status': plan_response.status_code,
    'plan_json': {key: value for key, value in plan_response.json().items() if key != 'dashboard'},
    'dashboard_summary': plan_response.json().get('dashboard', {}).get('summary', {}),
}, ensure_ascii=False, indent=2))
'@ | python -
```

Results:

- frontend node tests passed
- broader VIDEO MIX/dashboard pytest set passed
- `ruff` passed
- live source scan endpoint returned HTTP `200`
- live source plan endpoint returned HTTP `200`

## Local Smoke Result And Counts

Smoke was run against:

- source folder: `video_mix_validation/input`
- generated work_dir: `%TEMP%\yt_dlp_video_mix_issue41_smoke`

Observed counts:

- `total_files=5`
- `supported_media_count=5`
- `supported_video_count=5`
- `supported_photo_count=0`
- `ignored_or_unsupported_count=0`
- `asset_count=5`
- `clip_count=10`
- `candidate_count=10`
- `thumbnail_count=10`
- dashboard payload summary loaded with:
  - `approved_candidate_count=0`
  - `exported_candidate_count=0`

Generated local review artifact:

- `%TEMP%\yt_dlp_video_mix_issue41_smoke\reports\review.html`

## Known Limitations

- planning and review generation are still synchronous inside the request path; for local owner use this is acceptable, but long scans will block until completion
- backend errors remain API-originated and may still be English unless separately translated server-side
- the source-folder picker and work_dir picker both use the same Windows folder dialog and do not yet customize dialog title per action
- this pass does not redesign segmentation, templates, export behavior or review artifact HTML

## Exact Owner-Facing Usage Steps In Russian

1. Откройте локальный VIDEO MIX dashboard.
2. В блоке `Материалы` нажмите `Выбрать материалы` или вставьте путь к папке вручную.
3. При необходимости измените `Имя проекта`.
4. Оставьте предложенный `work_dir` или укажите свой.
5. Нажмите `Сканировать`, чтобы проверить найденные файлы.
6. Нажмите `Создать / обновить проект`.
7. После завершения дождитесь автозагрузки dashboard и продолжайте обычное ревью кандидатов, approve/reject и export.
