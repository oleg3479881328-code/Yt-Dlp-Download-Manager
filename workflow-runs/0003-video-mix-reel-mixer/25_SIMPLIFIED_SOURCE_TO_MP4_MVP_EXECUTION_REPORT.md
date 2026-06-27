# VIDEO MIX Stage 1.8 — Simplified Source-to-MP4 MVP Execution Report

## Files Changed

- `app/main.py`
- `app/static/styles.css`
- `app/static/video-mix-dashboard.js`
- `app/templates/video_mix_dashboard.html`
- `app/video_mix_dashboard.py`
- `tests/test_video_mix_dashboard_api.py`
- `tests/test_video_mix_pipeline.py`
- `video_mix/cli.py`
- `video_mix/service.py`
- `PROJECT_ENTRYPOINT.md`
- `PROJECT_RULES.md`
- `PROJECT_STATE.md`
- `logs/latest.md`
- `logs/PROJECT_LOG.md`

## Exact UX Delivered

- preserved the existing dashboard review controls, bulk approve/reject, export-approved flow, thumbnails and work_dir loading
- preserved the existing source scan / source plan materials-first flow
- added a new `Быстрый микс` / `Quick Mix` section in the dashboard
- owner can:
  - choose source folder with native Windows folder picker
  - paste/type source folder path manually
  - scan the folder first
  - enter `seconds per output video`
  - enter `number of videos`
  - click one button: `Сгенерировать ролики`
- after generation the dashboard now:
  - returns ready MP4 output paths
  - auto-loads the generated work_dir
  - keeps the output paths visible as direct links
  - allows opening `exports` through the existing dashboard action

## Backend Endpoints Delivered

- `POST /api/video-mix/pick-workdir`
- `POST /api/video-mix/pick-source-folder`
- `POST /api/video-mix/source/scan`
- `POST /api/video-mix/source/plan`
- `POST /api/video-mix/quick-mix`

## How The Quick Mix Flow Works

1. Scan the source folder for usable videos and photos.
2. Normalize or create a predictable work_dir.
3. Probe source videos with `ffprobe`; photos are accepted as still assets.
4. Build a deterministic sequence of short segments:
   - video assets contribute trimmed vertical clips
   - photo assets contribute still segments rendered to MP4
5. Concatenate those rendered segment MP4 files into final exports:
   - `exports/quick_mix_001.mp4`
   - `exports/quick_mix_002.mp4`
   - and so on
6. Save minimal work_dir metadata so the existing dashboard can still load the result.

This is intentionally a direct generation path:

- no manual approve/reject required
- no candidate review gate required before MP4 output
- existing review flow remains available separately

## Whether Photos Are Supported

Yes.

First-pass behavior:

- photos are rendered as still vertical video segments with ffmpeg
- photo segments are mixed together with video-derived segments in the same direct MP4 output flow

Validation note:

- live smoke passed with `2` video files plus `1` generated JPG photo asset in the same source folder

## Validation Commands / Results

```powershell
node --test frontend-tests\video-mix-dashboard.test.mjs
python -m pytest tests/test_video_mix_pipeline.py tests/test_segment_api.py tests/test_video_mix_dashboard_api.py tests/test_video_mix_dashboard_launcher.py
python -m ruff check app video_mix tests frontend-tests
@'
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from app.main import app

source_seed = Path('video_mix_validation/input').resolve()
base_tmp = Path(tempfile.gettempdir())
work_dir = base_tmp / 'yt_dlp_quick_mix_issue41_smoke_v2'
source_dir = base_tmp / 'yt_dlp_quick_mix_issue41_source_valid_v2'
if work_dir.exists():
    shutil.rmtree(work_dir)
if source_dir.exists():
    shutil.rmtree(source_dir)
source_dir.mkdir(parents=True, exist_ok=True)

for path in sorted(source_seed.glob('*.mp4'))[:2]:
    shutil.copy2(path, source_dir / path.name)

photo_path = source_dir / 'photo_valid.jpg'
subprocess.run([
    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=white:s=1080x1920:d=0.1', '-frames:v', '1', str(photo_path)
], check=True, capture_output=True, text=True)

client = TestClient(app)
response = client.post('/api/video-mix/quick-mix', json={
    'source_dir': str(source_dir),
    'project_name': 'Quick Mix Smoke',
    'work_dir': str(work_dir),
    'duration_seconds': 6,
    'output_count': 2,
})
response.raise_for_status()
payload = response.json()

probe_results = []
for relative_path in payload['output_paths']:
    output_path = work_dir / relative_path
    probe = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=filename,duration,size',
        '-show_entries', 'stream=width,height,r_frame_rate',
        '-of', 'json',
        str(output_path),
    ], check=True, capture_output=True, text=True)
    probe_results.append(json.loads(probe.stdout))

print(json.dumps({
    'response': payload,
    'probe_results': probe_results,
}, ensure_ascii=False, indent=2))
'@ | python -
```

Results:

- frontend node tests passed
- broader VIDEO MIX/dashboard pytest set passed
- `ruff` passed
- live `POST /api/video-mix/quick-mix` smoke returned HTTP `200`
- live smoke generated `2` finished MP4 outputs
- both outputs were probeable with `ffprobe`

## Local Smoke Result And Output Count

Smoke source folder:

- `%TEMP%\yt_dlp_quick_mix_issue41_source_valid_v2`

Smoke work_dir:

- `%TEMP%\yt_dlp_quick_mix_issue41_smoke_v2`

Smoke source contents:

- `2` local validation MP4 files
- `1` generated JPG photo asset

Generated outputs:

- `%TEMP%\yt_dlp_quick_mix_issue41_smoke_v2\exports\quick_mix_001.mp4`
- `%TEMP%\yt_dlp_quick_mix_issue41_smoke_v2\exports\quick_mix_002.mp4`

Observed output proof:

- output count: `2`
- `quick_mix_001.mp4`
  - `1080x1920`
  - `30fps`
  - `6.000000s`
  - `22033 bytes`
- `quick_mix_002.mp4`
  - `1080x1920`
  - `30fps`
  - `6.000000s`
  - `23128 bytes`

## Known Limitations

- direct Quick Mix exports are intentionally simple and deterministic, not quality-ranked
- no audio is preserved in this first-pass Quick Mix flow; segments are rendered as video-only MP4 for concat stability
- quick mix outputs do not create candidate cards or review artifacts by default; the existing review flow remains separate
- planning/render generation remains synchronous inside the request path
- backend-originated errors may still be English unless separately translated server-side
- smoke exposed one bad tiny PNG test asset that stalled ffmpeg; a valid JPG photo asset passed, so first-pass photo support is real but assumes ordinary image files
- this pass does not redesign wedding templates, scoring, candidate diversity, or advanced timeline controls

## Exact Owner-Facing Usage Steps In Russian

1. Откройте локальный VIDEO MIX dashboard.
2. В блоке `Материалы` выберите папку с исходными файлами или вставьте путь вручную.
3. При желании нажмите `Сканировать`, чтобы увидеть краткую сводку по видео и фото.
4. В блоке `Быстрый микс` укажите:
   - сколько секунд должен длиться один ролик
   - сколько роликов нужно сгенерировать
5. Нажмите `Сгенерировать ролики`.
6. Дождитесь завершения генерации.
7. Откройте готовые MP4 из списка путей или через кнопку открытия `exports`.
