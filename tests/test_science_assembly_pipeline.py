from __future__ import annotations

from science_assembly.ai.json_validation import (
    validate_manual_approvals,
    validate_ranked_candidates,
    validate_source_candidates,
    validate_visual_beats,
)
from science_assembly.ai.offline_demo_provider import OfflineDemoProvider
from science_assembly.pipeline.approvals import build_manual_approval_template
from science_assembly.pipeline.source_ledger import build_source_ledger
from science_assembly.pipeline.timeline_builder import build_timeline
from science_assembly.sources.pexels import PexelsVideoSearchAdapter


def test_offline_provider_generates_valid_visual_beats() -> None:
    provider = OfflineDemoProvider()
    data = provider.extract_visual_beats(
        script_text="Фотосинтез начинается в листе. Хлорофилл поглощает свет. Растение выделяет кислород.",
        project_id="test_project",
        language="ru",
        target_duration_seconds=30,
    )
    validate_visual_beats(data)
    assert data["project_id"] == "test_project"
    assert len(data["beats"]) >= 3


def test_approval_timeline_and_ledger_flow() -> None:
    visual_beats = {
        "project_id": "test_project",
        "beats": [
            {
                "beat_id": "beat_001",
                "order": 1,
                "narration_text": "Leaf in sunlight.",
                "visual_need": "green leaf sunlight",
                "visual_type": "b_roll",
                "duration_seconds": 8,
                "search_queries": ["green leaf sunlight"],
                "rights_requirement": "allowed_or_reviewed",
            }
        ],
    }
    candidates = {
        "project_id": "test_project",
        "candidates": [
            {
                "candidate_id": "pexels_b001_c001",
                "beat_id": "beat_001",
                "provider": "pexels",
                "source_url": "https://example.com/source",
                "asset_url": "https://example.com/asset.mp4",
                "creator_name": "Creator",
                "creator_url": "https://example.com/creator",
                "license_name": "Provider terms",
                "license_url": "https://example.com/license",
                "query": "green leaf sunlight",
                "rights_status": "provider_terms_review_needed",
                "date_accessed": "2026-06-20",
            }
        ],
    }
    ranked = {
        "project_id": "test_project",
        "rankings": [
            {
                "beat_id": "beat_001",
                "ranked_candidates": [
                    {"candidate_id": "pexels_b001_c001", "overall_score": 0.8, "recommendation": "review"}
                ],
            }
        ],
    }
    validate_visual_beats(visual_beats)
    validate_source_candidates(candidates)
    validate_ranked_candidates(ranked)

    approvals = build_manual_approval_template(ranked)
    approvals["approvals"][0]["approval_status"] = "approved"
    validate_manual_approvals(approvals)

    timeline = build_timeline(visual_beats=visual_beats, source_candidates=candidates, manual_approvals=approvals)
    assert len(timeline["tracks"]["visuals"]) == 1
    assert timeline["tracks"]["visuals"][0]["candidate_id"] == "pexels_b001_c001"

    ledger = build_source_ledger(timeline=timeline, source_candidates=candidates)
    assert len(ledger["assets"]) == 1
    assert ledger["assets"][0]["usage_decision"] == "preview_only"


def test_timeline_uses_only_approved_candidates() -> None:
    visual_beats = {
        "project_id": "test_project",
        "beats": [
            {
                "beat_id": "beat_001",
                "order": 1,
                "narration_text": "Leaf in sunlight.",
                "visual_need": "green leaf sunlight",
                "visual_type": "b_roll",
                "duration_seconds": 8,
                "search_queries": ["green leaf sunlight"],
                "rights_requirement": "allowed_or_reviewed",
            }
        ],
    }
    candidates = {
        "project_id": "test_project",
        "candidates": [
            {
                "candidate_id": "candidate_001",
                "beat_id": "beat_001",
                "provider": "pexels",
                "source_url": "https://example.com/source",
                "query": "green leaf sunlight",
                "rights_status": "provider_terms_review_needed",
                "date_accessed": "2026-06-20",
            }
        ],
    }
    approvals = {
        "project_id": "test_project",
        "approvals": [{"beat_id": "beat_001", "candidate_id": "candidate_001", "approval_status": "rejected"}],
    }
    timeline = build_timeline(visual_beats=visual_beats, source_candidates=candidates, manual_approvals=approvals)
    assert timeline["tracks"]["visuals"] == []


class FakePexelsAdapter(PexelsVideoSearchAdapter):
    def __init__(self) -> None:
        pass

    def _search(self, *, query: str, per_page: int, orientation: str | None):
        return [
            {"id": f"{query}-1", "url": f"https://example.com/{query}/1", "video_files": []},
            {"id": f"{query}-2", "url": f"https://example.com/{query}/2", "video_files": []},
        ]


def test_pexels_candidate_ids_are_unique_across_multiple_queries() -> None:
    adapter = FakePexelsAdapter()
    beat = {"beat_id": "beat_001", "search_queries": ["leaf", "chlorophyll"]}
    candidates = adapter.search_for_beat(beat=beat, beat_index=1, per_query=2)
    ids = [candidate["candidate_id"] for candidate in candidates]
    assert len(ids) == 4
    assert len(set(ids)) == 4
