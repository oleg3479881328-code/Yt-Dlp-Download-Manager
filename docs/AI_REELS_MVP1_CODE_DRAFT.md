# MVP 1 Segment Download — Code Draft Handoff

This draft supports Issue #10 and `docs/AI_VIDEO_REELS_PIPELINE_MVP.md`.

Branch:

```text
draft/mvp1-segment-download-code
```

This branch is **not a finished implementation**. It provides a safe starting point for the executor.

## What is already drafted

### `app/segment_utils.py`

Contains tested helpers for:

- parsing numeric seconds;
- parsing `MM:SS` / `HH:MM:SS(.ms)` strings;
- validating `start + end` or `start + duration`;
- sanitizing labels for filenames;
- producing a selected-range expression like `*65-95`;
- building a safe clips output template under the configured output directory.

### `tests/test_segment_utils.py`

Contains focused unit tests for the helpers above.

## Suggested integration plan

### 1. Extend `QueueRequest` in `app/main.py`

Draft shape:

```python
class QueueRequest(BaseModel):
    url: str
    mode: str = "video"
    quality: str = "bestvideo*+bestaudio/best"
    segment_start: str | float | None = None
    segment_end: str | float | None = None
    segment_duration: str | float | None = None
    segment_label: str | None = None
```

In `create_job()`, detect a segment request:

```python
from .segment_utils import SegmentValidationError, normalize_segment_payload

segment = None
if payload.segment_start is not None:
    try:
        segment_range = normalize_segment_payload(
            {
                "start": payload.segment_start,
                "end": payload.segment_end,
                "duration": payload.segment_duration,
                "label": payload.segment_label,
            }
        )
    except SegmentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    segment = {
        "start": segment_range.start,
        "end": segment_range.end,
        "duration": segment_range.duration,
        "label": segment_range.label,
        "section_expression": segment_range.section_expression,
    }
```

Store it in `analysis_json`:

```python
analysis_json = {**analysis, "segment": segment} if segment else analysis
```

Then use `analysis_json` in the job dictionary:

```python
"analysis_json": analysis_json,
```

Recommended stage/log copy:

```python
stage = "Queued segment" if segment else "Queued"
log_message = "Segment job added to queue" if segment else "Job added to queue"
```

### 2. Extend `build_ydl_options()` in `app/yt_service.py`

Current signature:

```python
def build_ydl_options(output_dir: Path, mode: str, quality: str, progress_hook) -> dict[str, Any]:
```

Suggested draft signature:

```python
def build_ydl_options(
    output_dir: Path,
    mode: str,
    quality: str,
    progress_hook,
    segment: dict[str, Any] | None = None,
) -> dict[str, Any]:
```

If segment is present:

```python
from .segment_utils import build_clip_output_template

if segment:
    options["outtmpl"] = build_clip_output_template(output_dir, label=segment.get("label"))
    options["download_ranges"] = [segment["section_expression"]]  # VERIFY against installed yt-dlp Python API
    options["force_keyframes_at_cuts"] = True
```

Important: the executor must verify the Python API shape for `download_ranges` against the installed `yt-dlp` version.

Fallback if the Python API shape does not accept the list directly:

- use the yt-dlp CLI path via subprocess for segment jobs; or
- import the correct helper from the installed yt-dlp package and wrap the section expression properly.

The upstream CLI option is `--download-sections`, with `*` prefix for time ranges, and it needs ffmpeg. `--force-keyframes-at-cuts` can reduce artifacts but is slower.

### 3. Extend `DownloadWorker._download_single()` in `app/worker.py`

At the start of `_download_single()` after `quality`:

```python
segment = (job.get("analysis_json") or {}).get("segment")
```

Then pass it into options:

```python
options = build_ydl_options(
    output_dir,
    mode,
    quality,
    self._progress_hook(job_id),
    segment=segment,
)
```

Log segment details:

```python
if segment:
    self.storage.add_log(
        job_id,
        f"Starting selected segment download: {segment['section_expression']} ({segment['label']})",
        utc_now(),
    )
```

Playlist handling should stay out of scope for MVP 1 unless the executor finds it trivial. First target: single URL → one selected segment.

### 4. Minimal dashboard UI

Add fields near the existing URL/quality controls:

```html
<div class="grid-three segment-controls">
  <label class="field">
    <span>Segment start</span>
    <input id="segmentStart" type="text" placeholder="00:01:05 or 65">
  </label>
  <label class="field">
    <span>Segment end</span>
    <input id="segmentEnd" type="text" placeholder="00:01:35 or 95">
  </label>
  <label class="field">
    <span>Label</span>
    <input id="segmentLabel" type="text" placeholder="hook">
  </label>
</div>
```

When calling `/api/jobs`, include these only when start is present:

```javascript
const segmentStart = qs("segmentStart").value.trim();
const body = {
  url: qs("url").value.trim(),
  mode: qs("mode").value,
  quality: qs("quality").value.trim(),
};
if (segmentStart) {
  body.segment_start = segmentStart;
  body.segment_end = qs("segmentEnd").value.trim();
  body.segment_label = qs("segmentLabel").value.trim();
}
```

Button copy can be simple:

```text
Download segment
Скачать фрагмент
```

### 5. Required executor validation

Executor must run:

```powershell
python -m pytest tests/test_segment_utils.py
python -m pytest tests
python -m ruff check app/segment_utils.py tests/test_segment_utils.py
```

Then perform one real manual validation on Windows:

```text
source URL + start + end → one short playable clip file under downloads/clips/...
```

Execution report must include:

- branch;
- commit SHA;
- files changed;
- test commands and results;
- real clip output path;
- file size;
- clip duration if available;
- whether this path downloaded/exported only the selected time range;
- remaining limitations.

## Known uncertainty

The helper code is stable and testable. The uncertain part is the exact installed `yt-dlp` Python API shape for selected time-range downloads.

The executor should verify that locally. If direct Python API support is awkward, use a small subprocess-based implementation for segment jobs only, while keeping the existing full-download worker path untouched.
