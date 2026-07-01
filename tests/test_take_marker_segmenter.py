from pathlib import Path

from video_mix.core.models import Asset, MediaType, SegmenterName
from video_mix.core.segmenters import (
    FixedIntervalSegmenter,
    TakeMarkerSegmenter,
    build_take_marker_clips,
    ensure_take_marker_segmenter,
    group_marker_sample_times,
    plan_segments_for_assets,
)


def make_video_asset(path: Path, *, duration_ms: int = 11_000) -> Asset:
    return Asset(
        asset_id="asset_take_source",
        project_id="project_1",
        path=path,
        media_type=MediaType.VIDEO,
        duration_ms=duration_ms,
    )


def test_group_marker_sample_times_builds_marker_intervals() -> None:
    intervals = group_marker_sample_times(
        [3000, 3250, 7000, 7250, 7500],
        sample_interval_ms=250,
        min_marker_ms=250,
    )

    assert intervals == [(3000, 3500), (7000, 7750)]


def test_build_take_marker_clips_splits_video_into_takes(tmp_path: Path) -> None:
    asset = make_video_asset(tmp_path / "scene_with_10_takes.mp4")

    clips = build_take_marker_clips(
        asset,
        tmp_path / "clips",
        [(3000, 3400), (7000, 7400)],
        marker_trim_padding_ms=0,
    )

    assert [(clip.source_start_ms, clip.source_end_ms) for clip in clips] == [
        (0, 3000),
        (3400, 7000),
        (7400, 11_000),
    ]
    assert {clip.segmenter for clip in clips} == {SegmenterName.TAKE_MARKER}
    assert [clip.metadata["take_index"] for clip in clips] == [1, 2, 3]
    assert all(clip.metadata["take_marker"] == "VM_TAKE_BREAK_V1" for clip in clips)


def test_take_marker_segmenter_precedes_fixed_interval_fallback(tmp_path: Path, monkeypatch) -> None:
    asset = make_video_asset(tmp_path / "scene_with_marker.mp4", duration_ms=8000)
    take_marker = TakeMarkerSegmenter(marker_trim_padding_ms=0)
    monkeypatch.setattr(take_marker, "_detect_marker_intervals", lambda asset: [(3000, 3400)])

    clips = plan_segments_for_assets(
        [asset],
        tmp_path / "work_clips",
        segmenters=[take_marker, FixedIntervalSegmenter(clip_ms=2000)],
    )

    assert [(clip.source_start_ms, clip.source_end_ms) for clip in clips] == [(0, 3000), (3400, 8000)]
    assert all(clip.segmenter == SegmenterName.TAKE_MARKER for clip in clips)
    assert all("segmenter_fallback" not in clip.metadata for clip in clips)


def test_take_marker_segmenter_is_added_before_explicit_fallbacks() -> None:
    segmenters = ensure_take_marker_segmenter([FixedIntervalSegmenter(clip_ms=2000)])

    assert segmenters[0].name == SegmenterName.TAKE_MARKER
    assert segmenters[1].name == SegmenterName.FIXED_INTERVAL
