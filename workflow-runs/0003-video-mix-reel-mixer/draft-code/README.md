# VIDEO MIX draft code

Status: draft only / not integrated / not validated

This folder contains assistant-written draft code for the future `VIDEO MIX` Stage 1 implementation.

It is intentionally stored under the workflow run, not as active production code.

Goal: make Codex implementation easier by providing a concrete starting skeleton.

## Draft shape

```text
draft-code/
  README.md
  video_mix/
    __init__.py
    cli.py
    core/
      __init__.py
      models.py
      asset_scan.py
      media_probe.py
      clip_extract.py
      scoring.py
      candidate_builder.py
      export_plan.py
    packs/
      wedding/
        pack.yaml
```

## How Codex should use this

1. Read planning docs in `workflow-runs/0003-video-mix-reel-mixer/`.
2. Treat this folder as a draft reference, not final architecture.
3. Move/adapt code into the real module only after owner approval.
4. Validate with real local media before claiming the module works.

## Hard boundaries

- Do not commit source media.
- Do not commit derived clips.
- Do not commit exported MP4 files.
- Do not wire this into the existing app until Stage 1 implementation is approved.
