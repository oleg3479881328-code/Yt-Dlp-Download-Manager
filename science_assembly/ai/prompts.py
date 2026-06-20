from __future__ import annotations

import json
from typing import Any, Dict


VISUAL_BEATS_SCHEMA_EXAMPLE: Dict[str, Any] = {
    "project_id": "science_video_demo_001",
    "source": "ai_generated_from_script",
    "language": "ru",
    "target_duration_seconds": 90,
    "beats": [
        {
            "beat_id": "beat_001",
            "script_segment_id": "seg_001",
            "order": 1,
            "narration_text": "...",
            "visual_need": "clear visual description for b-roll search",
            "visual_type": "b_roll",
            "preferred_style": "real footage or clean educational animation",
            "duration_seconds": 8,
            "search_queries": ["query one", "query two", "query three"],
            "avoid": ["low quality", "unrelated talking head"],
            "rights_requirement": "allowed_or_reviewed",
            "importance": "high",
        }
    ],
}


RANKED_CANDIDATES_SCHEMA_EXAMPLE: Dict[str, Any] = {
    "project_id": "science_video_demo_001",
    "rankings": [
        {
            "beat_id": "beat_001",
            "ranked_candidates": [
                {
                    "candidate_id": "cand_001",
                    "relevance_score": 0.87,
                    "technical_score": 0.78,
                    "rights_score": 0.5,
                    "overall_score": 0.74,
                    "why_it_matches": "short explanation",
                    "mismatch_warnings": ["warning if any"],
                    "rights_warning": "review provider terms before publication",
                    "recommendation": "review",
                }
            ],
        }
    ],
}


QA_REVIEW_SCHEMA_EXAMPLE: Dict[str, Any] = {
    "status": "needs_review",
    "warnings": [
        {
            "level": "medium",
            "area": "rights",
            "message": "Some assets are preview-only until rights review is complete.",
        }
    ],
    "recommended_next_actions": ["Review provider terms before publication."],
}


def visual_beats_prompt(*, script_text: str, project_id: str, language: str, target_duration_seconds: int) -> str:
    example = json.dumps(VISUAL_BEATS_SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)
    return f"""
You are designing a rights-aware educational video assembly plan.
Return valid json only. Do not include markdown.

Task:
Convert the narration script into visual beats for B-roll or educational visuals.
Each beat should cover about 5-12 seconds.
Generate practical search queries for stock video APIs such as Pexels or Pixabay.
Do not suggest downloading or reusing YouTube content unless it is explicitly rights-approved.

Project id: {project_id}
Language: {language}
Target duration seconds: {target_duration_seconds}

Required json shape example:
{example}

Narration script:
{script_text}
""".strip()


def rank_candidates_prompt(*, visual_beats: Dict[str, Any], source_candidates: Dict[str, Any], project_id: str) -> str:
    example = json.dumps(RANKED_CANDIDATES_SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)
    beats = json.dumps(visual_beats, ensure_ascii=False, indent=2)
    candidates = json.dumps(source_candidates, ensure_ascii=False, indent=2)
    return f"""
You are ranking B-roll candidates for an educational video.
Return valid json only. Do not include markdown.

Rules:
- Rank relevance, technical usability, and rights risk separately.
- Never mark unclear rights as safe.
- If provider terms need review, set recommendation to review or needs_rights_review.
- Prefer visuals that directly explain the narration.

Project id: {project_id}

Required json shape example:
{example}

Visual beats json:
{beats}

Source candidates json:
{candidates}
""".strip()


def qa_review_prompt(*, timeline: Dict[str, Any], source_ledger: Dict[str, Any]) -> str:
    example = json.dumps(QA_REVIEW_SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)
    timeline_json = json.dumps(timeline, ensure_ascii=False, indent=2)
    ledger_json = json.dumps(source_ledger, ensure_ascii=False, indent=2)
    return f"""
You are reviewing an educational video assembly plan before rendering or publication.
Return valid json only. Do not include markdown.

Check:
- missing source ledger entries;
- assets not approved for publication;
- visual mismatch risks;
- caption or narration timing issues;
- rights review warnings.

Required json shape example:
{example}

Timeline json:
{timeline_json}

Source ledger json:
{ledger_json}
""".strip()
