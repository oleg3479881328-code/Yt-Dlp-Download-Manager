# 12_DRAFT_CODE_REVISION_REPORT — VIDEO MIX

Date: 2026-06-26
Status: draft code revised after deep donor research / not integrated / not validated

## Trigger

Owner agreed with the deep donor research direction and asked what should happen next.

The correct next step was to revise the assistant-written draft code before any Codex implementation approval.

## What Changed

Draft code path:

```text
workflow-runs/0003-video-mix-reel-mixer/draft-code/
```

Updated draft files:

- `video_mix/core/models.py`
- `video_mix/core/candidate_builder.py`
- `video_mix/core/export_plan.py`
- `video_mix/cli.py`

New draft files:

- `video_mix/core/segmenters.py`
- `video_mix/core/duplicate_detection.py`

Updated handoff:

- `07_FUTURE_HANDOFF.md`

## Main Revision Decisions

### 1. CandidateReel became timeline-like

Old draft:

```text
CandidateReel -> list of CandidateClip
```

Revised draft:

```text
CandidateReel -> tracks -> timeline clips / overlays
```

This better matches donor research around timeline manifests and future OpenTimelineIO-style thinking.

### 2. Segmentation became pluggable

Old draft:

```text
fixed 3-second cuts only
```

Revised draft:

```text
Segmenter interface
├── FixedIntervalSegmenter fallback
└── PySceneDetectSegmenter placeholder
```

PySceneDetect is not forced into Stage 1, but the code now has a safe adapter slot.

### 3. Duplicate detection got a placeholder layer

Added:

- existing perceptual hash grouping placeholder;
- same-source overuse grouping;
- reuse penalty support through `duplicate_group_id`.

Real perceptual hash should be added later with imagehash/frame sampling.

### 4. Export now reads timeline manifests

Export planning now uses `candidate.video_clips` from tracks instead of assuming a flat clip list.

### 5. CLI now reflects the donor-research pipeline

Draft CLI now runs:

```text
scan assets
→ probe metadata
→ score assets
→ segment clips
→ tag clips
→ duplicate/reuse detection
→ score clips
→ build candidates
→ write local reports
```

No export is claimed as validated.

## Still Not Done

- no active module integration;
- no local execution;
- no ffmpeg render validation;
- no UI/dashboard;
- no real PySceneDetect parsing;
- no real perceptual hash frame sampling;
- no OpenCV quality scoring;
- no Remotion branded rendering.

## Current Recommendation

Now the draft is much safer for Codex.

Next step should be one narrow Stage 1 implementation task, but only after owner approval.

Codex should adapt this revised draft into the real module and run a local validation with test media.
