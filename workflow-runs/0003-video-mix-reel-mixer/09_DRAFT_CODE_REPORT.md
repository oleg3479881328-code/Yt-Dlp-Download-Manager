# 09_DRAFT_CODE_REPORT — VIDEO MIX

Date: 2026-06-26
Status: draft code created / not integrated / not validated

## Trigger

Owner asked the assistant to write draft code first so Codex has an easier implementation task later.

## Boundary

The draft code is stored under the workflow run, not in the active application module.

Path:

```text
workflow-runs/0003-video-mix-reel-mixer/draft-code/
```

This is intentional. It gives Codex a concrete starting point without claiming production implementation.

## Draft Files Created

```text
draft-code/README.md
draft-code/video_mix/__init__.py
draft-code/video_mix/cli.py
draft-code/video_mix/core/__init__.py
draft-code/video_mix/core/models.py
draft-code/video_mix/core/asset_scan.py
draft-code/video_mix/core/media_probe.py
draft-code/video_mix/core/clip_extract.py
draft-code/video_mix/core/scoring.py
draft-code/video_mix/core/tagging.py
draft-code/video_mix/core/candidate_builder.py
draft-code/video_mix/core/export_plan.py
draft-code/video_mix/packs/__init__.py
draft-code/video_mix/packs/wedding/__init__.py
draft-code/video_mix/packs/wedding/templates.py
draft-code/video_mix/packs/wedding/pack.txt
```

## Draft Capabilities

The draft includes:

- dataclass models;
- local media folder scan;
- ffprobe metadata wrapper;
- micro-clip planning;
- ffmpeg cut command builder;
- simple scoring;
- simple filename-based tag inference;
- candidate builder;
- export plan command builder;
- wedding pilot templates;
- CLI planning command.

## Not Done

- no local execution;
- no test media validation;
- no active app integration;
- no dashboard UI;
- no real export verification;
- no claim that VIDEO MIX works yet.

## Future Codex Use

Codex should treat this draft as a reference skeleton.

When Stage 1 is approved, Codex should adapt this code into the real module, run a local test, and write an execution report with real command output.

## Next Action

Review the draft code package. If approved, create a narrow Stage 1 implementation task for Codex/local coding agent.
