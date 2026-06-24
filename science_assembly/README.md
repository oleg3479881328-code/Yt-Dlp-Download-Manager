# Science Assembly Draft

Draft implementation scaffold for GitHub issue #2.

## Safety boundary

This module is a rights-aware science video assembly prototype.

It does **not** implement automatic YouTube downloading for publication.

## Offline shape test

Run without API keys:

```powershell
python -m science_assembly.cli beats --script science_assembly/samples/photosynthesis_short_script.ru.txt --out outputs/science_assembly/demo --offline-demo
```

Then inspect:

```text
outputs/science_assembly/demo/visual_beats.json
```

## DeepSeek test

Requires:

```env
DEEPSEEK_API_KEY=...
AI_MODEL_FAST=deepseek-v4-flash
AI_MODEL_REASONING=deepseek-v4-pro
```

Run:

```powershell
python -m science_assembly.cli beats --script science_assembly/samples/photosynthesis_short_script.ru.txt --out outputs/science_assembly/demo
```

## Pexels search test

Requires:

```env
PEXELS_API_KEY=...
```

Run after beats:

```powershell
python -m science_assembly.cli search --beats outputs/science_assembly/demo/visual_beats.json --out outputs/science_assembly/demo
```

## Ranking test

With DeepSeek:

```powershell
python -m science_assembly.cli rank --beats outputs/science_assembly/demo/visual_beats.json --candidates outputs/science_assembly/demo/source_candidates.json --out outputs/science_assembly/demo
```

Offline shape test:

```powershell
python -m science_assembly.cli rank --beats outputs/science_assembly/demo/visual_beats.json --candidates outputs/science_assembly/demo/source_candidates.json --out outputs/science_assembly/demo --offline-demo
```

## Approval and timeline

```powershell
python -m science_assembly.cli make-approval-template --ranked outputs/science_assembly/demo/ranked_candidates.json --out outputs/science_assembly/demo/manual_approvals.json
```

Edit `manual_approvals.json` and change selected items to:

```json
"approval_status": "approved"
```

Then:

```powershell
python -m science_assembly.cli timeline --beats outputs/science_assembly/demo/visual_beats.json --candidates outputs/science_assembly/demo/source_candidates.json --approvals outputs/science_assembly/demo/manual_approvals.json --out outputs/science_assembly/demo
```

Outputs:

```text
timeline.json
source_ledger.json
```

## Notes for executor

- This is draft code, not production code.
- Add tests before merging implementation.
- Do not commit API keys.
- Add the second stock provider adapter before claiming full Pexels/Pixabay coverage.
- Keep source ledger review status conservative by default.
