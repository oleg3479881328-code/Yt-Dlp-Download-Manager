from pathlib import Path

import pytest

from video_mix.core.models import Asset, MediaType
from video_mix.service import (
    _build_video_segment_command,
    _video_filter,
    _write_caption_text_file,
    normalize_caption_position,
    normalize_caption_text,
)


def test_normalize_caption_text_trims_and_normalizes_newlines() -> None:
    assert normalize_caption_text("  Line 1\r\nLine 2  ") == "Line 1\nLine 2"
    assert normalize_caption_text(None) == ""


def test_caption_position_validation() -> None:
    assert normalize_caption_position(None) == "bottom"
    assert normalize_caption_position("TOP") == "top"
    with pytest.raises(ValueError, match="Unsupported caption_position"):
        normalize_caption_position("left")


def test_video_filter_without_caption_keeps_scale_crop_only() -> None:
    assert _video_filter(1080, 1920) == "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30"


def test_video_filter_with_caption_adds_drawtext_filter(tmp_path: Path) -> None:
    caption_path = tmp_path / "caption.txt"
    filter_text = _video_filter(1080, 1920, caption_text_path=caption_path, caption_position="bottom")

    assert "drawtext=" in filter_text
    assert "textfile='" in filter_text
    assert "fontcolor=white" in filter_text
    assert "boxcolor=black@0.58" in filter_text
    assert "y=h-text_h-" in filter_text


def test_write_caption_text_file_returns_none_for_blank_text(tmp_path: Path) -> None:
    assert _write_caption_text_file(tmp_path, "  ") is None


def test_write_caption_text_file_persists_caption_text(tmp_path: Path) -> None:
    caption_path = _write_caption_text_file(tmp_path, "  Wedding Day  ")

    assert caption_path is not None
    assert caption_path.read_text(encoding="utf-8") == "Wedding Day"


def test_video_segment_command_can_overlay_caption_textfile(tmp_path: Path) -> None:
    asset = Asset(
        asset_id="asset_1",
        project_id="project_1",
        path=tmp_path / "source.mp4",
        media_type=MediaType.VIDEO,
        duration_ms=5000,
    )
    caption_path = tmp_path / "caption.txt"
    command = _build_video_segment_command(
        asset,
        tmp_path / "out.mp4",
        start_ms=0,
        duration_ms=3000,
        ffmpeg_path="ffmpeg",
        caption_text_path=caption_path,
        caption_position="top",
    )

    assert "drawtext=" in command
    assert any("y=40" in part for part in command)
