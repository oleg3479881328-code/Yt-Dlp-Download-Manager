from __future__ import annotations

import re
from typing import Any, Dict, List

from science_assembly.ai.provider import AIProvider

JsonDict = Dict[str, Any]


class OfflineDemoProvider(AIProvider):
    """Deterministic no-network provider for shape testing.

    This is not a replacement for DeepSeek. It only lets the executor test the
    pipeline and file formats without API keys.
    """

    def extract_visual_beats(
        self,
        *,
        script_text: str,
        project_id: str,
        language: str,
        target_duration_seconds: int,
    ) -> JsonDict:
        sentences = _split_sentences(script_text)
        if not sentences:
            sentences = [script_text.strip() or "Sample educational narration."]
        beat_duration = max(5, min(12, target_duration_seconds // max(1, len(sentences))))
        beats: List[Dict[str, Any]] = []
        for index, sentence in enumerate(sentences[:12], start=1):
            keywords = _keywords(sentence)
            query_base = " ".join(keywords[:4]) or "science education nature"
            beats.append(
                {
                    "beat_id": f"beat_{index:03d}",
                    "script_segment_id": f"seg_{index:03d}",
                    "order": index,
                    "narration_text": sentence,
                    "visual_need": f"educational b-roll illustrating: {sentence[:140]}",
                    "visual_type": "b_roll",
                    "preferred_style": "real footage or clean educational animation",
                    "duration_seconds": beat_duration,
                    "search_queries": [
                        query_base,
                        f"{query_base} educational",
                        f"{query_base} science",
                    ],
                    "avoid": ["unrelated talking head", "low quality", "watermarked screen recording"],
                    "rights_requirement": "allowed_or_reviewed",
                    "importance": "high" if index <= 3 else "medium",
                }
            )
        return {
            "project_id": project_id,
            "source": "offline_demo_from_script",
            "language": language,
            "target_duration_seconds": target_duration_seconds,
            "beats": beats,
        }

    def rank_candidates(
        self, *, visual_beats: JsonDict, source_candidates: JsonDict, project_id: str) -> JsonDict:
        candidates_by_beat: Dict[str, List[Dict[str, Any]]] = {}
        for candidate in source_candidates.get("candidates", []):
            candidates_by_beat.setdefault(candidate.get("beat_id", "unknown"), []).append(candidate)

        rankings: List[Dict[str, Any]] = []
        for beat in visual_beats.get("beats", []):
            beat_id = beat.get("beat_id", "unknown")
            ranked: List[Dict[str, Any]] = []
            for index, candidate in enumerate(candidates_by_beat.get(beat_id, []), start=1):
                relevance = max(0.4, 0.9 - (index - 1) * 0.08)
                technical = 0.75 if candidate.get("asset_url") else 0.5
                rights = 0.55 if candidate.get("rights_status") != "allowed" else 0.9
                overall = round((relevance * 0.5) + (technical * 0.25) + (rights * 0.25), 2)
                ranked.append(
                    {
                        "candidate_id": candidate.get("candidate_id"),
                        "relevance_score": round(relevance, 2),
                        "technical_score": round(technical, 2),
                        "rights_score": round(rights, 2),
                        "overall_score": overall,
                        "why_it_matches": "Offline demo ranking based on search result order and available asset metadata.",
                        "mismatch_warnings": [],
                        "rights_warning": "Review provider terms before publication.",
                        "recommendation": "review",
                    }
                )
            rankings.append({"beat_id": beat_id, "ranked_candidates": ranked})
        return {"project_id": project_id, "rankings": rankings}

    def qa_review(self, *, timeline: JsonDict, source_ledger: JsonDict) -> JsonDict:
        warnings = []
        for asset in source_ledger.get("assets", []):
            if asset.get("rights_review_status") != "reviewed_ok":
                warnings.append(
                    {
                        "level": "medium",
                        "area": "rights",
                        "message": f"Asset {asset.get('asset_id')} needs rights review before publication.",
                    }
                )
        return {
            "status": "needs_review" if warnings else "ok",
            "warnings": warnings,
            "recommended_next_actions": ["Review provider terms before publication."],
        }


def _split_sentences(text: str) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?<=[.!?。！？])\s+|(?<=[.!?])\n+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _keywords(sentence: str) -> List[str]:
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]{4,}", sentence.lower())
    stop = {
        "это",
        "который",
        "которые",
        "через",
        "потому",
        "может",
        "about",
        "that",
        "with",
        "from",
        "this",
        "into",
    }
    return [word for word in words if word not in stop]
