# Science Video Assembly MVP — JSON Schemas

- Date: 2026-06-20
- Status: draft schemas for MVP implementation

## Design Rule

All AI-generated outputs must be machine-parseable JSON.

The system should validate AI output before using it. If validation fails, the system should retry with a correction prompt or stop with a clear error.

## 1. Script Segments

File: `script_segments.json`

```json
{
  "project_id": "science_video_demo_001",
  "language": "ru",
  "target_duration_seconds": 120,
  "segments": [
    {
      "segment_id": "seg_001",
      "order": 1,
      "narration_text": "Фотосинтез — это процесс, с помощью которого растения превращают свет в химическую энергию.",
      "approx_start_seconds": 0,
      "approx_end_seconds": 12,
      "key_claims": [
        "plants convert light into chemical energy"
      ],
      "fact_check_status": "needs_check"
    }
  ]
}
```

Required fields:

- `project_id`
- `language`
- `target_duration_seconds`
- `segments[]`
- `segment_id`
- `order`
- `narration_text`
- `approx_start_seconds`
- `approx_end_seconds`
- `fact_check_status`

## 2. Visual Beats

File: `visual_beats.json`

```json
{
  "project_id": "science_video_demo_001",
  "source_script_file": "script_segments.json",
  "beats": [
    {
      "beat_id": "beat_001",
      "script_segment_id": "seg_001",
      "order": 1,
      "narration_text": "Фотосинтез — это процесс, с помощью которого растения превращают свет в химическую энергию.",
      "visual_need": "sunlight hitting green plant leaves, educational science style",
      "visual_type": "b_roll",
      "preferred_style": "real footage or clean educational animation",
      "duration_seconds": 8,
      "search_queries": [
        "sunlight green leaves close up",
        "plant leaves sunlight nature",
        "photosynthesis leaves sunlight"
      ],
      "avoid": [
        "cartoonish low quality visuals",
        "people speaking to camera"
      ],
      "rights_requirement": "allowed_or_reviewed",
      "importance": "high"
    }
  ]
}
```

Allowed `visual_type` values:

- `b_roll`
- `animation`
- `diagram`
- `stock_video`
- `ai_generated_visual`
- `local_media`
- `youtube_embed_reference`

Allowed `importance` values:

- `low`
- `medium`
- `high`

## 3. Source Candidate

File: `source_candidates.json`

```json
{
  "project_id": "science_video_demo_001",
  "candidates": [
    {
      "candidate_id": "cand_001",
      "beat_id": "beat_001",
      "provider": "pexels",
      "source_url": "https://www.pexels.com/video/example/",
      "asset_url": "https://videos.pexels.com/video-files/example.mp4",
      "thumbnail_url": "https://images.pexels.com/videos/example.jpg",
      "creator_name": "Creator Name",
      "creator_url": "https://www.pexels.com/@creator/",
      "license_name": "Pexels License / provider terms",
      "license_url": "https://www.pexels.com/license/",
      "query": "sunlight green leaves close up",
      "duration_seconds": 12,
      "width": 1920,
      "height": 1080,
      "orientation": "landscape",
      "tags": ["leaves", "sunlight", "nature"],
      "rights_status": "provider_terms_review_needed",
      "download_allowed": "unknown",
      "date_accessed": "2026-06-20",
      "raw_provider_payload_file": "raw/pexels_cand_001.json"
    }
  ]
}
```

Allowed `provider` values for MVP-1:

- `pexels`
- `pixabay`
- `local_media`

Future provider values:

- `twelve_labs`
- `videodb`
- `paid_stock`
- `youtube_reference`

Allowed `rights_status` values:

- `allowed`
- `provider_terms_review_needed`
- `needs_rights_review`
- `not_allowed`
- `unknown`

Allowed `download_allowed` values:

- `yes`
- `no`
- `unknown`

## 4. Ranked Candidate

File: `ranked_candidates.json`

```json
{
  "project_id": "science_video_demo_001",
  "rankings": [
    {
      "beat_id": "beat_001",
      "ranked_candidates": [
        {
          "candidate_id": "cand_001",
          "relevance_score": 0.87,
          "technical_score": 0.78,
          "rights_score": 0.50,
          "overall_score": 0.74,
          "why_it_matches": "Shows close-up green leaves with sunlight, matching the opening visual need.",
          "mismatch_warnings": [
            "No explicit science context on screen"
          ],
          "rights_warning": "Provider terms must be reviewed before publication use.",
          "recommendation": "review"
        }
      ]
    }
  ]
}
```

Allowed `recommendation` values:

- `approve_candidate`
- `review`
- `reject`
- `needs_rights_review`

## 5. Manual Approval

File: `manual_approvals.json`

```json
{
  "project_id": "science_video_demo_001",
  "approvals": [
    {
      "beat_id": "beat_001",
      "candidate_id": "cand_001",
      "approval_status": "approved",
      "approved_by": "owner",
      "approved_at": "2026-06-20T10:00:00-04:00",
      "notes": "Good enough for MVP preview. Check provider terms before publication."
    }
  ]
}
```

Allowed `approval_status` values:

- `pending_review`
- `approved`
- `rejected`
- `needs_rights_review`
- `replace_needed`

## 6. Timeline

File: `timeline.json`

```json
{
  "project_id": "science_video_demo_001",
  "title": "Фотосинтез простыми словами",
  "language": "ru",
  "target_aspect_ratio": "16:9",
  "target_resolution": "1920x1080",
  "fps": 30,
  "tracks": {
    "voiceover": [
      {
        "clip_id": "voice_001",
        "script_segment_id": "seg_001",
        "text": "Фотосинтез — это процесс, с помощью которого растения превращают свет в химическую энергию.",
        "timeline_start_seconds": 0,
        "timeline_end_seconds": 12,
        "audio_file": null
      }
    ],
    "visuals": [
      {
        "clip_id": "visual_001",
        "beat_id": "beat_001",
        "candidate_id": "cand_001",
        "source_file": "assets/cand_001.mp4",
        "source_start_seconds": 0,
        "source_end_seconds": 8,
        "timeline_start_seconds": 0,
        "timeline_end_seconds": 8,
        "fit_mode": "cover",
        "crop_mode": "center",
        "approved_for_preview": true,
        "approved_for_publication": false
      }
    ],
    "captions": [
      {
        "caption_id": "cap_001",
        "text": "Фотосинтез — это процесс...",
        "start_seconds": 0,
        "end_seconds": 4,
        "style": "default"
      }
    ]
  },
  "source_ledger_file": "source_ledger.json"
}
```

Allowed `target_aspect_ratio` values:

- `16:9`
- `9:16`
- `1:1`

Allowed `fit_mode` values:

- `cover`
- `contain`
- `blur_background`

## 7. Source Ledger

File: `source_ledger.json`

```json
{
  "project_id": "science_video_demo_001",
  "created_at": "2026-06-20T10:00:00-04:00",
  "assets": [
    {
      "asset_id": "asset_001",
      "candidate_id": "cand_001",
      "beat_id": "beat_001",
      "provider": "pexels",
      "source_url": "https://www.pexels.com/video/example/",
      "creator_name": "Creator Name",
      "creator_url": "https://www.pexels.com/@creator/",
      "license_name": "Pexels License / provider terms",
      "license_url": "https://www.pexels.com/license/",
      "date_accessed": "2026-06-20",
      "local_file": "assets/cand_001.mp4",
      "usage_decision": "preview_only",
      "rights_review_status": "needs_review_before_publication",
      "notes": "Used only for MVP preview until terms are reviewed."
    }
  ]
}
```

Allowed `usage_decision` values:

- `preview_only`
- `approved_for_publication`
- `rejected`
- `reference_only`

Allowed `rights_review_status` values:

- `needs_review_before_publication`
- `reviewed_ok`
- `rejected`
- `unknown`

## 8. DeepSeek JSON Prompt Contract

Every DeepSeek call that returns structured project data should include:

```text
You must output valid json only. Do not include markdown. Follow this exact JSON shape: ...
```

And use API JSON mode where supported:

```python
response_format={"type": "json_object"}
```

Validation rule:

- parse JSON;
- validate required fields;
- reject unknown destructive actions;
- store raw model output for debugging;
- never execute model-suggested shell commands automatically.

## 9. Tool Call Boundary

If DeepSeek Tool Calls are used later, the model may request functions like:

- `search_pexels_videos(query, orientation, per_page)`
- `search_pixabay_videos(query, category, safesearch, per_page)`
- `rank_candidates(beat_id, candidates)`
- `build_timeline(approved_clips)`

But the local application must execute the function and inspect results.

The model must never directly:

- download YouTube content;
- publish media;
- overwrite files silently;
- delete source files;
- bypass rights checks.
