# 07_FUTURE_HANDOFF — VIDEO MIX

Date: 2026-06-26
Status: prepared / not authorized for execution yet

## Boundary

This note prepares a future coding handoff only.

It does not authorize implementation.

## Read Order

1. `PROJECT_ENTRYPOINT.md`
2. `PROJECT_STATE.md`
3. `PROJECT_RULES.md`
4. `logs/PROJECT_LOG.md`
5. `workflow-runs/0003-video-mix-reel-mixer/01_OWNER_BRIEF.md`
6. `workflow-runs/0003-video-mix-reel-mixer/02_MVP_SCOPE.md`
7. `workflow-runs/0003-video-mix-reel-mixer/03_ARCHITECTURE_PLAN.md`
8. `workflow-runs/0003-video-mix-reel-mixer/04_DATA_MODEL_AND_PACK_SCHEMA.md`
9. `workflow-runs/0003-video-mix-reel-mixer/05_REVIEW_RULES.md`
10. `workflow-runs/0003-video-mix-reel-mixer/06_ROADMAP.md`

## Future Goal

Implement Stage 1 only:

```text
local media folder -> candidate Reels -> approved MP4 exports
```

## Constraints

- local-first;
- no public product work;
- no external publishing features;
- no raw media or exports in GitHub;
- do not rewrite unrelated downloader code;
- do not hardcode the core to the pilot industry.

## Proposed Deliverables

1. `video_mix/` module skeleton.
2. Local project scan.
3. ffprobe metadata wrapper.
4. ffmpeg micro-clip extraction.
5. Local metadata storage.
6. First wedding pack config.
7. 3–5 fixed templates.
8. Candidate reel manifests.
9. Approve/reject metadata.
10. Export approved candidates as MP4.
11. Execution report.

## Validation Required

Future implementation must report:

- commands used;
- input count;
- asset count;
- clip count;
- candidate count;
- approved export count;
- output filenames and sizes;
- warnings and failures.

## Definition Of Done

Stage 1 is done only when code exists, a local test was executed, at least one export succeeded, and the execution report is committed.
