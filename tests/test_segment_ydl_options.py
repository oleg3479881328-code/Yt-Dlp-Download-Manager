from __future__ import annotations

from pathlib import Path

from app.yt_service import build_ydl_options


def test_build_ydl_options_for_segment_uses_clip_template_and_ranges(tmp_path: Path) -> None:
    options = build_ydl_options(
        tmp_path,
        mode="video",
        quality="best",
        progress_hook=lambda payload: None,
        segment={
            "start": 65.0,
            "end": 95.0,
            "label": "hook",
            "section_expression": "*65-95",
        },
    )

    assert "clips" in options["outtmpl"]
    assert options["force_keyframes_at_cuts"] is True

    ranges = options["download_ranges"]({"id": "demo"}, object())
    assert ranges == [
        {
            "start_time": 65.0,
            "end_time": 95.0,
            "title": "hook",
            "index": 1,
        }
    ]
