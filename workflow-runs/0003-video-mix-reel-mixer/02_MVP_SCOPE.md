# 02_MVP_SCOPE — VIDEO MIX

Date: 2026-06-26
Status: planning

## MVP Name

`VIDEO MIX MVP 1 — Wedding Pack Pilot`

## MVP Purpose

Prove that the existing local video project can turn one folder of user-owned media into a batch of usable short vertical Reels.

The MVP is not intended to prove every future industry. It proves the reusable engine shape using one pilot pack.

## User Input

A local project folder containing:

```text
input/
  video/
  photo/
  music/        optional
  brand/        optional
output/
```

Minimum expected input:

- 10+ short videos, or 20–30 preferred;
- videos may be vertical, horizontal or mixed;
- photos are optional in the first MVP;
- no cloud upload required.

## MVP Output

The system should produce:

- a local asset catalog;
- extracted micro-clips;
- candidate reel plans;
- previewable candidates;
- approved exported MP4 files.

Target output count for first validation:

```text
10–20 candidate reels
3–5 approved exports
```

## Target Reel Defaults

```text
aspect ratio: 9:16
resolution: 1080x1920 preferred
fps: inherit or normalize to 30fps
length: 15–35 seconds
format: MP4
codec: H.264 + AAC when audio is present
```

## Required MVP Features

1. Choose or provide a local project folder.
2. Scan videos and photos.
3. Extract metadata with `ffprobe` or equivalent.
4. Split videos into micro-clips.
5. Create a basic local asset catalog.
6. Compute basic quality scores.
7. Detect obvious duplicates or near-duplicates.
8. Apply 3–5 fixed templates from the first industry pack.
9. Generate candidate reel plans.
10. Render preview/export for selected candidates.
11. Keep all source media and exports out of GitHub.

## First Wedding Templates

Keep template count small:

1. `romantic_story`;
2. `fast_highlight`;
3. `behind_the_scenes`;
4. `details_to_couple`;
5. `party_energy`.

## Explicit Non-Goals

- no social posting automation;
- no SaaS;
- no public product packaging;
- no Chrome Web Store work;
- no GPU video generation dependency;
- no large timeline editor;
- no industry pack marketplace;
- no advanced AI scene understanding required for MVP 1;
- no perfect automatic selection promise;
- no storing raw media or exports in repository.

## MVP Success Criteria

MVP 1 is successful only if:

- a local folder can be processed end-to-end;
- at least 10 candidate reels are generated from one source package;
- at least 3 MP4 exports are created after approval;
- output is visibly different across templates;
- source files and exports remain local and uncommitted;
- the architecture remains pack-based and not wedding-hardcoded.

## Validation Scenario

Use a test folder such as:

```text
local_test_media/wedding_pilot_001/
```

The folder itself must not be committed.

Expected validation report:

- number of input files;
- number of detected assets;
- number of micro-clips;
- number of candidate plans;
- number of exported MP4 files;
- export duration and file sizes;
- known failures or rejected candidates.

## Next Action

Use this scope as the boundary for architecture planning and later implementation handoff.
