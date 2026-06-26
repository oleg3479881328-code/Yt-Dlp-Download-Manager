# 07_FUTURE_HANDOFF — VIDEO MIX

Date: 2026-06-26
Status: revised after deep donor research / not authorized for execution yet

## Boundary

This note prepares a future coding handoff only.

It does not authorize implementation.

Codex must not treat the draft code as finished implementation. It is reference material.

## Required Read Order

1. `PROJECT_ENTRYPOINT.md`
2. `PROJECT_STATE.md`
3. `PROJECT_RULES.md`
4. `logs/PROJECT_LOG.md`
5. `workflow-runs/0003-video-mix-reel-mixer/11_DEEP_DONOR_RESEARCH_PRODUCTION_ENGINE.md`
6. `workflow-runs/0003-video-mix-reel-mixer/12_DRAFT_CODE_REVISION_REPORT.md`
7. `workflow-runs/0003-video-mix-reel-mixer/01_OWNER_BRIEF.md`
8. `workflow-runs/0003-video-mix-reel-mixer/02_MVP_SCOPE.md`
9. `workflow-runs/0003-video-mix-reel-mixer/03_ARCHITECTURE_PLAN.md`
10. `workflow-runs/0003-video-mix-reel-mixer/04_DATA_MODEL_AND_PACK_SCHEMA.md`
11. `workflow-runs/0003-video-mix-reel-mixer/05_REVIEW_RULES.md`
12. `workflow-runs/0003-video-mix-reel-mixer/06_ROADMAP.md`
13. `workflow-runs/0003-video-mix-reel-mixer/draft-code/`

## Future Goal

Implement Stage 1 only:

```text
one local production folder -> many candidate reels -> approved MP4 exports
```

This must remain a general production combiner, not a wedding-only editor.

## Stage 1 Technical Direction

Use:

- Python orchestration;
- ffprobe metadata probing;
- ffmpeg cutting/export;
- candidate manifests before rendering;
- local reports;
- human review gate.

Do not add hard AI dependency in Stage 1.

## Architecture Requirements

1. Keep `Reel Mixer Core` industry-neutral.
2. Keep pilot-specific logic in industry packs.
3. Use pluggable segmentation:
   - fixed interval fallback now;
   - PySceneDetect option later or if cheap to validate.
4. Use timeline-like candidate manifests:
   - tracks;
   - clips;
   - source references;
   - overlays;
   - render settings;
   - review status.
5. Keep render layer modular:
   - Stage 1 ffmpeg export;
   - Stage 2 Remotion branded rendering.
6. Add duplicate/reuse logic:
   - simple same-source penalty now;
   - perceptual hash later.

## Constraints

- local-first;
- no public product work;
- no external publishing features;
- no raw media or exports in GitHub;
- no unrelated downloader refactor;
- no hardcoded wedding core;
- no GPU generation requirement;
- no social account login or auto-posting.

## Proposed Deliverables

1. Move/adapt draft code into real `video_mix/` module.
2. Keep package boundaries from draft unless repository reality requires changes.
3. Implement local project scan.
4. Implement ffprobe metadata wrapper.
5. Implement pluggable segmentation interface.
6. Implement fixed interval segmenter as Stage 1 fallback.
7. Leave PySceneDetect adapter behind a safe optional flag unless validated.
8. Implement basic duplicate/reuse detection.
9. Implement pack/template loading.
10. Implement timeline-like candidate manifests.
11. Implement approve/reject metadata.
12. Implement approved MP4 export with ffmpeg.
13. Write execution report.

## Validation Required

Future implementation must run a real local test and report:

- commands used;
- input count;
- asset count;
- clip count;
- candidate count;
- approved export count;
- output filenames and sizes;
- warnings and failures;
- confirmation that raw media and exports are not committed.

## Definition Of Done

Stage 1 is done only when:

- code exists in the real module;
- a local test was executed;
- at least one export succeeded;
- an execution report is committed;
- project state is updated;
- raw media, generated clips and exports are not committed.
