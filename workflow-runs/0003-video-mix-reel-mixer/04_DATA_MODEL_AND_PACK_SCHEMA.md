# 04_DATA_MODEL_AND_PACK_SCHEMA — VIDEO MIX

Date: 2026-06-26
Status: planning

## Purpose

Define the minimum data model and industry-pack contract for `VIDEO MIX`.

This document is planning-only. It should guide later implementation.

## Main Entities

```text
Project
Asset
Clip
Tag
Template
CandidateReel
ReviewDecision
Export
```

## Project

Represents one local user media package.

Fields:

```yaml
project_id: string
name: string
industry_pack: string
root_path: string
created_at: datetime
status: scanned | clips_ready | candidates_ready | reviewed | exported
notes: string
```

## Asset

Represents an original media file.

Fields:

```yaml
asset_id: string
project_id: string
path: string
media_type: video | photo
duration_ms: integer
width: integer
height: integer
fps: number
orientation: vertical | horizontal | square | unknown
has_audio: boolean
probe_status: ok | warning | failed
quality_score: number
created_at_source: datetime | null
```

## Clip

Represents a derived usable segment from a video, or a still-photo motion segment.

Fields:

```yaml
clip_id: string
project_id: string
asset_id: string
source_start_ms: integer
source_end_ms: integer
duration_ms: integer
working_path: string
thumbnail_path: string
tags: list[string]
quality_score: number
duplicate_group_id: string | null
usable: boolean
reject_reason: string | null
```

## Template

Represents a reusable editing formula.

Fields:

```yaml
template_id: string
pack_id: string
name: string
target_duration_ms: integer
pacing: slow | medium | fast
slots: list[TemplateSlot]
overlays: list[OverlayRule]
export_preset: string
```

## Template Slot

Represents one required or optional position in a Reel.

Fields:

```yaml
slot_id: string
min_duration_ms: integer
max_duration_ms: integer
required_tags: list[string]
preferred_tags: list[string]
forbidden_tags: list[string]
reuse_policy: avoid_same_asset | allow | lock_if_selected
```

## CandidateReel

Represents a planned Reel before export.

Fields:

```yaml
candidate_id: string
project_id: string
pack_id: string
template_id: string
status: generated | previewed | approved | rejected | exported
score: number
duration_ms: integer
clip_sequence: list[CandidateClip]
overlays: list[ResolvedOverlay]
created_at: datetime
review_notes: string
```

## CandidateClip

```yaml
clip_id: string
slot_id: string
start_in_reel_ms: integer
end_in_reel_ms: integer
speed: number
crop_mode: fill_9_16 | fit_blur | center_crop
```

## ReviewDecision

```yaml
decision_id: string
candidate_id: string
decision: approve | reject | regenerate | lock_clip | avoid_clip
reason: string
created_at: datetime
```

## Export

```yaml
export_id: string
candidate_id: string
output_path: string
width: integer
height: integer
fps: number
duration_ms: integer
file_size_bytes: integer
render_status: queued | rendering | completed | failed
error_message: string | null
created_at: datetime
```

## Industry Pack Schema

Each pack should be stored as configuration, not core code where possible.

Example:

```yaml
pack_id: wedding
name: Wedding Photographer
version: 1
scene_tags:
  - details
  - preparation
  - bride
  - groom
  - couple
  - ceremony
  - kiss
  - guests
  - dance
  - venue
  - backstage
  - emotion
scoring_weights:
  sharpness: 0.25
  exposure: 0.15
  face_or_subject_presence: 0.20
  tag_match: 0.25
  duplicate_penalty: 0.15
default_export:
  aspect_ratio: 9:16
  width: 1080
  height: 1920
  fps: 30
  format: mp4
```

## Wedding Template Example

```yaml
template_id: romantic_story
name: Romantic Story
target_duration_ms: 28000
pacing: medium
slots:
  - slot_id: opening_detail
    min_duration_ms: 1500
    max_duration_ms: 3000
    preferred_tags: [details, venue]
  - slot_id: preparation
    min_duration_ms: 1500
    max_duration_ms: 3500
    preferred_tags: [bride, groom, preparation]
  - slot_id: couple_moment
    min_duration_ms: 2500
    max_duration_ms: 5000
    preferred_tags: [couple, emotion]
  - slot_id: closing
    min_duration_ms: 2000
    max_duration_ms: 4000
    preferred_tags: [kiss, dance, couple]
```

## Storage Bias

Use the existing project style where possible:

- SQLite for local state;
- local output directories for derived clips and exports;
- no raw media or exports in GitHub.

## Next Action

Define review and scoring rules for candidate generation.
