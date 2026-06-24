# Science Video Assembly MVP — Architecture

- Date: 2026-06-20
- Status: proposed architecture
- Scope: MVP planning for implementation handoff

## Goal

Build an AI-assisted local workflow that helps create educational / science-popular videos from a topic or script by turning the script into visual beats, finding allowed B-roll candidates, ranking them, producing a reviewable timeline, and rendering a preview.

The workflow must be rights-aware and source-ledger-first.

## High-Level System

```text
User topic or draft script
  -> AI Script Planner
  -> AI Visual Beat Extractor
  -> Source Search Adapters
  -> Candidate Normalizer
  -> AI Candidate Ranker
  -> Human Approval Gate
  -> Timeline Builder
  -> Preview Renderer
  -> QA / Source Ledger Export
```

## Components

### 1. AI Provider Abstraction

Purpose:

- keep DeepSeek as the first supported provider;
- avoid hard-coding the system to one vendor;
- allow later OpenAI / Anthropic / local model providers.

Environment variables:

```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=
AI_MODEL_FAST=deepseek-v4-flash
AI_MODEL_REASONING=deepseek-v4-pro
AI_JSON_MODE=true
```

Initial provider tasks:

- `generate_script_outline(topic)`
- `expand_script(outline, duration_minutes)`
- `extract_visual_beats(script)`
- `generate_source_queries(visual_beat)`
- `rank_source_candidates(visual_beat, candidates)`
- `create_timeline(approved_clips, script_segments)`
- `qa_review(timeline, source_ledger)`

Implementation rule:

- AI returns structured JSON.
- AI never downloads, cuts, renders, or publishes files.
- Local application executes tools.

### 2. Script Planner

Input options:

- topic only;
- topic + audience level;
- existing script;
- target duration.

MVP-1 accepted input:

- existing short script of 1–2 minutes;
- or topic -> short script generated for testing.

Output:

- `script_segments[]` with approximate timing.

### 3. Visual Beat Extractor

Purpose:

Convert script into visual needs.

Example:

```json
{
  "beat_id": "beat_004",
  "script_segment_id": "seg_004",
  "narration_text": "Inside the leaf, chloroplasts capture light energy.",
  "visual_need": "microscope view of chloroplasts inside leaf cells",
  "search_queries": [
    "chloroplast microscope leaf cells",
    "plant cells chloroplasts close up",
    "photosynthesis chloroplast animation"
  ],
  "preferred_style": "real footage or clean educational animation",
  "duration_seconds": 8,
  "required_rights_status": "allowed_or_reviewed"
}
```

### 4. Source Search Adapters

MVP-1 adapters:

- Pexels video search;
- Pixabay video search;
- local folder media search by filename/metadata if practical.

Optional later adapters:

- licensed paid stock provider;
- owner-owned media library;
- Twelve Labs / VideoDB semantic video library;
- YouTube reference/embedding only where allowed.

Each adapter must return normalized `source_candidate` objects.

### 5. Candidate Normalizer

Normalize all sources into one shape:

- source provider;
- source URL;
- preview URL / thumbnail;
- downloadable asset URL where allowed;
- creator/channel/author;
- license / terms note;
- dimensions;
- duration;
- tags;
- query that found it;
- raw provider payload.

### 6. AI Candidate Ranker

Input:

- visual beat;
- candidate list;
- license/rights notes;
- technical metadata.

Output:

- ranked candidate list;
- confidence;
- mismatch warnings;
- why selected;
- review questions for user.

Rules:

- rank relevance and usability separately;
- never override `rights_status`;
- if rights are unclear, mark `needs_review`.

### 7. Human Approval Gate

MVP-1 is not fully automatic.

The app must require explicit approval before a candidate enters the timeline.

Approval state:

- `pending_review`
- `approved`
- `rejected`
- `needs_rights_review`
- `replace_needed`

### 8. Timeline Builder

Purpose:

Convert approved beats and candidates into renderable timeline JSON.

Timeline includes:

- narration segments;
- visual clip references;
- start/end times inside source if clipping is supported;
- placement on timeline;
- captions;
- source ledger references;
- render notes.

### 9. Preview Renderer

MVP-1 options:

- ffmpeg-only preview: simplest possible concatenation/overlay test;
- Remotion preview: preferred if reusing subtitle studio patterns is practical.

Recommendation:

- Start with JSON-only + source ledger output.
- Add preview render only after the schema is stable.
- If rendering is included in MVP-1, prefer a minimal Remotion template if executor can safely isolate it from accepted subtitle work.

### 10. Source Ledger

Every external visual asset must be tracked.

Ledger fields:

- asset ID;
- provider;
- source URL;
- creator;
- license / terms URL;
- query;
- date accessed;
- selected for beat ID;
- review status;
- notes;
- downloaded local path if permitted;
- final usage decision.

## Data Flow

```text
script.md
  -> script_segments.json
  -> visual_beats.json
  -> source_candidates.json
  -> ranked_candidates.json
  -> approved_clips.json
  -> timeline.json
  -> source_ledger.csv/json
  -> preview.mp4 optional
```

## Storage Layout Proposal

```text
workflow-runs/0003-science-video-assembly-mvp/
  00_DISCOVERY_REVIEW.md
  01_ARCHITECTURE.md
  02_JSON_SCHEMAS.md
  03_IMPLEMENTATION_HANDOFF_PACKET.md

science_assembly/
  __init__.py
  ai/
    provider.py
    deepseek_provider.py
    prompts.py
  sources/
    pexels.py
    pixabay.py
    local_library.py
  schemas/
    visual_beat.schema.json
    source_candidate.schema.json
    timeline.schema.json
  render/
    timeline_to_ffmpeg.py
    remotion_export_bridge.md
  cli.py
```

This layout is a proposal for implementation; do not create it until an implementation task is accepted.

## Safety / Rights Boundary

YouTube content must not be automatically downloaded and republished unless rights are explicitly confirmed.

Allowed source classes for MVP-1:

- Pexels/Pixabay assets returned through their APIs, subject to their active terms;
- user-owned local media;
- manually approved licensed media;
- public domain / Creative Commons assets after metadata capture;
- YouTube embed/reference only, unless rights and platform permission are confirmed.

## MVP-1 Acceptance Criteria

1. A 1–2 minute script can be converted into at least 5 visual beats.
2. Each beat gets 3–10 candidate B-roll results from Pexels/Pixabay or local media.
3. DeepSeek ranks candidates with reasons and warnings.
4. User can approve/reject candidates, at least through a JSON/manual file workflow if no UI is built.
5. Approved candidates generate a valid `timeline.json`.
6. Source ledger is generated and includes provider, URL, rights status, and accessed date.
7. No automatic YouTube downloading is implemented in MVP-1.
8. The executor returns a concise validation report with commands, outputs, and known limitations.

## Non-Goals

- full 10-minute production quality video;
- direct YouTube scraping for publication;
- automatic publishing;
- accounts / billing / SaaS productization;
- multi-user collaboration;
- perfect visual matching;
- paid stock integration;
- Twelve Labs / VideoDB production integration.

## Recommended First Implementation Path

1. Create schemas and sample fixture.
2. Add DeepSeek provider wrapper with JSON mode.
3. Implement `extract_visual_beats` on a sample script.
4. Implement Pexels/Pixabay search adapters.
5. Implement candidate normalization and ranking.
6. Create manual approval file.
7. Generate `timeline.json` and `source_ledger.json`.
8. Only then add preview render.
