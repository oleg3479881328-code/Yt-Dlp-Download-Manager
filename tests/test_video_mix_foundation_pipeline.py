from __future__ import annotations

from pathlib import Path

from video_mix.analysis.foundation import analyze_project_scenes
from video_mix.core.models import Asset, MediaType, Orientation, Project, SegmenterName
from video_mix.core.segmenters import FixedIntervalSegmenter, PySceneDetectSegmenter, plan_asset_segments
from video_mix.core.storage import save_assets, save_project
from video_mix.proxy_pipeline import save_proxy_manifest
from video_mix.publishing.foundation import build_publishing_package
from video_mix.quality.foundation import build_quality_report
from video_mix.rendering.foundation import render_foundation_outputs


def test_analysis_prefers_ready_proxy_and_writes_keyframe(monkeypatch, tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    source_dir = tmp_path / "source"
    reports_dir = work_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)
    original_path = source_dir / "clip.mp4"
    proxy_path = work_dir / "video_proxies" / "asset_1.proxy.mp4"
    original_path.write_bytes(b"original")
    proxy_path.parent.mkdir(parents=True, exist_ok=True)
    proxy_path.write_bytes(b"proxy")
    save_project(work_dir, Project("project_1", "Demo", source_dir))
    save_assets(
        work_dir,
        [
            Asset(
                asset_id="asset_1",
                project_id="project_1",
                path=original_path,
                media_type=MediaType.VIDEO,
                duration_ms=4000,
                width=1080,
                height=1920,
                fps=30.0,
                orientation=Orientation.VERTICAL,
                has_audio=True,
                probe_status="ok",
            )
        ],
    )
    save_proxy_manifest(
        work_dir,
        {
            "entries": {
                "asset_1": {
                    "status": "ready",
                    "proxy_path": "video_proxies/asset_1.proxy.mp4",
                }
            }
        },
    )

    captured_paths: list[Path] = []

    def _plan_segments_for_assets(assets, _output_dir, segmenters=None):
        captured_paths.extend(asset.path for asset in assets)
        asset = assets[0]
        from video_mix.core.models import Clip, SegmenterName

        return [
            Clip(
                clip_id="clip_1",
                project_id="project_1",
                asset_id="asset_1",
                source_path=asset.path,
                source_start_ms=0,
                source_end_ms=1700,
                segmenter=SegmenterName.PYSCENEDETECT,
                metadata={"scene_detected": True},
            )
        ]

    keyframe_targets: list[Path] = []

    monkeypatch.setattr("video_mix.analysis.foundation.plan_segments_for_assets", _plan_segments_for_assets)
    monkeypatch.setattr("video_mix.analysis.foundation.probe_assets", lambda assets, ffprobe_path="ffprobe": assets)
    monkeypatch.setattr("video_mix.analysis.foundation.score_assets", lambda assets: assets)
    monkeypatch.setattr("video_mix.analysis.foundation.score_clips", lambda clips, assets: clips)
    preview_targets: list[Path] = []
    monkeypatch.setattr(
        "video_mix.analysis.foundation._extract_keyframe",
        lambda _source_path, keyframe_path, _midpoint_ms, _ffmpeg_path: (keyframe_path.parent.mkdir(parents=True, exist_ok=True), keyframe_path.write_bytes(b"jpg"), keyframe_targets.append(keyframe_path)),
    )
    monkeypatch.setattr(
        "video_mix.analysis.foundation._extract_preview_clip",
        lambda _source_path, preview_path, _start_ms, _end_ms, _ffmpeg_path: (preview_path.parent.mkdir(parents=True, exist_ok=True), preview_path.write_bytes(b"preview"), preview_targets.append(preview_path)),
    )

    class _StoreStub:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def upsert_analysis_run(self, **_kwargs) -> None:
            return None

        def upsert_scene(self, **_kwargs) -> None:
            return None

    monkeypatch.setattr("video_mix.analysis.foundation.VideoMixFoundationStore", _StoreStub)

    result = analyze_project_scenes(work_dir, ffprobe_path="ffprobe", ffmpeg_path="ffmpeg", prefer_pyscenedetect=True)

    assert captured_paths == [proxy_path.resolve()]
    assert result.scene_count == 1
    assert keyframe_targets and keyframe_targets[0].exists()
    assert preview_targets and preview_targets[0].exists()
    assert result.scenes[0]["keyframe_path"].endswith(".jpg")
    assert result.scenes[0]["preview_path"].endswith(".mp4")
    assert result.scenes[0]["score_json"]["used_proxy_for_analysis"] is True
    assert result.scenes[0]["score_json"]["measured_quality_score"] >= 0
    assert result.scenes[0]["detector_json"]["segmenter"] == SegmenterName.PYSCENEDETECT.value


def test_render_foundation_outputs_adds_opening_closing_and_cover(monkeypatch, tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    asset_path = tmp_path / "asset.mp4"
    opening_path = tmp_path / "opening.mp4"
    closing_path = tmp_path / "closing.mp4"
    for path in (asset_path, opening_path, closing_path):
        path.write_bytes(b"video")

    from video_mix.core.models import Asset

    monkeypatch.setattr(
        "video_mix.rendering.foundation.load_assets",
        lambda _work_dir: [
            Asset(
                asset_id="asset_1",
                project_id="project_1",
                path=asset_path,
                media_type=MediaType.VIDEO,
                duration_ms=5000,
                width=1080,
                height=1920,
                fps=30.0,
                orientation=Orientation.VERTICAL,
                has_audio=True,
                probe_status="ok",
            )
        ],
    )
    monkeypatch.setattr(
        "video_mix.rendering.foundation._build_optional_media_asset",
        lambda path, _ffprobe_path: Asset(
            asset_id=path.stem,
            project_id="project_1",
            path=path,
            media_type=MediaType.VIDEO,
            duration_ms=3000,
            width=1080,
            height=1920,
            fps=30.0,
            orientation=Orientation.VERTICAL,
            has_audio=True,
            probe_status="ok",
        ),
    )
    rendered_segments: list[tuple[Path, int]] = []
    monkeypatch.setattr(
        "video_mix.rendering.foundation._render_quick_mix_segment",
        lambda _asset, segment_path, start_ms, duration_ms, ffmpeg_path="ffmpeg": (segment_path.parent.mkdir(parents=True, exist_ok=True), segment_path.write_bytes(b"segment"), rendered_segments.append((segment_path, duration_ms))),
    )
    monkeypatch.setattr(
        "video_mix.rendering.foundation._render_quick_mix_output",
        lambda segment_paths, output_path, ffmpeg_path, music_path=None, music_start_ms=0: (output_path.parent.mkdir(parents=True, exist_ok=True), output_path.write_bytes(b"output")),
    )

    outputs = render_foundation_outputs(
        work_dir=work_dir,
        generation_id="foundation_demo",
        selected_plans=[
            {
                "plan_id": "plan_001",
                "requested_duration_ms": 10000,
                "items": [
                    {
                        "asset_id": "asset_1",
                        "source_start_ms": 0,
                        "source_end_ms": 1200,
                        "metadata_json": {"keyframe_path": "reports/scene_keyframes/clip_1.jpg"},
                    }
                ],
            }
        ],
        opening_media_paths=[str(opening_path)],
        closing_media_paths=[str(closing_path)],
        use_closing_duration=True,
    )

    assert len(rendered_segments) == 3
    assert outputs[0]["cover_source"] == "reports/scene_keyframes/clip_1.jpg"


def test_build_publishing_package_writes_valid_fallback_jpeg(tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    output_dir = work_dir / "foundation_generations" / "foundation_demo" / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    mp4_path = output_dir / "reel_01.mp4"
    mp4_path.write_bytes(b"mp4")

    package = build_publishing_package(
        work_dir=work_dir,
        generation_id="foundation_demo",
        outputs=[
            {
                "output_path": "foundation_generations/foundation_demo/exports/reel_01.mp4",
                "metadata": {},
                "plan": {},
                "quality_report": {},
            }
        ],
    )

    cover_path = work_dir / package["relative_package_dir"] / "cover_01.jpg"
    assert cover_path.exists()
    assert cover_path.read_bytes().startswith(b"\xff\xd8\xff")


def test_build_quality_report_flags_gaps_and_black_frames(monkeypatch, tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    output_path = work_dir / "exports" / "reel_01.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"mp4")

    monkeypatch.setattr(
        "video_mix.quality.foundation._ffprobe_payload",
        lambda _path, _ffprobe_path: {
            "format": {"duration": "5.0"},
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920},
                {"codec_type": "audio"},
            ],
        },
    )
    monkeypatch.setattr("video_mix.quality.foundation._sha256_file", lambda _path: "sha256-demo")
    monkeypatch.setattr("video_mix.quality.foundation._detect_black_segments", lambda _path, _ffmpeg_path: [{"start_s": 0.0, "end_s": 0.3, "duration_s": 0.3}])
    monkeypatch.setattr("video_mix.quality.foundation._detect_freeze_segments", lambda _path, _ffmpeg_path: [])
    monkeypatch.setattr("video_mix.quality.foundation._detect_similar_segments", lambda *_args, **_kwargs: [])

    class _StoreStub:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def upsert_quality_report(self, **_kwargs) -> None:
            return None

        def upsert_render_provenance(self, **_kwargs) -> None:
            return None

    monkeypatch.setattr("video_mix.quality.foundation.VideoMixFoundationStore", _StoreStub)

    report = build_quality_report(
        work_dir=work_dir,
        project_id="project_1",
        plan={
            "plan_id": "plan_1",
            "requested_duration_ms": 5000,
            "items": [
                {"asset_id": "asset_1", "timeline_start_ms": 0, "timeline_end_ms": 1000, "metadata_json": {"source_path": "originals/a.mp4"}, "source_start_ms": 0, "source_end_ms": 1000},
                {"asset_id": "asset_2", "timeline_start_ms": 1500, "timeline_end_ms": 2500, "metadata_json": {"source_path": "originals/b.mp4"}, "source_start_ms": 0, "source_end_ms": 1000},
            ],
        },
        output_path=output_path,
    )

    assert report["status"] == "qc_failed"
    assert report["findings"]["timeline_gaps_detected"] is True
    assert report["findings"]["black_segment_count"] == 1


def test_build_quality_report_flags_similar_segments(monkeypatch, tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    output_path = work_dir / "exports" / "reel_01.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"mp4")

    monkeypatch.setattr(
        "video_mix.quality.foundation._ffprobe_payload",
        lambda _path, _ffprobe_path: {
            "format": {"duration": "5.0"},
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920},
                {"codec_type": "audio"},
            ],
        },
    )
    monkeypatch.setattr("video_mix.quality.foundation._sha256_file", lambda _path: "sha256-demo")
    monkeypatch.setattr("video_mix.quality.foundation._detect_black_segments", lambda _path, _ffmpeg_path: [])
    monkeypatch.setattr("video_mix.quality.foundation._detect_freeze_segments", lambda _path, _ffmpeg_path: [])
    monkeypatch.setattr(
        "video_mix.quality.foundation._detect_similar_segments",
        lambda *_args, **_kwargs: [
            {
                "left_position": 1,
                "right_position": 2,
                "left_keyframe_path": "reports/scene_keyframes/a.jpg",
                "right_keyframe_path": "reports/scene_keyframes/b.jpg",
                "hash_distance": 3,
            }
        ],
    )

    class _StoreStub:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def upsert_quality_report(self, **_kwargs) -> None:
            return None

        def upsert_render_provenance(self, **_kwargs) -> None:
            return None

    monkeypatch.setattr("video_mix.quality.foundation.VideoMixFoundationStore", _StoreStub)

    report = build_quality_report(
        work_dir=work_dir,
        project_id="project_1",
        plan={
            "plan_id": "plan_1",
            "requested_duration_ms": 5000,
            "items": [
                {"asset_id": "asset_1", "timeline_start_ms": 0, "timeline_end_ms": 1000, "metadata_json": {"keyframe_path": "reports/scene_keyframes/a.jpg"}, "source_start_ms": 0, "source_end_ms": 1000},
                {"asset_id": "asset_2", "timeline_start_ms": 1000, "timeline_end_ms": 2000, "metadata_json": {"keyframe_path": "reports/scene_keyframes/b.jpg"}, "source_start_ms": 0, "source_end_ms": 1000},
            ],
        },
        output_path=output_path,
    )

    assert report["status"] == "qc_failed"
    assert report["findings"]["similar_segment_count"] == 1


def test_hard_cut_segmenter_detects_real_boundaries(monkeypatch, tmp_path: Path) -> None:
    asset_path = tmp_path / "clip.mp4"
    asset_path.write_bytes(b"video")
    asset = Asset(
        asset_id="asset_1",
        project_id="project_1",
        path=asset_path,
        media_type=MediaType.VIDEO,
        duration_ms=5000,
        width=1080,
        height=1920,
        fps=30.0,
        orientation=Orientation.VERTICAL,
        has_audio=True,
        probe_status="ok",
    )

    monkeypatch.setattr(PySceneDetectSegmenter, "is_available", lambda self: True)

    class _Completed:
        returncode = 0
        stdout = "frame:1 pts_time:1.200\nframe:2 pts_time:3.400\n"
        stderr = ""

    monkeypatch.setattr("video_mix.core.segmenters.subprocess.run", lambda *args, **kwargs: _Completed())

    clips = PySceneDetectSegmenter(ffmpeg_path="ffmpeg", min_scene_ms=1000).plan(asset, tmp_path / "out")

    assert [(clip.source_start_ms, clip.source_end_ms) for clip in clips] == [(0, 1200), (1200, 3400), (3400, 5000)]
    assert all(clip.metadata["scene_detected"] is True for clip in clips)


def test_hard_cut_segmenter_falls_back_to_fixed_interval(monkeypatch, tmp_path: Path) -> None:
    asset_path = tmp_path / "clip.mp4"
    asset_path.write_bytes(b"video")
    asset = Asset(
        asset_id="asset_1",
        project_id="project_1",
        path=asset_path,
        media_type=MediaType.VIDEO,
        duration_ms=4200,
        width=1080,
        height=1920,
        fps=30.0,
        orientation=Orientation.VERTICAL,
        has_audio=True,
        probe_status="ok",
    )

    monkeypatch.setattr(PySceneDetectSegmenter, "is_available", lambda self: True)
    monkeypatch.setattr(PySceneDetectSegmenter, "_detect_scene_cut_points_ms", lambda self, _asset: [])

    clips = plan_asset_segments(
        asset,
        tmp_path / "out",
        [PySceneDetectSegmenter(ffmpeg_path="ffmpeg", min_scene_ms=1000), FixedIntervalSegmenter(clip_ms=1500, max_clips_per_asset=12)],
    )

    assert clips
    assert clips[0].segmenter == SegmenterName.FIXED_INTERVAL
    assert clips[0].metadata["segmenter_fallback"] == "fixed_interval"
