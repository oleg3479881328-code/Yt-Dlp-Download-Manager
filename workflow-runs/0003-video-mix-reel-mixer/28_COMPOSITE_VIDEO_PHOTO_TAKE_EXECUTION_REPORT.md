# Composite Video Photo Take Execution Report

Status: review-ready

Task source:
- GitHub Issue `#58`
- PR `#60`
- owner review comment:
  - `https://github.com/oleg3479881328-code/Yt-Dlp-Download-Manager/pull/60#issuecomment-5002828852`

Branch:
- `codex/issue-58-composite-takes`

Base branch:
- `codex/issue-41-source-materials-loading`

## 1. Scope of this follow-up pass

This pass fixes two critical composite Quick Mix problems on top of the existing `video_photo_composite` PR:

1. atomic composite planning
2. canonical composite content identity across generation history and max-diversity

No work from Issue `#59` was started.

## 2. Delivered behavior

### 2.1 Atomic composite planning

`video_photo_composite` is now treated as a strictly atomic body unit:

- planner never creates a partial composite segment
- composite body segment always has:
  - `source_start_ms = 0`
  - `duration_ms = atomic_duration_ms`
- composite is selected only when the full unit fits inside the available body duration
- when it does not fit, planner selects another eligible Take if one exists
- when no eligible fallback exists, the flow returns explicit exhaustion instead of partial planning or hidden overshoot

### 2.2 Stable composite content identity

Composite body uniqueness now uses canonical content identity built from:

- `video_asset_id`
- ordered `photo_asset_ids`
- `photo_duration_ms`
- `photo_motion_mode`

Format:

```text
composite:<sha256(canonical-json)>
```

Canonical JSON is generated from a stable payload with sorted keys and preserved photo order.

Effects:

- different Take IDs with identical composite content are treated as the same body content
- changing photo order changes identity
- changing `photo_duration_ms` changes identity
- changing `static` <-> `ken_burns` changes identity
- music / opening / closing still do not participate in body uniqueness

## 3. Changed files

- `tests/test_quick_mix_diversity.py`
- `tests/test_quick_mix_diversity_adapter.py`
- `tests/test_quick_mix_generation.py`
- `tests/test_quick_mix_planner.py`
- `tests/test_video_mix_pipeline.py`
- `video_mix/core/quick_mix_diversity_adapter.py`
- `video_mix/core/quick_mix_diversity_candidates.py`
- `video_mix/core/quick_mix_diversity_models.py`
- `video_mix/core/quick_mix_diversity_selection.py`
- `video_mix/core/quick_mix_generation.py`
- `video_mix/core/quick_mix_planner.py`
- `video_mix/service.py`

## 4. Implementation details

### 4.1 Planner

`preferred_quick_mix_segment_ms(...)` now returns:

- full atomic duration for atomic composite that fits
- `0` for atomic composite that does not fit

This removes the old partial behavior equivalent to:

```python
min(remaining_ms, atomic_duration_ms)
```

`plan_quick_mix_segment(...)` now pins atomic composite windows to:

- `relative_source_start_ms = 0`
- `source_start_ms = source.source_start_ms`
- `duration_ms = atomic_duration_ms`

### 4.2 Exhaustion behavior

When only non-fitting atomic composite content remains:

- planner-level flow returns `quick_mix_atomic_take_exhausted`
- diversity adapter flow returns empty batch plus explicit exhaustion warning
- no partial composite segment is emitted
- no MP4 overshoot is planned

### 4.3 History / max-diversity restoration

Generation manifests now persist composite `content_identity`.

`load_prior_diversity_plans()` restores that identity into prior body signatures, so cross-generation max-diversity compares composite body content by canonical identity instead of only by Take ID or render window.

## 5. Regression coverage

Added or extended regression coverage for:

1. non-fitting `5400 ms` composite is not planned as a `2000 ms` partial segment
2. atomic composite segment keeps full duration
3. planner chooses another Take when composite does not fit
4. planner returns exhaustion when no fallback exists
5. generated plan preserves composite full duration and content identity
6. identical composite content under different Take IDs is rejected as duplicate body content
7. changed composite identity is not rejected as the same body content
8. generation manifest stores `content_identity`
9. prior generation history restores `content_identity`
10. second generation sees prior composite identity in max-diversity history

## 6. Validation commands

Executed on Windows in the issue worktree:

```powershell
pytest -q
ruff check app tests video_mix
node --test frontend-tests\video-mix-dashboard.test.mjs
node --check app\static\video-mix-dashboard.js
```

Observed:

- `pytest -q` -> `148 passed, 1 warning`
- `ruff check app tests video_mix` -> clean
- `node --test frontend-tests\video-mix-dashboard.test.mjs` -> `6 passed`
- `node --check app\static\video-mix-dashboard.js` -> clean

Pytest warning:

- `tests/test_video_mix_zip_intake.py::test_zip_rejects_duplicate_normalized_destinations`
- underlying Python `zipfile` duplicate-name warning only

## 7. Local HTTP smoke

Verified with temporary local uvicorn run:

- `/video-mix?lang=ru` -> HTTP `200`
- `/` -> HTTP `200`

## 8. Real-media smoke

Smoke summary root:

- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_atomic_smoke_rerun2`

Summary artifact:

- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_atomic_smoke_rerun2\summary.json`

### 8.1 Static composite

Output:

- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_atomic_smoke_rerun2\work_static\quick_mix_generations\quick_mix_20260717T125029561557Z\exports\quick_mix_001.mp4`

Requested duration:

- `5.4s`

Actual `ffprobe` duration:

- `5.400000`

Plan evidence:

- `selected_take_ids = ["composite_take_a"]`
- `body_visual_signature = ["composite:770de51874cedd4df84667e07d9886c7cc578bfb9cb564b739c66462ac1143e6"]`
- `generated_duration_ms = 5400`

Visual order probes:

- `t=0.5s` -> blue video frame
- `t=3.2s` -> first red photo frame
- `t=4.5s` -> second green photo frame

### 8.2 Ken Burns composite

Output:

- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_atomic_smoke_rerun2\work_ken_burns\quick_mix_generations\quick_mix_20260717T125031340318Z\exports\quick_mix_001.mp4`

Requested duration:

- `5.4s`

Actual `ffprobe` duration:

- `5.400000`

Plan evidence:

- `selected_take_ids = ["composite_take_a"]`
- `body_visual_signature = ["composite:db3669c33de394b1731d1fe2864eb4d4f20beba7e9cbef0e9fb6a507d1226005"]`
- `generated_duration_ms = 5400`

Visual order probes:

- `t=0.5s` -> blue video frame
- `t=3.2s` -> first red photo frame
- `t=4.5s` -> second green photo frame

### 8.3 Short-fallback proof: no partial composite

Output:

- `C:\Users\oleg3\OneDrive\Documents\Yt-Dlp-Download-Manager-issue58\tmp\issue58_atomic_smoke_rerun2\work_short_fallback\quick_mix_generations\quick_mix_20260717T125033199260Z\exports\quick_mix_001.mp4`

Requested duration:

- `2.0s`

Actual `ffprobe` duration:

- `2.000000`

Selected body:

- `selected_take_ids = ["fallback_short_take"]`

Interpretation:

- non-fitting `5400 ms` composite was not partially planned
- planner selected non-composite fallback content instead

### 8.4 Atomic exhaustion proof

Atomic exhaustion scenario produced:

- `generated_count = 0`
- warning codes include:
  - `quick_mix_atomic_take_exhausted`
  - `quick_mix_diversity_exhausted`

Atomic warning payload includes:

- `requested_output_count = 1`
- `achieved_output_count = 0`
- `target_duration_ms = 2000`
- `blocked_source_ids = ["composite_take_a"]`

Interpretation:

- when only non-fitting atomic composite remains, the system now returns explicit exhaustion instead of partial segment or overshoot

### 8.5 Cross-generation duplicate detection proof

History scenario:

- first generation selected:
  - `selected_take_ids = ["composite_take_b"]`
  - `body_visual_signature = ["composite:770de51874cedd4df84667e07d9886c7cc578bfb9cb564b739c66462ac1143e6"]`
- second generation achieved:
  - `generated_count = 0`
- second-generation warning reasons include:
  - `exact_take_duplicate = 1`

Interpretation:

- restored generation history recognized already-used composite body content
- second run did not silently reuse the same composite content

## 9. Boundaries preserved

Still not changed in this pass:

- no Issue `#59` work
- no random photo selection
- no per-photo individual duration
- no base-video trimming UI
- no rendered-output trimming as a workaround for planner mismatch
- no force-push
- no merge

## 10. Ready for review

Ready for review:
- Yes
