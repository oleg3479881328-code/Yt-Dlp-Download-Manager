from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

JsonDict = Dict[str, Any]


def build_manual_approval_template(ranked_candidates: JsonDict, *, max_per_beat: int = 3) -> JsonDict:
    """Create a review file that the owner/developer can edit by hand.

    The timeline builder must use only entries changed to `approved`.
    """

    project_id = str(ranked_candidates.get("project_id", "science_video_demo_001"))
    approvals: List[JsonDict] = []
    for ranking in ranked_candidates.get("rankings", []):
        beat_id = ranking.get("beat_id")
        for candidate in (ranking.get("ranked_candidates") or [])[:max_per_beat]:
            approvals.append(
                {
                    "beat_id": beat_id,
                    "candidate_id": candidate.get("candidate_id"),
                    "approval_status": "pending_review",
                    "approved_by": None,
                    "approved_at": None,
                    "overall_score": candidate.get("overall_score"),
                    "recommendation": candidate.get("recommendation"),
                    "notes": "Change approval_status to approved/rejected/needs_rights_review.",
                }
            )
    return {
        "project_id": project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "instructions": "Edit approval_status. Only approved items enter timeline.json.",
        "approvals": approvals,
    }


def approved_candidate_ids(manual_approvals: JsonDict) -> set[str]:
    ids: set[str] = set()
    for approval in manual_approvals.get("approvals", []):
        if approval.get("approval_status") == "approved" and approval.get("candidate_id"):
            ids.add(str(approval["candidate_id"]))
    return ids
