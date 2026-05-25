# IMPLEMENTATION HANDOFF PACKET — Animated Subtitle Video Maker Phase 1 MVP

## Packet Type

Codex execution packet — bounded new module implementation.

## Objective

Implement a new isolated local module named `subtitle_studio/` inside the existing repository. The module must prove one end-to-end rendering scenario:

```text
local user video + prepared timed captions JSON
    -> local preview with karaoke highlighting
    -> exported MP4 with burned-in animated subtitles
```

This is a personal local tool. Do not build public-product infrastructure.

## Source Decision / Design

Owner decision recorded on 2026-05-25:

- Add `Animated Subtitle Video Maker` inside `Yt-Dlp-Download-Manager`.
- Use `Remotion` + `@remotion/captions` for video preview/rendering.
- Use a later Phase 2 for `stable-ts` / `faster-whisper` word-timing generation.
- Keep Phase 1 strictly about rendering prepared timed captions onto a local video.

Read before execution:

1. `PROJECT_ENTRYPOINT.md`
2. `PROJECT_STATE.md`
3. `PROJECT_RULES.md`
4. `workflow-runs/0002-animated-subtitle-module/02_RESEARCH.md`
5. `workflow-runs/0002-animated-subtitle-module/03_PLAN.md`
6. This packet.

Primary external docs to follow:

- Remotion captions: `https://www.remotion.dev/docs/captions/create-tiktok-style-captions`
- Remotion displaying captions: `https://www.remotion.dev/docs/captions/displaying`
- Remotion Player: `https://www.remotion.dev/docs/player`

## Allowed Scope

Create an isolated React/TypeScript/Remotion module under:

```text
subtitle_studio/
```

Phase 1 must contain:

- an installable local Remotion project;
- one Remotion composition called clearly, for example `KaraokeVideo`;
- composition props for local video source and caption timing data;
- a documented sample captions JSON file containing word timings;
- one built-in visual preset called `KaraokePresetV1`;
- a preview workflow;
- an MP4 export workflow;
- a local README with exact commands and asset-placement instructions;
- tests or minimum automated checks that are practical for the created module.

A minimal `.gitignore` update is allowed only to exclude module runtime outputs such as:

- `subtitle_studio/node_modules/`
- `subtitle_studio/out/`
- user-supplied local video assets if a specific local asset folder is created.

## Out of Scope

Do not implement any of the following in this packet:

- automatic transcription;
- `stable-ts` or `faster-whisper` integration;
- `yt-dlp` subtitle download integration;
- subtitle translation;
- speaker detection;
- timeline editor;
- user-facing style editor;
- multiple presets;
- batch video generation;
- integration with existing FastAPI dashboard;
- integration with Chrome extension;
- changes to native host behavior;
- cloud services;
- packaging or installer work.

## Repository Context

Existing verified application layers:

- `app/` — existing FastAPI web dashboard and Python downloader runtime;
- `chrome_extension/` — existing browser extension;
- `native_host/` — existing Windows native messaging runtime.

They are outside the implementation target. New Remotion work must be isolated under `subtitle_studio/`.

Do not assume or invent a local filesystem repository path. Execute only inside the actual repository opened in VS Code/Codex and verify the repository identity first.

## Files Allowed To Change

Allowed new files:

```text
subtitle_studio/**
```

Allowed existing file modification:

```text
.gitignore
```

Only if needed to exclude Node dependencies, rendered outputs, or local test-video assets.

Not allowed in the implementation commit:

```text
app/**
chrome_extension/**
native_host/**
PROJECT_ENTRYPOINT.md
PROJECT_STATE.md
PROJECT_RULES.md
logs/**
workflow-runs/**
README.md at repository root
```

Project state documents are updated only after execution report and review.

## Forbidden Changes

- Do not refactor existing downloader or transcription code.
- Do not connect the Remotion module to FastAPI in this packet.
- Do not add a second preset or settings UI.
- Do not commit user video files or rendered `.mp4` files.
- Do not claim transcription works: Phase 1 accepts prepared caption timing input only.
- Do not change existing project behavior to make the demo work.

## Implementation Instructions

### 1. Module setup

Create `subtitle_studio/` as a self-contained local Remotion + React + TypeScript project using current official Remotion setup guidance. Keep dependency versions internally consistent.

### 2. Input model

Implement a typed caption input contract using Remotion caption-compatible timed token data. Place a small documented example file in the module, such as:

```text
subtitle_studio/public/samples/captions.json
```

The sample must include enough timed words to visibly demonstrate changing active-word highlighting.

Do not commit a binary sample video. Provide instructions for the user to place his own short test video into an ignored local asset location or pass it through supported Remotion props.

### 3. Composition

Create one portrait-oriented composition with default dimensions:

```text
1080 x 1920
```

Requirements:

- play a local video source;
- preserve usable aspect ratio with sensible fit behavior;
- render timed captions over the video;
- group captions in a TikTok-style readable page/window using `@remotion/captions` when appropriate;
- activate the currently spoken word from word timing data.

### 4. One visual preset only

Implement `KaraokePresetV1` with:

- subtitle block in the lower-center safe area;
- readable bold text;
- visible inactive words;
- active word clearly highlighted in a contrasting color;
- one restrained pop/scale animation on activation;
- text stroke and/or shadow for legibility over video.

All style constants should be localized in one clear component/config location so later presets can be added without rewriting caption timing logic. Do not build a preset selector yet.

### 5. Preview and export

Provide working local commands for:

- installing dependencies;
- opening preview;
- rendering/exporting an MP4.

The README must state how the user supplies his own local video and caption JSON.

### 6. Validation discipline

Validate only what has been built. A successful UI preview is not enough: perform one actual MP4 render using non-private disposable local/sample media if available. If no local test video is available in the environment, clearly report render validation as blocked by missing input media and do not fabricate success.

## Acceptance Criteria

The implementation can be marked ready for review only if all of the following are true:

1. `subtitle_studio/` exists as an isolated local Remotion module.
2. Existing `app/`, `chrome_extension/`, and `native_host/` behavior was not modified.
3. The module accepts a video source plus prepared word-timed caption data.
4. The module contains exactly one purposeful subtitle style preset: `KaraokePresetV1` or an equally explicit name.
5. During preview, the active word visibly changes styling according to timing.
6. Instructions for local setup, input replacement, preview and MP4 export exist in `subtitle_studio/README.md`.
7. Generated output and local media are excluded from Git where applicable.
8. One exported MP4 with burned-in karaoke subtitles is actually produced and visually verified, or the execution report explicitly states that this final validation is blocked by missing local media.
9. No claims are made about transcription integration, because it is not part of Phase 1.

## Validation Commands / Checks

Codex must choose exact commands compatible with the created official Remotion project, then report them verbatim. Minimum required checks:

```text
1. Confirm repository identity before editing.
2. Install module dependencies in subtitle_studio/.
3. Run the module's type/lint/build checks if configured.
4. Open or run preview and confirm karaoke word activation visually.
5. Execute one MP4 render command if test video input is available.
6. Confirm no generated MP4 or local input video is staged for commit.
7. Report git diff/status and list all files changed.
```

## Rollback Notes

Phase 1 is intentionally isolated. If unsuccessful, rollback should require removal of `subtitle_studio/` and any narrow `.gitignore` additions only. Existing downloader application code must remain unaffected.

## Execution Report Contract

Return exactly this structure after execution:

```text
EXECUTION REPORT

Status: completed | blocked | failed
Repository Verified: Yes / No
Files Changed:
- ...

Commands Run:
- ...

Validation Performed:
- ...

Validation Not Performed:
- ...

Rendered MP4 Produced: Yes / No
Rendered MP4 Visually Checked: Yes / No

Blockers:
- ...

Assumptions Made:
- ...

Risks / Follow-Up:
- ...

Ready For Review: Yes / No
```

## Final Instruction To Codex

Implement only Phase 1 rendering proof. Stop after the execution report. Do not begin Phase 2 transcription integration without a new reviewed packet.
