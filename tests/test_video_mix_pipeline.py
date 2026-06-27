from pathlib import Path

from video_mix.core.asset_scan import detect_media_type, stable_id
from video_mix.core.models import CandidateStatus, Clip, MediaType, Orientation, Project, SegmenterName
from video_mix.core.review import (
    build_review_html,
    build_thumbnail_command,
    collect_existing_thumbnails,
    write_review_html,
)
from video_mix.core.storage import build_asset, build_candidate, build_clip, to_jsonable


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


def test_review_html_contains_candidate_metadata_and_commands(tmp_path: Path) -> None:
    project = Project(project_id="project_1", name="Wedding Validation", root_path=tmp_path, industry_pack="wedding")
    asset = build_asset(
        {
            "asset_id": "asset_1",
            "project_id": "project_1",
            "path": str(tmp_path / "rings_detail.mp4"),
            "media_type": MediaType.VIDEO.value,
            "duration_ms": 4000,
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "orientation": Orientation.VERTICAL.value,
            "has_audio": True,
            "probe_status": "ok",
            "quality_score": 80.0,
            "metadata": {},
        }
    )
    clip = build_clip(
        {
            "clip_id": "clip_1",
            "project_id": "project_1",
            "asset_id": "asset_1",
            "source_path": str(tmp_path / "rings_detail.mp4"),
            "source_start_ms": 0,
            "source_end_ms": 3000,
            "segmenter": SegmenterName.FIXED_INTERVAL.value,
            "working_path": str(tmp_path / "clip_1.mp4"),
            "tags": ["details", "rings"],
            "quality_score": 88.0,
            "usable": True,
            "metadata": {},
        }
    )
    candidate = build_candidate(
        {
            "candidate_id": "cand_1",
            "project_id": "project_1",
            "pack_id": "wedding",
            "template_id": "romantic_story",
            "status": CandidateStatus.GENERATED.value,
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
            "warnings": ["missing_slot:closing"],
            "review_notes": "",
        }
    )

    html = build_review_html(
        project,
        [candidate],
        [clip],
        [asset],
        tmp_path,
        {"clip_1": "thumbnails/clip_1.jpg"},
        {},
    )
    assert "VIDEO MIX Review" in html
    assert "cand_1" in html
    assert "romantic_story" in html
    assert "rings_detail.mp4" in html
    assert "details, rings" in html
    assert "python -m video_mix.cli approve" in html
    assert 'src="thumbnails/clip_1.jpg"' in html

    review_path, _, _ = write_review_html(project, [candidate], [clip], [asset], tmp_path, ffmpeg_path="ffmpeg")
    assert review_path.exists()
    assert "cand_1" in review_path.read_text(encoding="utf-8")


def test_build_thumbnail_command_uses_clip_midpoint(tmp_path: Path) -> None:
    clip = Clip(
        clip_id="clip_1",
        project_id="project_1",
        asset_id="asset_1",
        source_path=tmp_path / "demo.mp4",
        source_start_ms=2000,
        source_end_ms=6000,
        segmenter=SegmenterName.FIXED_INTERVAL,
    )
    command = build_thumbnail_command(clip, tmp_path / "thumb.jpg")
    assert command[:5] == ["ffmpeg", "-y", "-ss", "4.000", "-i"]


def test_collect_existing_thumbnails_uses_local_files(tmp_path: Path) -> None:
    clip = Clip(
        clip_id="clip_1",
        project_id="project_1",
        asset_id="asset_1",
        source_path=tmp_path / "demo.mp4",
        source_start_ms=0,
        source_end_ms=3000,
        segmenter=SegmenterName.FIXED_INTERVAL,
    )
    thumbnails_dir = tmp_path / "reports" / "thumbnails"
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    (thumbnails_dir / "clip_1.jpg").write_bytes(b"jpg")

    lookup, warnings = collect_existing_thumbnails([clip], tmp_path)

    assert lookup == {"clip_1": "thumbnails/clip_1.jpg"}
    assert warnings == {}
