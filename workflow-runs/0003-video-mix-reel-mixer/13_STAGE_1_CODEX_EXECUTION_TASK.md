# 13_STAGE_1_CODEX_EXECUTION_TASK — VIDEO MIX

Date: 2026-06-26
Status: authorized task packet for Codex/local coding agent

## Task Title

VIDEO MIX Stage 1 — Local Production Combiner MVP

## Communication Channel

Primary execution channel:

- GitHub Issue created from this task packet.

The executor must use that Issue as the single coordination thread.

The executor must also create a PR for code changes and link it in the Issue.

## Owner Communication Protocol

The owner does not want repeated clarification questions.

The owner may write a short command in ChatGPT:

```text
0-2 проверь ответ
```

Meaning:

- ChatGPT must check the latest executor response in the GitHub Issue or PR;
- ChatGPT must review whether the executor followed the task;
- ChatGPT must tell the owner whether to accept, correct, or push back;
- ChatGPT must post the needed response back to GitHub if required.

The executor must understand that silence from the owner is not permission to stop.

## No-Ask Rule

The executor must not ask:

- Should I start?
- Do you want me to do this?
- Should I implement Stage 1?
- Should I create the files?
- Should I run validation?

This issue is the authorization to execute Stage 1.

If a decision is already defined in the task packet, execute it.

If something is ambiguous but not blocking, make a reasonable MVP decision, record it in the execution report, and continue.

Only ask in the Issue if there is a true blocker that prevents execution.

## Required Read Order

Before changing code, read:

1. `PROJECT_ENTRYPOINT.md`
2. `PROJECT_STATE.md`
3. `PROJECT_RULES.md`
4. `logs/PROJECT_LOG.md`
5. `workflow-runs/0003-video-mix-reel-mixer/11_DEEP_DONOR_RESEARCH_PRODUCTION_ENGINE.md`
6. `workflow-runs/0003-video-mix-reel-mixer/12_DRAFT_CODE_REVISION_REPORT.md`
7. `workflow-runs/0003-video-mix-reel-mixer/07_FUTURE_HANDOFF.md`
8. `workflow-runs/0003-video-mix-reel-mixer/draft-code/`

## Mission

Implement Stage 1 only:

```text
one local production folder
→ scan media
→ probe metadata
→ segment clips
→ create timeline candidate manifests
→ approve/reject metadata
→ export approved MP4 files
→ execution report
```

This must remain a general production combiner, not a wedding-only editor.

Wedding is the first pilot pack only.

## Scope

Create a real module:

```text
video_mix/
```

Use the revised draft code as a starting point, but adapt it to repository reality.

The draft code is located at:

```text
workflow-runs/0003-video-mix-reel-mixer/draft-code/
```

## Required Architecture

The implementation must keep:

```text
Reel Mixer Core + Industry Packs
```

Core must be industry-neutral.

Pilot-specific logic must stay in a pack.

Required module shape may be adjusted, but should stay close to:

```text
video_mix/
  __init__.py
  cli.py
  core/
    models.py
    asset_scan.py
    media_probe.py
    segmenters.py
    duplicate_detection.py
    scoring.py
    tagging.py
    candidate_builder.py
    export_plan.py
  packs/
    wedding/
      templates.py
      pack.txt or pack.yaml
```

## Stage 1 Technical Stack

Use:

- Python;
- ffprobe;
- ffmpeg;
- local JSON reports or SQLite if already easy in repository;
- timeline-like candidate manifests;
- simple approve/reject metadata;
- ffmpeg export for approved candidates.

Do not add hard AI dependency in Stage 1.

## Segmentation Requirement

Do not hardcode only naive fixed 3-second cuts as the permanent architecture.

Implement pluggable segmentation:

- fixed interval segmenter as working Stage 1 fallback;
- PySceneDetect adapter placeholder or optional implementation if simple and validated.

If PySceneDetect is not installed or not validated, do not fail Stage 1. Fall back to fixed interval and record this in the execution report.

## Candidate Manifest Requirement

Candidate Reels must be represented as timeline-like manifests before rendering.

Manifest should include:

- candidate id;
- project id;
- pack id;
- template id;
- status;
- score;
- duration;
- tracks;
- timeline clips;
- source asset references;
- source timestamps;
- timeline timestamps;
- overlays if present;
- render/platform settings;
- warnings;
- review status.

## Review Gate Requirement

Do not mass-export blindly.

Stage 1 must support at least simple metadata state:

```text
generated -> approved/rejected -> exported only if approved
```

A CLI command or report-based approval mechanism is acceptable for Stage 1.

A full dashboard UI is not required for Stage 1.

## Export Requirement

Export approved candidates as MP4 using ffmpeg.

Default preset:

```text
aspect ratio: 9:16
resolution: 1080x1920
fps: 30
format: mp4
```

The export layer must be modular so Remotion can be added later for branded templates.

## Do Not Build

Do not build:

- public SaaS;
- social posting automation;
- account login;
- GPU generation;
- full editor timeline UI;
- industry marketplace;
- multiple industry packs beyond the pilot;
- CLIP/OpenCLIP tagging;
- YOLO integration;
- Remotion branded rendering;
- unrelated downloader refactors.

## Privacy / Git Rules

Do not commit:

- source media;
- derived clips;
- rendered MP4 exports;
- local databases;
- private local paths containing user media;
- large generated artifacts.

Update `.gitignore` if needed.

## Minimum CLI Expectations

Implement a simple CLI or equivalent local entrypoint.

Suggested commands:

```text
python -m video_mix.cli plan <project_folder>
python -m video_mix.cli approve <work_dir> <candidate_id>
python -m video_mix.cli export <work_dir>
```

Equivalent commands are acceptable if documented.

## Required Validation

Run a real local validation.

If no owner media is available, generate or use safe tiny synthetic test media locally. Do not commit the generated media or MP4 exports.

Validation must prove:

- project folder scan works;
- media probe runs;
- segments are planned or generated;
- candidate manifests are created;
- at least one candidate can be approved;
- at least one MP4 export succeeds;
- raw media and exports are not committed.

## Required Execution Report

Create:

```text
workflow-runs/0003-video-mix-reel-mixer/14_STAGE_1_EXECUTION_REPORT.md
```

Report must include:

- status;
- files changed;
- commands run;
- input media count;
- asset count;
- clip count;
- candidate count;
- approved candidate count;
- exported MP4 count;
- output filenames and sizes, without committing outputs;
- warnings;
- failures;
- known limitations;
- exact next action.

## PR Requirement

Create a PR after implementation.

The PR body must include:

- link to the execution Issue;
- link to `14_STAGE_1_EXECUTION_REPORT.md`;
- summary of implementation;
- validation commands;
- what was not done;
- risks.

## Completion Rule

Do not mark the task complete until:

- code exists in `video_mix/`;
- local validation was run;
- at least one MP4 export succeeded;
- execution report exists;
- PR exists and is linked in the Issue;
- project state is updated.

## First Executor Comment Required

The executor's first Issue comment must be exactly a short start confirmation, not a question.

Required format:

```text
STARTED
I will execute Stage 1 according to this Issue. I will not ask for confirmation unless blocked. Next update will include implementation progress or blocker evidence.
```

Then start implementation immediately.

## If Blocked

If truly blocked, post:

```text
BLOCKED
Reason:
Evidence:
What I tried:
What decision is required:
Recommended default:
```

Do not use vague blocker messages.

## Final Executor Comment Required

When finished, post:

```text
READY FOR REVIEW
PR:
Execution report:
Validation summary:
Known limitations:
Next recommended action:
```

Do not close the Issue yourself unless explicitly instructed.
