# 11_DEEP_DONOR_RESEARCH_PRODUCTION_ENGINE — VIDEO MIX

Date: 2026-06-26
Status: deep donor research / production-engine framing

## Scope

This research is for a general production combiner, not only a wedding photographer tool.

Wedding is only the first pilot pack. The target architecture must support many production verticals:

- wedding / events;
- real estate;
- restaurants;
- automotive;
- product and gadget content;
- local services / before-after;
- fitness / beauty;
- travel / venue promotion;
- podcasts / education / creator repurposing.

## Core Question

What ready solutions and donor systems should shape `VIDEO MIX`?

The answer is not one donor. The right model is a layered donor stack.

```text
Asset intake
→ media intelligence
→ scene and clip extraction
→ visual/audio/tag scoring
→ timeline/candidate planning
→ template rendering
→ human review
→ export packages
→ optional publishing later
```

## Donor Layer 1 — Local Media Backend

### FFmpeg / ffprobe

Source: https://ffmpeg.org/

Role:

- metadata probing;
- trimming;
- scaling and cropping;
- concatenation;
- export;
- codec normalization.

Decision:

- primary local media backend for Stage 1.

Reason:

- already aligned with the current project;
- local-first;
- cross-platform;
- no cloud dependency;
- fits Windows workflow.

## Donor Layer 2 — Scene Detection / Micro-Clip Extraction

### PySceneDetect

Source: https://www.scenedetect.com/docs/latest/
GitHub: https://github.com/Breakthrough/PySceneDetect

Findings:

- provides command line and Python API;
- supports multiple detectors;
- can output scene lists and split video with ffmpeg or mkvmerge;
- relevant to replacing naive fixed 3-second cuts.

Decision:

- strong Stage 1.5 or Stage 2 donor;
- can be tested in Stage 1 if simple integration is cheap.

Use in VIDEO MIX:

```text
raw video -> scene list -> candidate micro-clips -> scoring
```

### Auto-Editor

Source: https://auto-editor.com/
GitHub: https://github.com/WyattBlue/auto-editor

Findings:

- automatically edits video/audio using methods, especially audio loudness;
- has CLI, GUI and timeline ideas.

Decision:

- donor for audio-driven trimming and timeline ideas;
- not primary engine for visual backstage/event footage.

Best use cases:

- podcasts;
- education;
- talking-head videos;
- interviews;
- webinars.

## Donor Layer 3 — Timeline Data Model

### OpenTimelineIO

Source: https://opentimelineio.readthedocs.io/en/latest/

Findings:

- API and interchange format for editorial cut information;
- represents clips, timing, tracks, transitions, markers and metadata;
- references external media instead of embedding video/audio.

Decision:

- strong architecture reference;
- do not add as a hard dependency in Stage 1 unless necessary;
- model our `CandidateReel` manifest in an OTIO-compatible direction.

VIDEO MIX implication:

- candidate Reels should be timeline manifests first, rendered files second.

## Donor Layer 4 — Programmatic Editing Libraries

### MoviePy

Source: https://zulko.github.io/moviepy/

Role:

- Python-native video editing prototype;
- clip concatenation;
- resizing/cropping;
- quick proof-of-concept.

Decision:

- useful prototype donor;
- avoid relying on it for heavy bulk export until validated.

### MLT / Shotcut / Kdenlive / Flowblade

Sources:

- https://www.mltframework.org/
- https://shotcut.org/
- https://kdenlive.org/
- https://jliljebl.github.io/flowblade/

Role:

- mature non-linear editing concepts;
- tracks, transitions, filters and rendering pipeline ideas.

Decision:

- reference only;
- too heavy for Stage 1 local batch engine.

### LosslessCut

Source: https://github.com/mifi/lossless-cut

Role:

- fast cutting UX;
- cut list handling;
- ffmpeg command exposure.

Decision:

- UX/reference donor for local review and fast trimming;
- not core engine.

## Donor Layer 5 — Visual Understanding / Tagging

### OpenCV

Source: https://opencv.org/

Findings:

- large open-source computer vision library;
- useful for blur, brightness, motion and frame analysis.

Decision:

- good Stage 1/2 local quality scoring dependency.

Use:

- blur detection;
- brightness/exposure score;
- frame sampling;
- motion/shakiness estimation;
- simple face/object heuristics.

### CLIP / OpenCLIP

Sources:

- https://github.com/openai/CLIP
- https://github.com/mlfoundations/open_clip

Findings:

- maps images and text into comparable embedding space;
- useful for zero-shot scene/tag matching.

Decision:

- strong future donor for industry-pack tagging;
- not required for Stage 1 local MVP.

Use:

```text
frame thumbnail + pack tag prompts -> semantic tag probabilities
```

Examples:

- real estate: kitchen, bathroom, exterior, bedroom;
- restaurant: dish, kitchen, chef, dining room;
- wedding: bride, rings, dance, venue;
- auto: exterior, interior, dashboard, wheel, engine.

### Ultralytics YOLO

Source: https://docs.ultralytics.com/

Findings:

- supports detection, segmentation, classification, pose and tracking;
- licensing needs attention: AGPL-3.0 or Enterprise.

Decision:

- powerful but not Stage 1 default;
- consider only if object detection becomes necessary and licensing is acceptable.

## Donor Layer 6 — Duplicate / Similarity Detection

### imagehash

Source: https://github.com/JohannesBuchner/imagehash

Findings:

- Python perceptual image hashing module;
- supports common perceptual hashing approaches.

Decision:

- good local donor for thumbnail-level duplicate detection;
- use for approximate visual duplication, not legal/copyright proof.

Use:

```text
sampled frame -> perceptual hash -> duplicate group -> reuse penalty
```

## Donor Layer 7 — Audio / Beat / Music Alignment

### librosa

Source: https://librosa.org/doc/latest/index.html
GitHub: https://github.com/librosa/librosa

Findings:

- Python package for music and audio analysis;
- includes onset detection, beat and tempo, temporal segmentation.

Decision:

- Stage 2 donor for music-aware editing;
- not necessary for Stage 1.

Use:

- beat-aligned cuts;
- energy detection;
- music-driven pacing templates.

### Essentia

Source: https://essentia.upf.edu/

Decision:

- advanced audio-analysis donor;
- likely too heavy for first local MVP.

## Donor Layer 8 — Template Rendering / Branded Output

### Remotion

Source: https://www.remotion.dev/docs/

Findings:

- programmatic video rendering with React/Node;
- templates, captions, player, rendering and app-building concepts;
- already proven in this repository through `subtitle_studio` Phase 1.

Decision:

- strong renderer for Stage 2 branded templates and overlays;
- Stage 1 can start with ffmpeg-only export if simpler.

Use:

- branded overlays;
- title cards;
- animated captions;
- logo and CTA system;
- vertical template families.

## Donor Layer 9 — Cloud Video APIs / Product Architecture

### Creatomate

Source: https://creatomate.com/docs/fundamentals/getting-started/introduction

Findings:

- media automation platform;
- spreadsheet bulk generation;
- REST API for programmatic video/image generation;
- template editor and preview SDK.

Decision:

- strong product architecture donor;
- do not use as dependency for local MVP.

Borrow:

- template-first production model;
- spreadsheet/batch mindset;
- one template -> many outputs.

### Shotstack

Source: https://shotstack.io/docs/api/

Findings:

- cloud editing API;
- JSON schema for tracks, clips, assets, transitions, overlays, text and output;
- separate Edit, Serve and Ingest APIs.

Decision:

- excellent timeline JSON donor;
- not local-first backend.

Borrow:

- JSON edit schema;
- render job lifecycle;
- timeline/track/clip model;
- template render model.

### JSON2Video

Source: https://json2video.com/docs/api/

Findings:

- public API resources: movies, templates and media;
- movie JSON syntax, scenes, elements, audio, subtitles.

Decision:

- useful JSON-template reference;
- not dependency.

### Cloudinary

Source: https://cloudinary.com/documentation/video_manipulation_and_delivery

Findings:

- video transformations, upload, asset management, AI add-ons and video-related APIs;
- useful for SaaS/cloud architecture but outside local MVP.

Decision:

- reference only.

## Donor Layer 10 — SaaS Competitor / UX Reference

### OpusClip

Source: https://www.opus.pro/

Findings:

- long video to multiple shorts;
- AI clipping, animated captions, AI reframe, AI B-roll, social scheduler, brand templates, XML export;
- positions itself across creators, agencies, advertisers, e-commerce and real estate.

Decision:

- strong UX/product donor;
- not engine donor for our local many-assets mixer.

Borrow:

- candidate scoring language;
- brand templates;
- reframe workflow;
- batch clips from one source;
- export-to-editor idea.

### quso.ai / vidyo.ai

Source: https://quso.ai/

Findings:

- AI clip generator, subtitles, content repurposing, social scheduler, analytics;
- use cases include creators, podcasters, freelancers, real estate, small businesses, agencies and entertainment.

Decision:

- strong general production workflow donor;
- more social-management oriented than local engine.

### Klap

Source: https://klap.app/

Findings:

- long video to TikToks/Reels/Shorts;
- AI edit, auto reframe, captions, customization, publishing/scheduling;
- FAQ says it works best for speech-heavy content.

Decision:

- strong long-video-to-shorts UX donor;
- less suitable as direct model for non-speech asset mixing.

### Munch Studio

Source: https://www.munchstudio.com/

Findings:

- broader AI social media marketing flow;
- learns business from website/videos/photos/Zoom recordings;
- creates posts and strategy, then owner approves and posts favorites.

Decision:

- very relevant to future production OS / industry-pack thinking;
- not Stage 1 engine donor.

Borrow:

- business-intake model;
- strategy layer;
- approve-and-post workflow;
- performance loop.

## Platform Output Constraints

### YouTube Shorts

Source: https://support.google.com/youtube/answer/12779649

Finding:

- computer upload Shorts can be up to 3 minutes and square or vertical.

Implication:

- default 9:16 under 3 minutes is safe for Shorts.

### TikTok Ads Specs

Source: https://ads.tiktok.com/help/article/tiktok-auction-in-feed-ads

Finding:

- vertical 9:16 recommended; at least 540x960 for vertical ads;
- common formats include mp4 and mov;
- file size limit for these ads is 500 MB.

Implication:

- local export preset 1080x1920 MP4 remains correct.

### Meta / Reels Direction

Source: https://www.reuters.com/business/all-new-facebook-videos-be-classified-reels-soon-meta-says-2025-06-17/

Finding:

- Meta announced Facebook video uploads would be unified under Reels and remove older length/format distinctions.

Implication:

- build export presets flexibly; do not hardcode only old Facebook Reels rules.

## Industry Pack Implications

The core engine should not contain industry logic.

Each industry pack should define:

- scene tags;
- preferred shot types;
- forbidden/weak shot patterns;
- pacing presets;
- template slots;
- overlay text rules;
- CTA library;
- export naming and metadata;
- optional visual tag prompts;
- optional music/beat rules;
- platform presets.

Example packs:

### Wedding / Event Pack

Tags:

- bride, groom, couple, guests, ceremony, dance, detail, venue, emotion, backstage.

Templates:

- romantic story;
- fast highlight;
- behind the scenes;
- details to couple;
- party energy.

### Real Estate Pack

Tags:

- exterior, kitchen, living room, bedroom, bathroom, backyard, drone, neighborhood, agent, before-after.

Templates:

- listing walkthrough;
- luxury reveal;
- top 5 features;
- before-after renovation;
- neighborhood teaser.

### Restaurant Pack

Tags:

- dish, chef, kitchen, plating, interior, guests, drink, closeup, steam, preparation.

Templates:

- dish hero;
- behind the kitchen;
- restaurant atmosphere;
- menu promo;
- chef process.

### Automotive Pack

Tags:

- exterior, interior, wheel, engine, dashboard, driving, detail, logo, before-after, feature.

Templates:

- car reveal;
- feature walkaround;
- luxury detail;
- before-after detailing;
- dealership promo.

### Product / Gadget Pack

Tags:

- unboxing, closeup, hand use, feature, before-after, comparison, problem, solution.

Templates:

- hook-problem-solution;
- top features;
- demo montage;
- before-after;
- affiliate style CTA.

## Recommended Architecture After Research

Stage 1 should remain simple:

```text
ffprobe + ffmpeg + Python orchestration + candidate manifests + review gate
```

But draft code should be revised before implementation:

1. Replace fixed 3-second cuts with pluggable segmentation:
   - fixed interval fallback;
   - PySceneDetect option;
   - future audio/speech/beat segmentation.

2. Make `CandidateReel` more timeline-like:
   - tracks;
   - clips;
   - overlays;
   - source references;
   - render settings;
   - review status.

3. Add industry pack contract:
   - tags;
   - templates;
   - scoring weights;
   - CTA text;
   - overlay rules;
   - platform presets.

4. Add duplicate detection:
   - sampled thumbnails;
   - perceptual hash;
   - duplicate groups;
   - reuse penalty.

5. Keep render layer modular:
   - Stage 1 ffmpeg render;
   - Stage 2 Remotion branded render.

6. Do not build publisher yet:
   - export packages only;
   - no account login;
   - no auto-posting.

## Decision Matrix

| Donor | Use Now | Use Later | Do Not Use As |
|---|---:|---:|---|
| ffmpeg / ffprobe | yes | yes | full product model |
| PySceneDetect | maybe | yes | full editor |
| Auto-Editor | no | maybe | visual event engine |
| OpenTimelineIO | reference | maybe | required Stage 1 dependency |
| MoviePy | maybe | maybe | heavy production exporter without testing |
| OpenCV | maybe | yes | semantic AI engine |
| CLIP/OpenCLIP | no | yes | Stage 1 dependency |
| YOLO | no | maybe | default dependency due licensing risk |
| imagehash | maybe | yes | legal proof of uniqueness |
| librosa | no | yes | Stage 1 dependency |
| Remotion | no | yes | first clip extraction tool |
| Creatomate | reference | reference | local backend |
| Shotstack | reference | reference | local backend |
| JSON2Video | reference | reference | local backend |
| OpusClip | UX reference | reference | direct backend |
| quso.ai | UX reference | reference | direct backend |
| Klap | UX reference | reference | non-speech mixer model |
| Munch Studio | workflow reference | reference | local engine |

## Recommended Stage Plan

### Stage 1 — Local Production Combiner MVP

Goal:

```text
one local production folder -> many candidate reels -> approved MP4 exports
```

Tech:

- Python;
- ffprobe;
- ffmpeg;
- simple metadata JSON/SQLite;
- basic industry pack config;
- simple preview/report.

No AI dependency required.

### Stage 1.5 — Smarter Clip Extraction

Add:

- PySceneDetect;
- perceptual hash duplicate detection;
- OpenCV quality scoring.

### Stage 2 — Branded Template Renderer

Add:

- Remotion renderer;
- title cards;
- logo placement;
- animated overlays;
- platform presets.

### Stage 3 — Visual Intelligence

Add optional:

- CLIP/OpenCLIP tag scoring;
- YOLO only if licensing is resolved;
- pack-specific prompt/tag libraries.

### Stage 4 — Production OS

Add:

- campaign/project database;
- asset library;
- approval queue;
- export packages;
- analytics metadata;
- multi-pack support.

Publishing automation remains separate and requires owner approval.

## Bottom Line

The strongest general architecture is not a wedding editor and not a clone of OpusClip.

It is:

```text
local media production combiner
+ pluggable industry packs
+ timeline/candidate manifest system
+ local rendering first
+ optional AI tagging later
+ human review gate
```

This keeps VIDEO MIX scalable across industries while staying compatible with the current local Windows project.
