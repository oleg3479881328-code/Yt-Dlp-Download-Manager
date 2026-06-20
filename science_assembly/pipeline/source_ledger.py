from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

JsonDict = Dict[str, Any]


def build_source_ledger(*, timeline: JsonDict, source_candidates: JsonDict) -> JsonDict:
    project_id = str(timeline.get("project_id") or source_candidates.get("project_id") or "science_video_demo_001")
    candidates_by_id = {
        str(candidate.get("candidate_id")): candidate for candidate in source_candidates.get("candidates", [])
    }
    assets: List[JsonDict] = []
    for index, visual in enumerate(timeline.get("tracks", {}).get("visuals", []), start=1):
        candidate_id = str(visual.get("candidate_id"))
        candidate = candidates_by_id.get(candidate_id, {})
        assets.append(
            {
                "asset_id": f"asset_{index:03d}",
                "candidate_id": candidate_id,
                "beat_id": visual.get("beat_id"),
                "provider": candidate.get("provider"),
                "source_url": candidate.get("source_url"),
                "creator_name": candidate.get("creator_name"),
                "creator_url": candidate.get("creator_url"),
                "license_name": candidate.get("license_name"),
                "license_url": candidate.get("license_url"),
                "date_accessed": candidate.get("date_accessed"),
                "local_file": visual.get("source_file"),
                "usage_decision": "preview_only",
                "rights_review_status": "needs_review_before_publication",
                "notes": "Draft MVP ledger entry. Review provider terms before publication.",
            }
        )
    return {
        "project_id": project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "assets": assets,
    }
