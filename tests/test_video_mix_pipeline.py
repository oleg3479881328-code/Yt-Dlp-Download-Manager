from pathlib import Path

from video_mix.core.asset_scan import detect_media_type, stable_id
from video_mix.core.models import CandidateStatus, Clip, SegmenterName
from video_mix.core.storage import build_candidate, to_jsonable


def test_detect_media_type_video() -> None:
    assert detect_media_type(Path("rings_detail.mp4")).value == "video"


def test_stable_id_is_repeatable() -> None:
    assert stable_id("asset", "abc") == stable_id("asset", "abc")


def test_candidate_round_trip_from_jsonable() -> None:
    payload = {
        "candidate_id": "cand_1",
        "project_id": "project_1",
        "pack_id": "wedding",
        "template_id": "romantic_story",
        "status": CandidateStatus.APPROVED.value,
        "score": 88.0,
        "duration_ms": 3000,
        "tracks": [
            {
                "track_id": "video_main",
                "track_type": "video",
                "clips": [
                    {
                        "clip_id": "clip_1",
                        "slot_id": "opening_detail",
                        "source_asset_id": "asset_1",
                        "source_start_ms": 0,
                        "source_end_ms": 3000,
                        "timeline_start_ms": 0,
                        "timeline_end_ms": 3000,
                    }
                ],
                "overlays": [],
            }
        ],
        "platform_preset": {"width": 1080, "height": 1920, "fps": 30, "format": "mp4"},
        "warnings": [],
        "review_notes": "ok",
    }
    candidate = build_candidate(payload)
    assert candidate.status == CandidateStatus.APPROVED
    assert to_jsonable(candidate)["template_id"] == "romantic_story"


def test_clip_duration_property() -> None:
    clip = Clip(
        clip_id="clip_1",
        project_id="project_1",
        asset_id="asset_1",
        source_path=Path("demo.mp4"),
        source_start_ms=500,
        source_end_ms=3500,
        segmenter=SegmenterName.FIXED_INTERVAL,
    )
    assert clip.duration_ms == 3000
