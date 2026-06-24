from __future__ import annotations

from typing import Any, Dict, List

from science_assembly.pipeline.approvals import approved_candidate_ids

JsonDict = Dict[str, Any]


def build_timeline(
    *,
    visual_beats: JsonDict,
    source_candidates: JsonDict,
    manual_approvals: JsonDict,
    title: str = "Science video assembly preview",
    language: str = "ru",
) -> JsonDict:
    """Build a draft timeline from approved candidates only."""

    project_id = str(visual_beats.get("project_id") or source_candidates.get("project_id") or "science_video_demo_001")
    approved_ids = approved_candidate_ids(manual_approvals)
    candidates_by_id = {
        str(candidate.get("candidate_id")): candidate for candidate in source_candidates.get("candidates", [])
    }

    narration: List[JsonDict] = []
    visuals: List[JsonDict] = []
    captions: List[JsonDict] = []
    cursor = 0.0

    for index, beat in enumerate(visual_beats.get("beats", []), start=1):
        beat_id = str(beat.get("beat_id"))
        duration = float(beat.get("duration_seconds") or 8)
        text = str(beat.get("narration_text") or "")
        start = cursor
        end = cursor + duration

        narration.append({"id": f"voice_{index:03d}", "beat_id": beat_id, "text": text, "start": round(start, 2), "end": round(end, 2)})
        captions.append({"id": f"cap_{index:03d}", "text": text, "start": round(start, 2), "end": round(end, 2)})

        approved_for_beat = [cid for cid in approved_ids if candidates_by_id.get(cid, {}).get("beat_id") == beat_id]
        if approved_for_beat:
            candidate = candidates_by_id[approved_for_beat[0]]
            visuals.append(
                {
                    "id": f"visual_{index:03d}",
                    "beat_id": beat_id,
                    "candidate_id": candidate.get("candidate_id"),
                    "source_url": candidate.get("source_url"),
                    "asset_url": candidate.get("asset_url"),
                    "timeline_start_seconds": round(start, 2),
                    "timeline_end_seconds": round(end, 2),
                    "fit_mode": "cover",
                    "approved_for_preview": True,
                    "approved_for_publication": False,
                }
            )
        cursor = end

    return {
        "project_id": project_id,
        "title": title,
        "language": language,
        "target_aspect_ratio": "16:9",
        "target_resolution": "1920x1080",
        "fps": 30,
        "tracks": {"voiceover": narration, "visuals": visuals, "captions": captions},
        "source_ledger_file": "source_ledger.json",
    }
