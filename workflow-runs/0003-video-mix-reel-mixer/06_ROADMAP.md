# 06_ROADMAP — VIDEO MIX

Date: 2026-06-26
Status: planning

## Purpose

Define the staged path for VIDEO MIX without overbuilding.

## Stage 0 — Planning Completed By Assistant

Goal:

- capture owner intent;
- define MVP scope;
- define architecture;
- define data model;
- define review rules;
- prepare future implementation boundary.

Status:

- active in this workflow run.

## Stage 1 — Local Batch MVP

Goal:

```text
local media folder -> candidate Reels -> approved MP4 exports
```

Required:

- local project folder scan;
- video metadata extraction;
- micro-clip generation;
- simple scoring;
- wedding pilot pack;
- 3–5 fixed templates;
- candidate list;
- approve/reject flow;
- export approved MP4.

Success:

- at least 10 candidates from one test folder;
- at least 3 approved exports;
- no raw media or exports committed.

## Stage 2 — Better Template Engine

Goal:

- stronger template rules;
- more pacing options;
- better reuse control;
- more visible variation;
- basic text overlay presets.

Do not start until Stage 1 validates.

## Stage 3 — Stronger Analysis

Goal:

- better scene understanding;
- stronger visual tagging;
- possible reuse of Video Content Analyzer ideas;
- better duplicate and similarity detection.

Do not start before the basic engine works.

## Stage 4 — More Industry Packs

Goal:

Add second and third packs after the core is proven.

Good candidates:

- real estate;
- car dealership;
- restaurant;
- event venue;
- product or gadget review.

The first new pack should require minimal core changes. If a new pack forces major core rewrites, the core-pack contract is wrong.

## Stage 5 — Production Workflow

Goal:

- batch project management;
- stronger review dashboard;
- export packages;
- metadata notes;
- analytics fields.

Publishing automation remains out of scope until explicitly approved.

## Assistant-Only Work Completed Or Possible

The assistant can complete:

- product brief;
- MVP scope;
- architecture plan;
- data model;
- pack schema;
- scoring rules;
- roadmap;
- future handoff packet;
- project-state synchronization.

## Requires Codex Later

Codex or a local coding agent is needed for:

- actual file creation under `video_mix/`;
- Python implementation;
- UI implementation;
- ffmpeg/ffprobe integration;
- local execution;
- rendering validation;
- execution report with real command outputs.

## Current Recommendation

Do not implement code until the owner confirms this planning package.

When implementation is approved, start with Stage 1 only.
