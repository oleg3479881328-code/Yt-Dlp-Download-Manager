# 10_DONOR_RESEARCH — VIDEO MIX

Date: 2026-06-26
Status: initial donor research / not exhaustive

## Why This Exists

Owner asked whether a deep donor/source/ready-solution search had been done before approving VIDEO MIX.

Honest answer: before this file, no full VIDEO MIX-specific deep donor search had been committed. The earlier work reused internal project context and previous video-analysis donor research, but VIDEO MIX needs its own donor review.

This file captures the first external donor scan.

## Research Categories

VIDEO MIX needs donors in several categories:

1. scene detection and splitting;
2. automatic editing / silence or motion based cutting;
3. programmatic video editing libraries;
4. template rendering systems;
5. cloud video editing APIs;
6. long-video-to-shorts SaaS tools;
7. local/manual editors as workflow references.

## Strong Technical Donors

### PySceneDetect

Use for:

- scene detection;
- cut list generation;
- possible video splitting;
- Python API or CLI reference.

Why useful:

- directly relevant to micro-clip extraction;
- supports command-line and Python API;
- requires ffmpeg or mkvmerge for splitting.

Decision:

- strong candidate for Stage 1 or Stage 2 clip segmentation.

Source:

- https://www.scenedetect.com/docs/latest/

### Auto-Editor

Use for:

- automatic editing based on audio loudness and other methods;
- CLI workflow ideas;
- timeline format ideas.

Why useful:

- relevant for removing dead/silent/weak parts;
- better for talking-head or audio-driven material than purely visual wedding backstage.

Decision:

- useful donor idea, not primary engine.

Source:

- https://auto-editor.com/

### MoviePy

Use for:

- Python video editing automation;
- clip concatenation;
- resizing/cropping;
- quick prototype rendering.

Why useful:

- Python-native;
- open source;
- good for fast prototype logic.

Risk:

- may be slower or less robust than raw ffmpeg for bulk production.

Decision:

- useful prototype/reference; production export may still prefer ffmpeg/Remotion.

Source:

- https://zulko.github.io/moviepy/

### FFmpeg / ffprobe

Use for:

- probing metadata;
- cutting;
- scaling/cropping 9:16;
- concatenation;
- export.

Decision:

- primary low-level local media backend.

Source:

- https://ffmpeg.org/

### Remotion

Use for:

- template-based rendering;
- text overlays;
- branded layouts;
- preview/render layer;
- reuse with existing `subtitle_studio` experience.

Decision:

- strong candidate for visual template rendering after basic ffmpeg pipeline works.

Source:

- https://www.remotion.dev/docs/

## Cloud/API Donors

### Creatomate

Use for:

- template video generation;
- bulk generation patterns;
- API-driven renders;
- spreadsheet/CSV-style batch production ideas.

Decision:

- very strong product-pattern donor, but not local-first MVP backend.

Source:

- https://creatomate.com/

### Shotstack

Use for:

- cloud video editing API patterns;
- JSON template ideas;
- bulk video rendering;
- industry examples such as real estate and automotive.

Decision:

- strong architecture/product donor, not first local MVP backend.

Source:

- https://shotstack.io/

## SaaS/Product Donors

### OpusClip

Use for:

- long-video-to-shorts product flow;
- AI clipping;
- AI reframing;
- brand templates;
- social workflow ideas.

Fit:

- strong for long talking videos, podcasts, vlogs and existing long-form content;
- less direct for mixing many backstage clips into many new reels.

Decision:

- product/UX donor, not engine donor.

Source:

- https://www.opus.pro/

### CapCut long video to shorts / AutoCut style workflows

Use for:

- UX reference;
- manual review/polish layer;
- creator-facing expectations.

Decision:

- workflow reference only; not reliable local automation backend.

Source:

- https://www.capcut.com/tools/long-video-to-shorts

## Local Editor References

Kdenlive, Shotcut, Flowblade, Avidemux and similar editors prove mature editing workflows, but they are not ideal primary donors for a compact local batch engine.

Use only for:

- export format ideas;
- timeline concepts;
- manual editing expectations.

Do not embed or depend on them for Stage 1.

## Recommended VIDEO MIX Donor Stack

For Stage 1 local MVP:

```text
ffprobe
+ ffmpeg
+ simple Python orchestration
+ pack/template config
+ human review gate
```

For Stage 1.5 or Stage 2:

```text
PySceneDetect
+ stronger duplicate detection
+ better scene/shot extraction
```

For visual templates and branded overlays:

```text
Remotion
```

For product pattern inspiration:

```text
Creatomate
Shotstack
OpusClip
CapCut
```

## Current Recommendation

Do not approve Stage 1 until this donor research is reviewed.

The existing draft code remains useful as a local skeleton, but it should be revised by Codex with these donor decisions in mind:

- consider PySceneDetect for scene splitting instead of only fixed 3-second cuts;
- keep ffmpeg/ffprobe as local backend;
- keep Remotion as likely template renderer for branded output;
- keep Creatomate/Shotstack as architecture references, not dependencies;
- keep OpusClip/CapCut as UX/product references, not core backend.

## Not Yet Done

This is not a full deep research report yet.

Still worth checking before implementation:

- GitHub repositories for automated social video generation;
- CLIP/YOLO/OpenCV options for visual tagging;
- duplicate/perceptual hash libraries;
- music beat detection libraries;
- wedding/video-industry-specific auto-editing tools;
- licensing risks for SaaS/API donors;
- Windows compatibility of all chosen libraries.
