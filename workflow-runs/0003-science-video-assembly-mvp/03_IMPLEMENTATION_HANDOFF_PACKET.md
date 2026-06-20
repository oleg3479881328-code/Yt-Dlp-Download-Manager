# Science Video Assembly MVP — Implementation Handoff Packet

- Date: 2026-06-20
- Packet type: Codex / developer handoff
- Repository: `oleg3479881328-code/Yt-Dlp-Download-Manager`
- Branch prepared by ChatGPT: `docs/science-video-assembly-mvp-20260620`
- Execution state: not implemented yet

## Objective

Implement the smallest safe AI-assisted prototype for science-popular video assembly.

The first implementation should prove this workflow:

```text
short script
-> DeepSeek visual beats JSON
-> Pexels/Pixabay source candidates
-> DeepSeek candidate ranking JSON
-> manual approval file
-> timeline JSON
-> source ledger JSON
```

Preview rendering is optional for the first execution if it would add too much risk. A JSON-only prototype is acceptable if it is validated with a sample script and real API payloads.

## Hard Boundaries

1. Do not implement automatic YouTube downloading for publication in MVP-1.
2. Do not bypass YouTube Terms or rights checks.
3. Do not disturb the accepted `subtitle_studio/` Phase 1 output.
4. Do not broaden this into a SaaS product, marketplace, accounts, publishing tool, or multi-user system.
5. Do not store API keys in committed files.
6. Do not overwrite existing downloaded media or accepted render artifacts.
7. Do not make the AI execute shell commands directly.
8. Preserve Project Execution OS documentation discipline.

## Environment Variables

Add support for environment-based secrets/settings only:

```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=
AI_MODEL_FAST=deepseek-v4-flash
AI_MODEL_REASONING=deepseek-v4-pro
PEXELS_API_KEY=
PIXABAY_API_KEY=
SCIENCE_ASSEMBLY_OUTPUT_DIR=outputs/science_assembly
```

If keys are missing, fail with a clear message.

## Proposed Implementation Files

Executor may adjust names if existing repository structure demands it, but must keep the implementation isolated.

```text
science_assembly/
  __init__.py
  cli.py
  ai/
    __init__.py
    provider.py
    deepseek_provider.py
    prompts.py
    json_validation.py
  sources/
    __init__.py
    pexels.py
    pixabay.py
    normalizer.py
  pipeline/
    __init__.py
    visual_beats.py
    candidate_ranking.py
    timeline_builder.py
    source_ledger.py
  samples/
    photosynthesis_short_script.ru.txt
  schemas/
    README.md
```

Optional later:

```text
science_assembly/render/
  ffmpeg_preview.py
  remotion_bridge.md
```

## CLI Proposal

Minimum useful commands:

```powershell
python -m science_assembly.cli beats --script science_assembly/samples/photosynthesis_short_script.ru.txt --out outputs/science_assembly/demo
python -m science_assembly.cli search --beats outputs/science_assembly/demo/visual_beats.json --out outputs/science_assembly/demo
python -m science_assembly.cli rank --beats outputs/science_assembly/demo/visual_beats.json --candidates outputs/science_assembly/demo/source_candidates.json --out outputs/science_assembly/demo
python -m science_assembly.cli make-approval-template --ranked outputs/science_assembly/demo/ranked_candidates.json --out outputs/science_assembly/demo/manual_approvals.json
python -m science_assembly.cli timeline --approvals outputs/science_assembly/demo/manual_approvals.json --out outputs/science_assembly/demo
```

Optional:

```powershell
python -m science_assembly.cli preview --timeline outputs/science_assembly/demo/timeline.json --out outputs/science_assembly/demo/preview.mp4
```

## AI Provider Requirements

### DeepSeek provider

Use OpenAI-compatible client with:

```python
base_url="https://api.deepseek.com"
```

Use JSON Output where appropriate:

```python
response_format={"type": "json_object"}
```

Prompt must include the word `json` and an example JSON shape.

### Model routing

Use fast model for:

- visual beat extraction;
- source query generation;
- candidate ranking.

Use reasoning/pro model for:

- script expansion;
- final QA review;
- resolving conflicts or ambiguous visual plans.

Default model names should come from environment variables.

## Source Adapter Requirements

### Pexels

Implement video search adapter:

- endpoint: `GET https://api.pexels.com/v1/videos/search`
- auth: `Authorization: PEXELS_API_KEY`
- input: query, orientation optional, per_page optional.
- output: normalized `source_candidate` objects.

### Pixabay

Implement video search adapter:

- endpoint: `GET https://pixabay.com/api/videos/`
- input: key, q, category optional, safesearch true by default, per_page.
- output: normalized `source_candidate` objects.

## Manual Approval Requirement

The first implementation may use a JSON file as the approval surface.

Generated template should mark all candidates as `pending_review`.

The owner/developer manually changes selected candidates to `approved`.

The timeline command must include only `approved` candidates.

## Source Ledger Requirement

Every timeline asset must appear in `source_ledger.json`.

The ledger must include at least:

- provider;
- source URL;
- creator if available;
- license / terms URL if available;
- date accessed;
- local path if downloaded;
- usage decision;
- rights review status.

## Sample Script

Create a short Russian sample script for photosynthesis, about 60–90 seconds, if no sample exists.

Do not use a 10-minute script for MVP validation. Keep test data small.

## Acceptance Criteria

Implementation is accepted only if all are true:

- A sample script produces valid `visual_beats.json`.
- At least 5 visual beats are generated.
- Pexels and/or Pixabay search returns normalized candidates.
- Candidate ranking produces structured JSON with scores and warnings.
- Manual approval file is generated.
- Timeline JSON is generated from approved items only.
- Source ledger JSON is generated.
- Missing API keys fail safely with clear messages.
- No YouTube content is automatically downloaded.
- Existing downloader and subtitle studio tests / behavior are not broken.
- Executor reports commands run and actual output file paths.

## Validation Commands

Executor should return a validation report containing:

```text
python -m science_assembly.cli beats ...
python -m science_assembly.cli search ...
python -m science_assembly.cli rank ...
python -m science_assembly.cli make-approval-template ...
python -m science_assembly.cli timeline ...
```

If tests are added:

```text
pytest tests/test_science_assembly_*.py
```

## Risks

### RISK-001 — Rights ambiguity

Pexels/Pixabay are easier than arbitrary YouTube, but provider terms still require review before publication.

Mitigation:

- ledger-first design;
- mark publication as not approved by default;
- require review status.

### RISK-002 — AI JSON instability

DeepSeek JSON mode can still return unusable output if prompt or max tokens are wrong.

Mitigation:

- schema validation;
- short prompts;
- output examples;
- retry once with correction prompt;
- store raw output for debugging.

### RISK-003 — Scope creep into full editor

The owner wants automation, but MVP-1 should not become a full editor.

Mitigation:

- JSON workflow first;
- preview optional;
- UI later.

### RISK-004 — Rendering complexity

Remotion/ffmpeg rendering can distract from proving source discovery and timeline assembly.

Mitigation:

- timeline JSON is the primary MVP output;
- preview render is optional if timeline is valid.

## Deliverables

Executor must return:

1. Files changed.
2. Commands run.
3. Output artifacts created.
4. API calls tested or skipped due to missing keys.
5. Screenshots or sample output snippets if useful.
6. Known limitations.
7. Next recommended step.

## Recommended Next Step After MVP-1

If MVP-1 works, create a separate spike:

```text
Twelve Labs / VideoDB semantic video search spike
```

Goal:

- upload 2–3 approved videos;
- ask natural-language moment search queries;
- compare results to local transcript/frame analyzer;
- decide whether external semantic video API is worth integration.
