# 2026-06-20 — Science Video Assembly MVP decision and review fixes

## Trigger

Owner requested maximum progress on AI-assisted automation for educational / science-popular video creation, then asked for code drafts to make executor work easier.

## Owner Decision

A bounded `Science Video Assembly MVP` draft track is authorized inside this repository through PR `#3`.

This does not authorize automatic YouTube downloading for publication. The module must remain rights-aware and source-ledger-first.

## Scope

Allowed MVP path:

```text
short script
-> DeepSeek visual beats JSON
-> stock source candidates
-> DeepSeek candidate ranking JSON
-> manual approval file
-> timeline JSON
-> source ledger JSON
```

## Review Findings

Initial review found four issues:

1. canonical source-of-truth files still said only Phase 2 planning was allowed;
2. second stock provider adapter was still a placeholder;
3. Pexels candidate IDs could duplicate across multiple queries for the same beat;
4. tests were missing.

## Fixes Applied In PR #3

- `AGENTS.md`, `PROJECT_STATE.md`, `PROJECT_ENTRYPOINT.md`, and `PROJECT_RULES.md` were synchronized to make PR `#3` the active task.
- `science_assembly/sources/video_stock_b.py` now implements the second stock provider adapter while preserving the neutral draft filename.
- `science_assembly/cli.py` now supports `--provider pexels`, `--provider stock-b`, and `--provider all`.
- `science_assembly/sources/pexels.py` now uses a per-beat candidate counter so IDs remain unique across multiple queries.
- `tests/test_science_assembly_pipeline.py` adds minimal tests for offline provider, validation, approval, timeline, ledger, and duplicate candidate IDs.

## Current Next Action

Executor should run:

```powershell
python -m science_assembly.cli beats --script science_assembly/samples/photosynthesis_short_script.ru.txt --out outputs/science_assembly/demo --offline-demo
pytest -q tests/test_science_assembly_pipeline.py
```

Then return an execution report in PR `#3`.
