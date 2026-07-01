from pathlib import Path

import pytest

from video_mix.core.asset_scan import detect_media_type, stable_id
from video_mix.core.models import Asset, CandidateStatus, Clip, MediaType, Orientation, Project, SegmenterName
from video_mix.core.review import (
    build_review_html,
    build_thumbnail_command,
    collect_existing_thumbnails,
    write_review_html,
)
from video_mix.core.storage import build_asset, build_candidate, build_clip, to_jsonable
from video_mix.service import (
    _build_video_segment_command,
    output_dimensions,
    quick_mix_source_materials,
    resolve_work_dir,
)


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


def test_resolve_work_dir_defaults_under_source_dir(tmp_path: Path) -> None:
    source_dir = tmp_path / "input"
    source_dir.mkdir()

    resolved = resolve_work_dir(source_dir)

    assert resolved == (source_dir / "_video_mix_work").resolve()


def test_resolve_work_dir_preserves_relative_cli_semantics(tmp_path: Path) -> None:
    source_dir = tmp_path / "input"
    source_dir.mkdir()
    cwd = tmp_path / "workspace"
    cwd.mkdir()

    resolved = resolve_work_dir(source_dir, "video_mix_validation/work", cwd=cwd)

    assert resolved == (cwd / "video_mix_validation" / "work").resolve()


def test_output_dimensions_support_vertical_and_horizontal() -> None:
    assert output_dimensions("vertical") == (1080, 1920)
    assert output_dimensions("horizontal") == (1920, 1080)

    with pytest.raises(ValueError, match="Unsupported output_orientation"):
        output_dimensions("square")


def test_video_segment_command_uses_horizontal_output_dimensions(tmp_path: Path) -> None:
    asset = Asset(
        asset_id="asset_1",
        project_id="project_1",
        path=tmp_path / "clip.mp4",
        media_type=MediaType.VIDEO,
        duration_ms=4000,
    )

    command = _build_video_segment_command(
        asset,
        tmp_path / "segment.mp4",
        start_ms=0,
        duration_ms=3000,
        ffmpeg_path="ffmpeg",
        output_width=1920,
        output_height=1080,
    )

    assert "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30" in command


def test_quick_mix_source_materials_supports_videos_and_photos(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    video_path = source_dir / "clip.mp4"
    photo_path = source_dir / "photo.jpg"
    video_path.write_bytes(b"video")
    photo_path.write_bytes(b"photo")

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            if asset.media_type == MediaType.VIDEO:
                asset.duration_ms = 4000
                asset.width = 1080
                asset.height = 1920
                asset.fps = 30.0
                asset.orientation = Orientation.VERTICAL
                asset.probe_status = "ok"
            else:
                asset.probe_status = "skipped_photo"
        return assets

    rendered_segments: list[Path] = []
    rendered_outputs: list[Path] = []
    rendered_dimensions: list[tuple[int, int]] = []

    def fake_render_segment(
        asset: Asset,
        output_path: Path,
        *,
        start_ms: int,
        duration_ms: int,
        ffmpeg_path: str,
        output_width: int = 1080,
        output_height: int = 1920,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(f"{asset.media_type}:{start_ms}:{duration_ms}".encode())
        rendered_segments.append(output_path)
        rendered_dimensions.append((output_width, output_height))

    def fake_render_output(segment_paths: list[Path], output_path: Path, ffmpeg_path: str) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes("\n".join(path.name for path in segment_paths).encode("utf-8"))
        rendered_outputs.append(output_path)

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", fake_render_segment)
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", fake_render_output)

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=6,
        output_count=2,
        project_name="Quick Mix Validation",
        work_dir=str(tmp_path / "work"),
        output_orientation="horizontal",
    )

    assert result["generated_count"] == 2
    assert result["video_count"] == 1
    assert result["image_count"] == 1
    assert result["photo_support"] is True
    assert result["output_orientation"] == "horizontal"
    assert result["output_width"] == 1920
    assert result["output_height"] == 1080
    assert result["output_paths"] == ["exports/quick_mix_001.mp4", "exports/quick_mix_002.mp4"]
    assert len(rendered_segments) >= 2
    assert len(rendered_outputs) == 2
    assert set(rendered_dimensions) == {(1920, 1080)}
