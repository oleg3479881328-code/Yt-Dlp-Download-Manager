# 01_OWNER_BRIEF — VIDEO MIX / Reel Mixer Engine

Date: 2026-06-26
Status: owner direction captured / planning active
Repository: `oleg3479881328-code/Yt-Dlp-Download-Manager`
Issue: `#20 VIDEO MIX — scalable reels mixer engine with wedding photographer pilot`

## Owner Direction

The owner wants a local system for mass creation of short vertical Reels from existing media materials.

First pilot vertical: wedding photographer.

Typical input:

- 20–30 backstage videos and/or photos;
- local project folder;
- optional brand assets, text overlays and music.

Target output:

- many candidate vertical Reels;
- usually 15–35 seconds;
- preview before export;
- export only approved MP4 files.

## Key Product Decision

Wedding photography is only the first pilot pack.

The system must be built as a scalable `Reel Mixer Engine` that can later support other industries through separate industry packs.

## Module Placement

`VIDEO MIX` belongs inside `Yt-Dlp-Download-Manager`.

It must not become a separate competing video project.

## Core / Pack Separation

```text
VIDEO MIX
├── Reel Mixer Core
│   └── industry-neutral asset, clip, template, candidate and export engine
└── Industry Packs
    └── vertical-specific labels, templates, pacing, scoring, overlays and CTA rules
```

The core must not be hardcoded to the wedding scenario.

The wedding pack is only the first validation surface.

## Future Pack Examples

- wedding photographer;
- real estate;
- car dealership;
- restaurant;
- event venue;
- travel;
- product/gadget review;
- fitness;
- beauty salon;
- contractor / before-after services.

## First MVP Goal

```text
local media folder
→ asset scan
→ micro-clip extraction
→ basic quality and duplicate scoring
→ fixed templates
→ 10–20 candidate reels
→ preview list/grid
→ approve/reject
→ export approved MP4 files
```

## Boundary

Assistant should complete all planning, architecture, scope control and handoff preparation possible directly.

Codex should receive only the future implementation work that requires code changes or local execution.

## Current State

- owner direction: confirmed;
- issue: created as `#20`;
- planning artifacts: being created in this workflow run;
- implementation: not started;
- validation: not performed.
