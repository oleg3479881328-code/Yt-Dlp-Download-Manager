# Quick Mix Anti-Duplicate Planner Report

Status: implemented as a safe isolated core planner branch.

Branch:
- `assistant/quick-mix-anti-duplicates`

Scope kept safe:
- Did not modify the current dashboard PR #52.
- Did not merge into `master`.
- Did not change current `/video-mix` dashboard behavior.
- Added a pure planner module and tests only.

Problem confirmed:
- The current Quick Mix generator can repeat visually duplicated source material because it selects assets by simple rotation.
- WhatsApp duplicate-export names like `Video.mp4`, `Video (1).mp4`, `Video (2).mp4` are treated as unrelated files by path-based `asset_id`.

Implemented:
- New `video_mix/core/quick_mix_planner.py`.
- New `tests/test_quick_mix_planner.py`.
- Source-group normalization that collapses WhatsApp-style numbered duplicate filenames.
- Per-output planning that prefers:
  1. unused base source id;
  2. unused normalized source group;
  3. warning-backed relaxed source group only if unique material is exhausted;
  4. warning-backed repeated source only as last resort.
- Explicit warning codes:
  - `quick_mix_unique_material_exhausted`
  - `quick_mix_source_group_relaxed`
  - `quick_mix_asset_repeat_relaxed`
- Planned segment metadata:
  - output index;
  - step index;
  - source id;
  - base source id;
  - source path;
  - source basename;
  - normalized source group;
  - media type;
  - source start/end;
  - relative source start;
  - duration;
  - warnings.

Tests added:
- WhatsApp filename variants collapse to one group.
- One output avoids same source and WhatsApp group when enough unique material exists.
- Planner reports `quick_mix_unique_material_exhausted` when it must repeat.
- Video offsets advance across outputs without reusing a source inside the same output when enough unique material exists.
- Empty source list is rejected.

Validation performed in this ChatGPT environment:
- Local syntax design was checked before committing the planner shape.
- Full project tests were not run because the execution environment here does not have the GitHub repo checkout or network access.

Remaining integration work:
- Wire `video_mix/core/quick_mix_planner.py` into `video_mix/service.py` inside `quick_mix_source_materials()`.
- Save the serialized plan to `reports/quick_mix_plan.json`.
- Include warning count and warnings in `reports/quick_mix.json` and the Quick Mix API response.
- Run:
  - `python -m pytest tests/test_quick_mix_planner.py tests/test_video_mix_pipeline.py tests/test_video_mix_dashboard_api.py -q`
  - `python -m ruff check video_mix/core/quick_mix_planner.py tests/test_quick_mix_planner.py video_mix/service.py`

Recommended next safe step:
- Let Codex wire this planner into `service.py` on this branch or a follow-up branch, then test with the real `quick_mix_004` source folder before merging.
