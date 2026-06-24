from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


JsonDict = Dict[str, Any]


class JsonValidationError(ValueError):
    pass


def load_json(path: str | Path) -> JsonDict:
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise JsonValidationError(f"Expected JSON object in {path}")
    return data


def write_json(path: str | Path, data: JsonDict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def require_keys(obj: JsonDict, keys: Iterable[str], *, context: str) -> None:
    missing = [key for key in keys if key not in obj]
    if missing:
        raise JsonValidationError(f"Missing required keys in {context}: {', '.join(missing)}")


def ensure_list(obj: JsonDict, key: str, *, context: str) -> List[Any]:
    value = obj.get(key)
    if not isinstance(value, list):
        raise JsonValidationError(f"Expected list at {context}.{key}")
    return value


def validate_visual_beats(data: JsonDict) -> None:
    require_keys(data, ["project_id", "beats"], context="visual_beats")
    for index, beat in enumerate(ensure_list(data, "beats", context="visual_beats")):
        if not isinstance(beat, dict):
            raise JsonValidationError(f"visual_beats.beats[{index}] must be an object")
        require_keys(
            beat,
            [
                "beat_id",
                "order",
                "narration_text",
                "visual_need",
                "visual_type",
                "duration_seconds",
                "search_queries",
                "rights_requirement",
            ],
            context=f"visual_beats.beats[{index}]",
        )


def validate_source_candidates(data: JsonDict) -> None:
    require_keys(data, ["project_id", "candidates"], context="source_candidates")
    for index, candidate in enumerate(ensure_list(data, "candidates", context="source_candidates")):
        if not isinstance(candidate, dict):
            raise JsonValidationError(f"source_candidates.candidates[{index}] must be an object")
        require_keys(
            candidate,
            ["candidate_id", "beat_id", "provider", "source_url", "query", "rights_status", "date_accessed"],
            context=f"source_candidates.candidates[{index}]",
        )


def validate_ranked_candidates(data: JsonDict) -> None:
    require_keys(data, ["project_id", "rankings"], context="ranked_candidates")
    for index, ranking in enumerate(ensure_list(data, "rankings", context="ranked_candidates")):
        if not isinstance(ranking, dict):
            raise JsonValidationError(f"ranked_candidates.rankings[{index}] must be an object")
        require_keys(ranking, ["beat_id", "ranked_candidates"], context=f"ranked_candidates.rankings[{index}]")


def validate_manual_approvals(data: JsonDict) -> None:
    require_keys(data, ["project_id", "approvals"], context="manual_approvals")
    for index, approval in enumerate(ensure_list(data, "approvals", context="manual_approvals")):
        if not isinstance(approval, dict):
            raise JsonValidationError(f"manual_approvals.approvals[{index}] must be an object")
        require_keys(
            approval,
            ["beat_id", "candidate_id", "approval_status"],
            context=f"manual_approvals.approvals[{index}]",
        )
