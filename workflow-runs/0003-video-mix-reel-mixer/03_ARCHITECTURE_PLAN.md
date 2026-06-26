# 03_ARCHITECTURE_PLAN — VIDEO MIX

Date: 2026-06-26
Status: planning

## Architecture Principle

Build a reusable `Reel Mixer Core` plus separate `Industry Packs`.

The core is industry-neutral. It should not contain wedding-specific assumptions.

The first wedding pilot is only a pack that proves the model.

## Proposed Folder Shape

```text
video_mix/
  README.md
  core/
    asset_scan.py
    media_probe.py
    clip_extract.py
    scoring.py
    duplicate_detection.py
    candidate_builder.py
    render_queue.py
    export.py
  packs/
    wedding/
      pack.yaml
      templates.yaml
      overlays.yaml
      scoring.yaml
  storage/
    schema.sql
  ui/
    routes.py
    static/
    templates/
```

This is a proposed implementation shape, not yet created in code.

## Core Pipeline

```text
project folder
→ scan media
→ probe metadata
→ extract thumbnails/keyframes
→ split into micro-clips
→ score clips
→ apply industry pack templates
→ generate candidate reel plans
→ preview candidates
→ approve/reject/regenerate
→ export approved MP4
```

## Core Modules

### 1. Asset Scan

Responsibilities:

- find supported video/photo files;
- assign stable asset IDs;
- record local paths;
- record media type;
- ignore unsupported files;
- keep raw media local.

### 2. Media Probe

Responsibilities:

- read duration;
- read resolution;
- read orientation;
- read fps;
- read audio presence;
- read codec basics;
- detect obviously broken files.

Likely tool:

- `ffprobe`.

### 3. Clip Extraction

Responsibilities:

- cut usable micro-clips from input video;
- preserve source asset reference and timestamps;
- avoid destructive edits;
- store extracted clips in local working output.

MVP strategy:

- fixed interval or scene-change assisted splitting;
- keep clips short: about 1.5–5 seconds;
- later improve with visual scene detection.

### 4. Scoring

Responsibilities:

- basic sharpness score;
- exposure/brightness sanity;
- motion/blur warning;
- duration fit;
- orientation fit;
- duplicate penalty;
- pack-specific score adjustments.

### 5. Candidate Builder

Responsibilities:

- load industry pack;
- load templates;
- select clips by tag/slot rules;
- avoid repeating the same clip too often;
- generate candidate reel plans before rendering.

Candidate plans should be JSON-like manifests, not only rendered files.

### 6. Preview and Review

Responsibilities:

- show candidate list/grid;
- show duration, score and template name;
- allow approve/reject/regenerate;
- prevent blind mass export.

### 7. Export

Responsibilities:

- render approved candidates;
- output MP4;
- use vertical 9:16 defaults;
- keep naming deterministic;
- write export report.

## Integration With Existing Project

Reuse where useful:

- `ffmpeg` / `ffprobe` assumptions from existing downloader stack;
- local dashboard pattern;
- SQLite state pattern;
- Remotion rendering experience from `subtitle_studio` if template rendering becomes visual/text-heavy;
- future `Video Content Analyzer` ideas only after MVP needs stronger scene understanding.

Do not rewrite:

- existing downloader runtime;
- Chrome extension/native host;
- subtitle studio internals unless needed by the active task.

## Industry Pack Contract

Each pack should define:

- pack name;
- supported scene tags;
- clip slot types;
- templates;
- scoring weights;
- overlay presets;
- CTA presets;
- export naming rules.

The wedding pack is the first implementation of this contract.

## MVP Technical Bias

Prefer simple local deterministic processing first.

Use AI only where it adds obvious value after the basic pipeline works.

The first MVP should prove batch assembly, not perfect automated creative judgment.

## Risks

### RISK-VMIX-001 — Overbuilding

The module can easily become a full editor or SaaS. MVP must stay local and narrow.

### RISK-VMIX-002 — Bad automatic choices

Automatic mixing may produce awkward edits. Human review gate is required.

### RISK-VMIX-003 — Duplicate outputs

Many generated reels may feel too similar. Candidate generation must track source reuse.

### RISK-VMIX-004 — Hardcoded wedding logic

The first pilot can contaminate the core. Wedding-specific rules must stay in `packs/wedding/`.

### RISK-VMIX-005 — Source media privacy

User media and exports must remain local and out of GitHub.

## Next Action

Define the data model and pack schema.
