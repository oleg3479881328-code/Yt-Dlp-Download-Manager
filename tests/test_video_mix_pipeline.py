import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from video_mix.core.asset_scan import detect_media_type, stable_id
from video_mix.core.media_probe import probe_asset
from video_mix.core.models import Asset, CandidateStatus, Clip, MediaType, Orientation, Project, SegmenterName
from video_mix.core.quick_mix_diversity_models import (
    QUICK_MIX_DIVERSITY_EXHAUSTED,
    DiversityBatch,
    DiversityPlan,
    DiversityReport,
    DiversitySegment,
)
from video_mix.core.review import (
    build_review_html,
    build_thumbnail_command,
    collect_existing_thumbnails,
    write_review_html,
)
from video_mix.core.storage import build_asset, build_candidate, build_clip, read_json, to_jsonable
from video_mix.service import (
    _build_episode_groups,
    _build_quick_mix_variant_signature_from_manifest,
    _build_variant_similarity_rank,
    _build_video_segment_command,
    _choose_take_render_window,
    _mux_quick_mix_audio,
    _resolve_audio_track_duration_ms,
    _resolve_music_paths,
    _take_next_balanced_variant,
    estimate_quick_mix_capacity,
    quick_mix_source_materials,
    resolve_work_dir,
    scan_source_materials,
)


class _DeterministicChoice:
    @staticmethod
    def choice(values):
        return values[0]

    @staticmethod
    def randint(start, end):
        return start


def _fake_diversity_segment(
    asset: Asset,
    *,
    source_id: str,
    folder_id: str,
    duration_ms: int,
    source_start_ms: int = 0,
    source_group: str = "",
    content_identity: str = "",
) -> DiversitySegment:
    return DiversitySegment(
        source_id=source_id,
        base_source_id=asset.asset_id,
        source_group=source_group or folder_id,
        folder_id=folder_id,
        source_path=str(asset.path.resolve()),
        media_type=asset.media_type.value,
        source_start_ms=source_start_ms,
        duration_ms=duration_ms,
        content_identity=content_identity,
    )


def _fake_diversity_batch(
    plans: list[DiversityPlan],
    *,
    requested_output_count: int,
    warnings: tuple[dict, ...] = (),
) -> DiversityBatch:
    achieved_output_count = len(plans)
    report = DiversityReport(
        strategy="test",
        estimated_search_space=len(plans),
        candidate_budget=len(plans),
        candidates_generated=len(plans),
        duplicate_candidates_removed=0,
        requested_output_count=requested_output_count,
        achieved_output_count=achieved_output_count,
        rejected_by_reason={},
        minimum_pairwise_distance=1.0,
        average_pairwise_distance=1.0,
        maximum_pairwise_distance=1.0,
        nearest_neighbour_distance_by_output={index: 1.0 for index in range(1, achieved_output_count + 1)},
        source_usage={},
        asset_usage={},
        folder_usage={},
        folder_position_usage={},
        folder_transition_usage={},
    )
    return DiversityBatch(plans=tuple(plans), warnings=warnings, report=report)


def test_take_next_balanced_variant_prefers_less_used_take() -> None:
    variants = [
        {"take_id": "take_001"},
        {"take_id": "take_002"},
        {"take_id": "take_003"},
    ]

    selected = _take_next_balanced_variant(
        variants,
        [],
        {"take_001": 4, "take_002": 1, "take_003": 0},
    )

    assert selected is not None
    assert selected["take_id"] == "take_003"


def test_take_next_balanced_variant_avoids_recent_take_ids_when_possible() -> None:
    variants = [
        {"take_id": "take_001"},
        {"take_id": "take_002"},
        {"take_id": "take_003"},
    ]

    selected = _take_next_balanced_variant(
        variants,
        [],
        {"take_001": 0, "take_002": 0, "take_003": 0},
        avoid_take_ids={"take_003", "take_002"},
    )

    assert selected is not None
    assert selected["take_id"] == "take_001"


def test_take_next_balanced_variant_avoids_asset_ids_when_possible() -> None:
    variants = [
        {"take_id": "take_001", "asset": Asset(asset_id="asset_1", project_id="p", path=Path("a.mp4"), media_type=MediaType.VIDEO)},
        {"take_id": "take_002", "asset": Asset(asset_id="asset_2", project_id="p", path=Path("b.mp4"), media_type=MediaType.VIDEO)},
        {"take_id": "take_003", "asset": Asset(asset_id="asset_3", project_id="p", path=Path("c.mp4"), media_type=MediaType.VIDEO)},
    ]

    selected = _take_next_balanced_variant(
        variants,
        [],
        {"take_001": 0, "take_002": 0, "take_003": 0},
        avoid_asset_ids={"asset_3", "asset_2"},
    )

    assert selected is not None
    assert selected["take_id"] == "take_001"


def test_take_next_balanced_variant_prunes_stale_pool_entries() -> None:
    variants = [
        {"take_id": "take_001", "asset": Asset(asset_id="asset_1", project_id="p", path=Path("a.mp4"), media_type=MediaType.VIDEO)},
        {"take_id": "take_002", "asset": Asset(asset_id="asset_2", project_id="p", path=Path("b.mp4"), media_type=MediaType.VIDEO)},
    ]
    stale_pool = list(variants)

    selected = _take_next_balanced_variant(
        variants,
        stale_pool,
        {"take_001": 0, "take_002": 0},
        avoid_asset_ids={"asset_2"},
    )

    assert selected is not None
    assert selected["take_id"] == "take_001"


def test_take_next_balanced_variant_returns_none_when_only_repeats_remain() -> None:
    variants = [
        {"take_id": "take_001", "asset": Asset(asset_id="asset_1", project_id="p", path=Path("a.mp4"), media_type=MediaType.VIDEO)},
        {"take_id": "take_002", "asset": Asset(asset_id="asset_2", project_id="p", path=Path("b.mp4"), media_type=MediaType.VIDEO)},
    ]

    selected = _take_next_balanced_variant(
        variants,
        [],
        {"take_001": 0, "take_002": 0},
        avoid_asset_ids={"asset_1", "asset_2"},
    )

    assert selected is None


def test_choose_take_render_window_randomizes_start_inside_take(monkeypatch: pytest.MonkeyPatch) -> None:
    asset = Asset(
        asset_id="asset_1",
        project_id="project_1",
        path=Path("demo.mp4"),
        media_type=MediaType.VIDEO,
        duration_ms=12000,
    )
    selected_take = {
        "start_ms": 3000,
        "end_ms": 9000,
        "max_duration_ms": 6000,
        "take_id": "take_001",
    }

    monkeypatch.setattr("video_mix.service._random_int_inclusive", lambda max_value: max_value)

    start_ms, segment_ms = _choose_take_render_window(selected_take, asset, preferred_ms=2000)

    assert segment_ms == 2000
    assert start_ms == 7000


def test_build_video_segment_command_uses_decode_time_trim_for_precise_cut() -> None:
    asset = Asset(
        asset_id="asset_1",
        project_id="project_1",
        path=Path("demo.mp4"),
        media_type=MediaType.VIDEO,
        duration_ms=8000,
        width=1080,
        height=1920,
        fps=30.0,
        orientation=Orientation.VERTICAL,
        has_audio=False,
        probe_status="ok",
        quality_score=80.0,
        metadata={},
    )

    command = _build_video_segment_command(
        asset,
        Path("out.mp4"),
        start_ms=15420,
        duration_ms=2000,
        ffmpeg_path="ffmpeg",
    )

    assert command[:4] == ["ffmpeg", "-y", "-i", "demo.mp4"]
    assert "-ss" not in command
    vf_index = command.index("-vf")
    assert command[vf_index + 1].startswith("trim=start=15.420:duration=2.000,setpts=PTS-STARTPTS,")


def test_detect_media_type_video() -> None:
    assert detect_media_type(Path("rings_detail.mp4")).value == "video"


def test_stable_id_is_repeatable() -> None:
    assert stable_id("asset", "abc") == stable_id("asset", "abc")


def test_probe_asset_decodes_ffprobe_json_from_bytes_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asset = Asset(
        asset_id="asset_1",
        project_id="project_1",
        path=tmp_path / "clip.mp4",
        media_type=MediaType.VIDEO,
    )

    class _Completed:
        stdout = b'{"streams":[{"codec_type":"video","width":1080,"height":1920,"avg_frame_rate":"30/1"}],"format":{"duration":"12.34"}}'

    monkeypatch.setattr("video_mix.core.media_probe.subprocess.run", lambda *args, **kwargs: _Completed())

    result = probe_asset(asset, ffprobe_path="ffprobe")

    assert result.probe_status == "ok"
    assert result.duration_ms == 12340
    assert result.width == 1080
    assert result.height == 1920
    assert result.fps == 30.0


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


def test_scan_source_materials_supports_zip_input(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip.mp4").write_bytes(b"video")
    (source_dir / "photo.jpg").write_bytes(b"photo")
    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(source_dir / "clip.mp4", "clip.mp4")
        archive.write(source_dir / "photo.jpg", "photo.jpg")

    result = scan_source_materials(str(zip_path))

    assert result["source_dir"] == str(zip_path.resolve())
    assert result["source_kind"] == "zip"
    assert result["supported_media_count"] == 2
    assert result["suggested_work_dir"] == str((tmp_path / "bundle_video_mix_work").resolve())
    assert Path(result["resolved_source_dir"]).exists()


def test_scan_source_materials_allows_imported_media_under_work_dir_root(tmp_path: Path) -> None:
    source_dir = tmp_path / "input" / "_video_mix_work" / "imports" / "bundle"
    folder = source_dir / "01_Невеста"
    folder.mkdir(parents=True)
    (folder / "clip.mp4").write_bytes(b"video")

    result = scan_source_materials(str(source_dir))

    assert result["supported_media_count"] == 1
    assert result["preview_files"] == ["01_Невеста/clip.mp4"]


def test_scan_source_materials_still_skips_nested_internal_work_dirs(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip.mp4").write_bytes(b"video")
    nested_internal = source_dir / "_video_mix_work"
    nested_internal.mkdir()
    (nested_internal / "ignored.mp4").write_bytes(b"video")

    result = scan_source_materials(str(source_dir))

    assert result["supported_media_count"] == 1
    assert result["preview_files"] == ["clip.mp4"]


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

    def fake_render_segment(asset: Asset, output_path: Path, *, start_ms: int, duration_ms: int, ffmpeg_path: str) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(f"{asset.media_type}:{start_ms}:{duration_ms}".encode())
        rendered_segments.append(output_path)

    def fake_render_output(
        segment_paths: list[Path],
        output_path: Path,
        ffmpeg_path: str,
        *,
        music_path: Path | None = None,
        music_start_ms: int = 0,
    ) -> None:
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
    )

    assert result["generated_count"] == 2
    assert result["video_count"] == 1
    assert result["image_count"] == 1
    assert result["photo_support"] is True
    assert result["duration_source"] == "manual"
    assert result["generation_elapsed_ms"] >= 0
    assert result["quick_mix_plan_path"] == "reports/quick_mix_plan.json"
    assert result["quick_mix_warning_count"] >= 0
    assert all(path.endswith(".mp4") for path in result["output_paths"])
    assert all(path.startswith("quick_mix_generations/") for path in result["output_paths"])
    assert len(rendered_segments) >= 2
    assert len(rendered_outputs) == 2
    quick_mix_json = read_json(tmp_path / "work" / "reports" / "quick_mix.json")
    quick_mix_plan = read_json(tmp_path / "work" / "reports" / "quick_mix_plan.json")
    assert quick_mix_json["quick_mix_plan_path"] == "reports/quick_mix_plan.json"
    assert quick_mix_json["quick_mix_generation_index_path"] == "reports/quick_mix_generations.json"
    assert quick_mix_plan["generation_id"] == result["quick_mix_generation_id"]
    assert len(quick_mix_plan["outputs"]) == 2


def test_quick_mix_source_materials_avoids_duplicate_whatsapp_groups_per_output(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for path in (
        source_dir / "WhatsApp Video 2026-07-03 at 10.21.53 PM.jpg",
        source_dir / "WhatsApp Video 2026-07-03 at 10.21.53 PM (1).jpg",
        source_dir / "cake_detail.jpg",
    ):
        path.write_bytes(b"photo")

    rendered_asset_names: list[str] = []

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.probe_status = "skipped_photo"
        return assets

    def fake_render_segment(asset: Asset, output_path: Path, *, start_ms: int, duration_ms: int, ffmpeg_path: str) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(asset.path.name.encode("utf-8"))
        rendered_asset_names.append(asset.path.name)

    def fake_render_output(
        segment_paths: list[Path],
        output_path: Path,
        ffmpeg_path: str,
        *,
        music_path: Path | None = None,
        music_start_ms: int = 0,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"ok")

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", fake_render_segment)
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", fake_render_output)
    monkeypatch.setattr("video_mix.service._shuffle_in_place", lambda items: None)
    monkeypatch.setattr("video_mix.service._SYSTEM_RANDOM", _DeterministicChoice())

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=3,
        output_count=1,
        project_name="Planner Validation",
        work_dir=str(tmp_path / "work"),
    )

    assert result["quick_mix_warning_count"] == 0
    assert result["quick_mix_warnings"] == []
    assert len(rendered_asset_names) == 2
    whatsapp_hits = [name for name in rendered_asset_names if "WhatsApp Video 2026-07-03 at 10.21.53 PM" in name]
    assert len(whatsapp_hits) == 1
    quick_mix_plan = read_json(tmp_path / "work" / "reports" / "quick_mix_plan.json")
    groups = [segment["source_group"] for segment in quick_mix_plan["outputs"][0]["segments"]]
    assert len(groups) == len(set(groups))
    assert quick_mix_plan["warning_count"] == 0


def test_quick_mix_source_materials_backfills_short_clip_to_requested_duration(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for name in ("a.mp4", "b.mp4", "c.mp4"):
        (source_dir / name).write_bytes(b"video")

    durations_by_name = {"a.mp4": 2000, "b.mp4": 2000, "c.mp4": 700}
    rendered_calls: list[tuple[str, int]] = []

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = durations_by_name[asset.path.name]
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    def fake_render_segment(asset: Asset, output_path: Path, *, start_ms: int, duration_ms: int, ffmpeg_path: str) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(f"{asset.path.name}:{duration_ms}".encode())
        rendered_calls.append((asset.path.name, duration_ms))

    def fake_render_output(
        segment_paths: list[Path],
        output_path: Path,
        ffmpeg_path: str,
        *,
        music_path: Path | None = None,
        music_start_ms: int = 0,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"ok")

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", fake_render_segment)
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", fake_render_output)
    monkeypatch.setattr("video_mix.service._shuffle_in_place", lambda items: None)
    monkeypatch.setattr("video_mix.service._SYSTEM_RANDOM", _DeterministicChoice())

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=4.7,
        output_count=1,
        project_name="Backfill Validation",
        work_dir=str(tmp_path / "work"),
    )

    assert result["generated_count"] == 1
    assert sum(duration_ms for _, duration_ms in rendered_calls) == 4700
    quick_mix_plan = read_json(tmp_path / "work" / "reports" / "quick_mix_plan.json")
    assert quick_mix_plan["outputs"][0]["planned_duration_ms"] == 4700
    assert sum(segment["duration_ms"] for segment in quick_mix_plan["outputs"][0]["segments"]) == 4700
    segment_durations = [segment["duration_ms"] for segment in quick_mix_plan["outputs"][0]["segments"]]
    assert all(duration > 0 for duration in segment_durations)
    assert any(duration < 2000 for duration in segment_durations)


def test_quick_mix_source_materials_supports_music_and_pinned_media(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip.mp4").write_bytes(b"video")
    (source_dir / "photo.jpg").write_bytes(b"photo")
    music_path = tmp_path / "music.mp3"
    opening_path = tmp_path / "opening.jpg"
    closing_path = tmp_path / "closing.mp4"
    music_path.write_bytes(b"audio")
    opening_path.write_bytes(b"opening")
    closing_path.write_bytes(b"closing")

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

    rendered_segments: list[tuple[str, int, int]] = []
    rendered_outputs: list[tuple[Path, Path | None]] = []

    def fake_render_segment(asset: Asset, output_path: Path, *, start_ms: int, duration_ms: int, ffmpeg_path: str) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(f"{asset.path.name}:{start_ms}:{duration_ms}".encode())
        rendered_segments.append((asset.path.name, start_ms, duration_ms))

    def fake_render_output(
        segment_paths: list[Path],
        output_path: Path,
        ffmpeg_path: str,
        *,
        music_path: Path | None = None,
        music_start_ms: int = 0,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes("\n".join(path.name for path in segment_paths).encode("utf-8"))
        rendered_outputs.append((output_path, music_path))

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", fake_render_segment)
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", fake_render_output)
    monkeypatch.setattr("video_mix.service._resolve_audio_track_duration_ms", lambda *_args, **_kwargs: 9000)

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=6,
        output_count=1,
        project_name="Quick Mix Validation",
        work_dir=str(tmp_path / "work"),
        music_path=str(music_path),
        use_music_duration=True,
        opening_media_path=str(opening_path),
        closing_media_path=str(closing_path),
    )

    assert result["duration_seconds"] == 9
    assert result["duration_source"] == "music"
    assert result["music_path"] == str(music_path.resolve())
    assert result["opening_media_path"] == str(opening_path.resolve())
    assert result["closing_media_path"] == str(closing_path.resolve())
    assert len(rendered_outputs) == 1
    assert rendered_outputs[0][0].as_posix().endswith("/exports/quick_mix_001.mp4")
    assert rendered_outputs[0][1] == music_path.resolve()
    assert rendered_segments[0][0] == "opening.jpg"
    assert rendered_segments[-1][0] == "closing.mp4"
    assert rendered_segments[-1][1] > 0


def test_quick_mix_source_materials_randomizes_music_offset_when_not_using_full_track(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip.mp4").write_bytes(b"video")
    music_path = tmp_path / "music.mp3"
    music_path.write_bytes(b"audio")
    captured_music_start_ms: list[int] = []

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 4000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    def fake_render_output(
        segment_paths: list[Path],
        output_path: Path,
        ffmpeg_path: str,
        *,
        music_path: Path | None = None,
        music_start_ms: int = 0,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"out")
        captured_music_start_ms.append(music_start_ms)

    class _OffsetRandom:
        @staticmethod
        def shuffle(items):
            return None

        @staticmethod
        def randint(start, end):
            return min(end, 1500)

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", fake_render_output)
    monkeypatch.setattr("video_mix.service._resolve_audio_track_duration_ms", lambda *_args, **_kwargs: 9000)
    monkeypatch.setattr("video_mix.service._SYSTEM_RANDOM", _OffsetRandom())

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=4,
        output_count=1,
        work_dir=str(tmp_path / "work"),
        music_path=str(music_path),
        use_music_duration=False,
    )

    assert captured_music_start_ms == [1500]
    assert result["variants"][0]["music_start_ms"] == 1500


def test_quick_mix_source_materials_can_keep_manual_duration_with_music(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip.mp4").write_bytes(b"video")
    music_path = tmp_path / "music.mp3"
    music_path.write_bytes(b"audio")

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 4000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))
    monkeypatch.setattr("video_mix.service._resolve_audio_track_duration_ms", lambda *_args, **_kwargs: 9000)

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=6,
        output_count=1,
        work_dir=str(tmp_path / "work"),
        music_path=str(music_path),
        use_music_duration=False,
    )

    assert result["duration_seconds"] == 6
    assert result["duration_source"] == "manual"


def test_resolve_music_paths_accepts_video_file_as_music_source(tmp_path: Path) -> None:
    music_video_path = tmp_path / "music_source.mp4"
    music_video_path.write_bytes(b"video-with-audio")

    resolved = _resolve_music_paths(str(music_video_path), None)

    assert resolved == [music_video_path.resolve()]


def test_resolve_audio_track_duration_requires_audio_stream(tmp_path: Path, monkeypatch) -> None:
    silent_video_path = tmp_path / "silent.mp4"
    silent_video_path.write_bytes(b"video")

    class _FakeCompleted:
        stdout = '{"streams":[{"codec_type":"video","duration":"5.0"}],"format":{"duration":"5.0"}}'

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: _FakeCompleted())

    with pytest.raises(ValueError, match="Could not read music track duration"):
        _resolve_audio_track_duration_ms(silent_video_path, "ffprobe")


def test_mux_quick_mix_audio_maps_audio_stream_from_video_music_source(tmp_path: Path, monkeypatch) -> None:
    captured: list[list[str]] = []
    video_path = tmp_path / "visual.mp4"
    music_video_path = tmp_path / "music_source.mp4"
    output_path = tmp_path / "out.mp4"

    video_path.write_bytes(b"video")
    music_video_path.write_bytes(b"music-video")

    monkeypatch.setattr("subprocess.run", lambda command, check=True: captured.append(command))

    _mux_quick_mix_audio(video_path, output_path, music_video_path, "ffmpeg")

    assert captured
    command = captured[0]
    assert "-map" in command
    assert "0:v:0" in command
    assert "1:a:0" in command


def test_mux_quick_mix_audio_can_start_from_random_offset(tmp_path: Path, monkeypatch) -> None:
    captured: list[list[str]] = []
    video_path = tmp_path / "visual.mp4"
    music_path = tmp_path / "music.mp3"
    output_path = tmp_path / "out.mp4"

    video_path.write_bytes(b"video")
    music_path.write_bytes(b"music")

    monkeypatch.setattr("subprocess.run", lambda command, check=True: captured.append(command))

    _mux_quick_mix_audio(video_path, output_path, music_path, "ffmpeg", music_start_ms=4250)

    command = captured[0]
    assert "-ss" in command
    assert "4.250" in command


def test_quick_mix_source_materials_supports_zip_source(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip.mp4").write_bytes(b"video")
    (source_dir / "photo.jpg").write_bytes(b"photo")
    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(source_dir / "clip.mp4", "clip.mp4")
        archive.write(source_dir / "photo.jpg", "photo.jpg")

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

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    result = quick_mix_source_materials(
        str(zip_path),
        duration_seconds=6,
        output_count=1,
        work_dir=str(tmp_path / "work"),
    )

    assert result["source_dir"] == str(zip_path.resolve())
    assert result["source_kind"] == "zip"
    assert result["generated_count"] == 1
    assert Path(result["resolved_source_dir"]).exists()


def test_quick_mix_source_materials_uses_unique_video_windows_before_reuse(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    clip_a = source_dir / "clip_a.mp4"
    clip_b = source_dir / "clip_b.mp4"
    clip_a.write_bytes(b"video-a")
    clip_b.write_bytes(b"video-b")

    planner_calls: list[dict[str, object]] = []

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 4000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    asset_a = Asset(stable_id("asset", str(clip_a.resolve())), "project", clip_a.resolve(), MediaType.VIDEO, duration_ms=4000)
    asset_b = Asset(stable_id("asset", str(clip_b.resolve())), "project", clip_b.resolve(), MediaType.VIDEO, duration_ms=4000)

    def fake_build_episode_group_diversity_plan(
        episode_groups,
        *,
        target_duration_ms,
        output_count,
        prior_plans=(),
        reserved_asset_ids=None,
        reserved_source_groups=None,
        **_kwargs,
    ):
        planner_calls.append(
            {
                "episode_group_count": len(episode_groups),
                "target_duration_ms": target_duration_ms,
                "output_count": output_count,
                "prior_plan_count": len(prior_plans),
                "reserved_asset_ids": set(reserved_asset_ids or ()),
                "reserved_source_groups": set(reserved_source_groups or ()),
            }
        )
        plan = DiversityPlan(
            output_index=1,
            target_duration_ms=target_duration_ms,
            segments=(
                _fake_diversity_segment(asset_a, source_id="take_a", folder_id="episode_a", duration_ms=2000),
                _fake_diversity_segment(asset_b, source_id="take_b", folder_id="episode_b", duration_ms=2000),
            ),
        )
        return SimpleNamespace(batch=_fake_diversity_batch([plan], requested_output_count=output_count))

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service.build_episode_group_diversity_plan", fake_build_episode_group_diversity_plan)
    monkeypatch.setattr(
        "video_mix.service.render_segments_for_plan",
        lambda plan, _adapter_result: [
            {
                "asset": asset_a,
                "start_ms": 0,
                "duration_ms": int(plan.segments[0].duration_ms),
                "step_index": 0,
                "segment_kind": "body",
                "source_id": "take_a",
                "folder_id": "episode_a",
            },
            {
                "asset": asset_b,
                "start_ms": 0,
                "duration_ms": int(plan.segments[1].duration_ms),
                "step_index": 1,
                "segment_kind": "body",
                "source_id": "take_b",
                "folder_id": "episode_b",
            },
        ],
    )
    monkeypatch.setattr(
        "video_mix.service.selected_take_manifest_for_plan",
        lambda plan, _adapter_result: [
            {
                "episode_id": "episode_a",
                "episode_label": "Episode A",
                "take_id": "take_a",
                "take_index": 1,
                "marker_split": False,
                "asset_id": asset_a.asset_id,
                "media_type": "video",
                "normalized_source_group": "episode_a",
                "source_path": str(asset_a.path),
                "source_start_ms": 0,
                "source_end_ms": 2000,
                "render_start_ms": 0,
                "render_end_ms": 2000,
            },
            {
                "episode_id": "episode_b",
                "episode_label": "Episode B",
                "take_id": "take_b",
                "take_index": 1,
                "marker_split": False,
                "asset_id": asset_b.asset_id,
                "media_type": "video",
                "normalized_source_group": "episode_b",
                "source_path": str(asset_b.path),
                "source_start_ms": 0,
                "source_end_ms": 2000,
                "render_start_ms": 0,
                "render_end_ms": 2000,
            },
        ],
    )
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=4,
        output_count=1,
        work_dir=str(tmp_path / "work"),
    )

    assert result["generated_count"] == 1
    assert planner_calls == [
        {
            "episode_group_count": 2,
            "target_duration_ms": 4000,
            "output_count": 1,
            "prior_plan_count": 0,
            "reserved_asset_ids": set(),
            "reserved_source_groups": set(),
        }
    ]


def test_quick_mix_source_materials_refills_episode_queue_until_target_duration(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    clip_a = source_dir / "clip_a.mp4"
    clip_b = source_dir / "clip_b.mp4"
    clip_a.write_bytes(b"video-a")
    clip_b.write_bytes(b"video-b")

    planner_prior_counts: list[int] = []

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 4000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    asset_a = Asset(stable_id("asset", str(clip_a.resolve())), "project", clip_a.resolve(), MediaType.VIDEO, duration_ms=4000)
    asset_b = Asset(stable_id("asset", str(clip_b.resolve())), "project", clip_b.resolve(), MediaType.VIDEO, duration_ms=4000)

    def fake_build_episode_group_diversity_plan(
        _episode_groups,
        *,
        target_duration_ms,
        output_count,
        prior_plans=(),
        **_kwargs,
    ):
        planner_prior_counts.append(len(prior_plans))
        plan = DiversityPlan(
            output_index=1,
            target_duration_ms=target_duration_ms,
            segments=(
                _fake_diversity_segment(asset_a, source_id="take_a", folder_id="episode_a", duration_ms=2000),
                _fake_diversity_segment(asset_b, source_id="take_b", folder_id="episode_b", duration_ms=2000),
            ),
        )
        return SimpleNamespace(batch=_fake_diversity_batch([plan], requested_output_count=output_count))

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service.build_episode_group_diversity_plan", fake_build_episode_group_diversity_plan)
    monkeypatch.setattr(
        "video_mix.service.render_segments_for_plan",
        lambda plan, _adapter_result: [
            {
                "asset": asset_a,
                "start_ms": 0,
                "duration_ms": int(plan.segments[0].duration_ms),
                "step_index": 0,
                "segment_kind": "body",
                "source_id": "take_a",
                "folder_id": "episode_a",
            },
            {
                "asset": asset_b,
                "start_ms": 0,
                "duration_ms": int(plan.segments[1].duration_ms),
                "step_index": 1,
                "segment_kind": "body",
                "source_id": "take_b",
                "folder_id": "episode_b",
            },
        ],
    )
    monkeypatch.setattr(
        "video_mix.service.selected_take_manifest_for_plan",
        lambda *_args, **_kwargs: [
            {
                "episode_id": "episode_a",
                "episode_label": "Episode A",
                "take_id": "take_a",
                "take_index": 1,
                "marker_split": False,
                "asset_id": asset_a.asset_id,
                "media_type": "video",
                "normalized_source_group": "episode_a",
                "source_path": str(asset_a.path),
                "source_start_ms": 0,
                "source_end_ms": 2000,
                "render_start_ms": 0,
                "render_end_ms": 2000,
            },
            {
                "episode_id": "episode_b",
                "episode_label": "Episode B",
                "take_id": "take_b",
                "take_index": 1,
                "marker_split": False,
                "asset_id": asset_b.asset_id,
                "media_type": "video",
                "normalized_source_group": "episode_b",
                "source_path": str(asset_b.path),
                "source_start_ms": 0,
                "source_end_ms": 2000,
                "render_start_ms": 0,
                "render_end_ms": 2000,
            },
        ],
    )
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    work_dir = tmp_path / "work"
    quick_mix_source_materials(
        str(source_dir),
        duration_seconds=4,
        output_count=1,
        work_dir=str(work_dir),
    )
    quick_mix_source_materials(
        str(source_dir),
        duration_seconds=4,
        output_count=1,
        work_dir=str(work_dir),
    )

    assert planner_prior_counts == [0, 1]


def test_quick_mix_source_materials_does_not_reuse_opening_asset_in_body(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    clip_a = source_dir / "clip_a.mp4"
    clip_b = source_dir / "clip_b.mp4"
    clip_c = source_dir / "clip_c.mp4"
    clip_a.write_bytes(b"video-a")
    clip_b.write_bytes(b"video-b")
    clip_c.write_bytes(b"video-c")

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 4000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    captured_reserved_asset_ids: list[set[str]] = []
    captured_reserved_source_groups: list[set[str]] = []
    asset_b = Asset(stable_id("asset", str(clip_b.resolve())), "project", clip_b.resolve(), MediaType.VIDEO, duration_ms=4000)
    asset_c = Asset(stable_id("asset", str(clip_c.resolve())), "project", clip_c.resolve(), MediaType.VIDEO, duration_ms=4000)

    def fake_build_episode_group_diversity_plan(
        _episode_groups,
        *,
        target_duration_ms,
        output_count,
        reserved_asset_ids=None,
        reserved_source_groups=None,
        **_kwargs,
    ):
        captured_reserved_asset_ids.append(set(reserved_asset_ids or ()))
        captured_reserved_source_groups.append(set(reserved_source_groups or ()))
        plan = DiversityPlan(
            output_index=1,
            target_duration_ms=target_duration_ms,
            segments=(
                _fake_diversity_segment(asset_b, source_id="take_b", folder_id="episode_b", duration_ms=2000),
                _fake_diversity_segment(asset_c, source_id="take_c", folder_id="episode_c", duration_ms=2000),
            ),
        )
        return SimpleNamespace(batch=_fake_diversity_batch([plan], requested_output_count=output_count))

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service.build_episode_group_diversity_plan", fake_build_episode_group_diversity_plan)
    monkeypatch.setattr(
        "video_mix.service.render_segments_for_plan",
        lambda *_args, **_kwargs: [
            {
                "asset": asset_b,
                "start_ms": 0,
                "duration_ms": 2000,
                "step_index": 0,
                "segment_kind": "body",
                "source_id": "take_b",
                "folder_id": "episode_b",
            },
            {
                "asset": asset_c,
                "start_ms": 0,
                "duration_ms": 2000,
                "step_index": 1,
                "segment_kind": "body",
                "source_id": "take_c",
                "folder_id": "episode_c",
            },
        ],
    )
    monkeypatch.setattr("video_mix.service.selected_take_manifest_for_plan", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    quick_mix_source_materials(
        str(source_dir),
        duration_seconds=6,
        output_count=1,
        work_dir=str(tmp_path / "work"),
        opening_media_path=str(clip_a),
    )

    assert captured_reserved_asset_ids == [{stable_id("asset", str(clip_a.resolve()))}]
    assert captured_reserved_source_groups == [{"clip_a.mp4"}]


def test_quick_mix_source_materials_excludes_all_marker_variants_from_body(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    clip_a = source_dir / "clip_a.mp4"
    clip_b = source_dir / "clip_b.mp4"
    clip_c = source_dir / "clip_c.mp4"
    clip_d = source_dir / "clip_d.mp4"
    for clip_path, payload in (
        (clip_a, b"video-a"),
        (clip_b, b"video-b"),
        (clip_c, b"video-c"),
        (clip_d, b"video-d"),
    ):
        clip_path.write_bytes(payload)

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 4000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    captured_reserved_asset_ids: list[set[str]] = []
    captured_reserved_source_groups: list[set[str]] = []
    asset_c = Asset(stable_id("asset", str(clip_c.resolve())), "project", clip_c.resolve(), MediaType.VIDEO, duration_ms=4000)

    def fake_build_episode_group_diversity_plan(
        _episode_groups,
        *,
        target_duration_ms,
        output_count,
        reserved_asset_ids=None,
        reserved_source_groups=None,
        **_kwargs,
    ):
        captured_reserved_asset_ids.append(set(reserved_asset_ids or ()))
        captured_reserved_source_groups.append(set(reserved_source_groups or ()))
        plan = DiversityPlan(
            output_index=1,
            target_duration_ms=target_duration_ms,
            segments=(
                _fake_diversity_segment(asset_c, source_id="take_c", folder_id="episode_c", duration_ms=4000),
            ),
        )
        return SimpleNamespace(batch=_fake_diversity_batch([plan], requested_output_count=output_count))

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service.build_episode_group_diversity_plan", fake_build_episode_group_diversity_plan)
    monkeypatch.setattr(
        "video_mix.service.render_segments_for_plan",
        lambda *_args, **_kwargs: [
            {
                "asset": asset_c,
                "start_ms": 0,
                "duration_ms": 4000,
                "step_index": 0,
                "segment_kind": "body",
                "source_id": "take_c",
                "folder_id": "episode_c",
            }
        ],
    )
    monkeypatch.setattr("video_mix.service.selected_take_manifest_for_plan", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    quick_mix_source_materials(
        str(source_dir),
        duration_seconds=6,
        output_count=1,
        work_dir=str(tmp_path / "work"),
        opening_media_paths=[str(clip_a), str(clip_b)],
    )

    assert len(captured_reserved_asset_ids) == 1
    assert captured_reserved_asset_ids[0] <= {
        stable_id("asset", str(clip_a.resolve())),
        stable_id("asset", str(clip_b.resolve())),
    }
    assert len(captured_reserved_source_groups) == 1
    assert captured_reserved_source_groups[0] <= {"clip_a.mp4", "clip_b.mp4"}


def test_quick_mix_source_materials_allows_short_tail_under_body_minimum(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip_a.mp4").write_bytes(b"video-a")
    (source_dir / "clip_b.mp4").write_bytes(b"video-b")

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 5000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    rendered_durations: list[int] = []

    def fake_render_segment(asset: Asset, output_path: Path, *, start_ms: int, duration_ms: int, ffmpeg_path: str) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"seg")
        rendered_durations.append(duration_ms)

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", fake_render_segment)
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))
    monkeypatch.setattr("video_mix.service._shuffle_in_place", lambda items: None)
    monkeypatch.setattr("video_mix.service._SYSTEM_RANDOM", _DeterministicChoice())

    quick_mix_source_materials(
        str(source_dir),
        duration_seconds=3.2,
        output_count=1,
        work_dir=str(tmp_path / "work"),
    )

    assert sum(rendered_durations) == 3200
    assert any(duration < 1500 for duration in rendered_durations)


def test_quick_mix_variant_signature_distinguishes_composite_photo_order() -> None:
    variant_a = {
        "requested_duration_ms": 6000,
        "selected_takes": [
            {
                "episode_id": "episode_001",
                "composite_signature": "video:asset_1|photos:photo_a,photo_b|photo_ms:1200|motion:static",
            }
        ],
        "selected_music_path": "C:/music_a.mp3",
        "selected_opening_path": "C:/opening_a.jpg",
        "selected_closing_path": "C:/closing_a.mp4",
    }
    variant_b = {
        **variant_a,
        "selected_takes": [
            {
                "episode_id": "episode_001",
                "composite_signature": "video:asset_1|photos:photo_b,photo_a|photo_ms:1200|motion:static",
            }
        ],
    }

    assert _build_quick_mix_variant_signature_from_manifest(variant_a) != _build_quick_mix_variant_signature_from_manifest(variant_b)


def test_quick_mix_variant_signature_ignores_music_and_markers_for_composite_body() -> None:
    base_variant = {
        "requested_duration_ms": 6000,
        "selected_takes": [
            {
                "episode_id": "episode_001",
                "composite_signature": "video:asset_1|photos:photo_a,photo_b|photo_ms:1200|motion:ken_burns",
            }
        ],
        "selected_music_path": "C:/music_a.mp3",
        "selected_opening_path": "C:/opening_a.jpg",
        "selected_closing_path": "C:/closing_a.mp4",
    }
    changed_variant = {
        **base_variant,
        "selected_music_path": "C:/music_b.mp3",
        "selected_opening_path": "C:/opening_b.jpg",
        "selected_closing_path": "C:/closing_b.mp4",
    }

    assert _build_quick_mix_variant_signature_from_manifest(base_variant) == _build_quick_mix_variant_signature_from_manifest(changed_variant)


def test_quick_mix_source_materials_preserves_composite_atomic_duration_and_content_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    clip_path = source_dir / "clip.mp4"
    clip_path.write_bytes(b"video")
    work_dir = tmp_path / "work"
    content_identity = "composite:atomic-demo"

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            if asset.media_type == MediaType.VIDEO:
                asset.duration_ms = 3000
                asset.width = 1080
                asset.height = 1920
                asset.fps = 30.0
                asset.orientation = Orientation.VERTICAL
                asset.probe_status = "ok"
            else:
                asset.probe_status = "skipped_photo"
        return assets

    video_asset = Asset(stable_id("asset", str(clip_path.resolve())), "project", clip_path.resolve(), MediaType.VIDEO, duration_ms=3000)
    photo_a = Asset("photo_a", "project", tmp_path / "photo_a.jpg", MediaType.PHOTO)
    photo_b = Asset("photo_b", "project", tmp_path / "photo_b.jpg", MediaType.PHOTO)
    photo_a.path.write_bytes(b"a")
    photo_b.path.write_bytes(b"b")
    rendered_segment_durations: list[int] = []

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr(
        "video_mix.service.build_episode_group_diversity_plan",
        lambda *_args, target_duration_ms, output_count, **_kwargs: SimpleNamespace(
            batch=_fake_diversity_batch(
                [
                    DiversityPlan(
                        output_index=1,
                        target_duration_ms=target_duration_ms,
                        segments=(
                            _fake_diversity_segment(
                                video_asset,
                                source_id="composite_take_001",
                                folder_id="episode_001",
                                duration_ms=5400,
                                content_identity=content_identity,
                            ),
                        ),
                    )
                ],
                requested_output_count=output_count,
            )
        ),
    )
    monkeypatch.setattr(
        "video_mix.service.render_segments_for_plan",
        lambda *_args, **_kwargs: [
            {
                "asset": video_asset,
                "start_ms": 0,
                "duration_ms": 5400,
                "step_index": 0,
                "segment_kind": "body",
                "source_id": "composite_take_001",
                "folder_id": "episode_001",
                "take_type": "video_photo_composite",
                "content_identity": content_identity,
                "raw_take": {
                    "video_asset": video_asset,
                    "photo_assets": [photo_a, photo_b],
                    "photo_duration_ms": 1200,
                    "photo_motion_mode": "static",
                },
            }
        ],
    )
    monkeypatch.setattr(
        "video_mix.service.selected_take_manifest_for_plan",
        lambda *_args, **_kwargs: [
            {
                "episode_id": "episode_001",
                "episode_label": "episode_001",
                "take_id": "composite_take_001",
                "take_index": 1,
                "marker_split": False,
                "take_type": "video_photo_composite",
                "asset_id": video_asset.asset_id,
                "media_type": "video",
                "normalized_source_group": "clip.mp4",
                "source_path": str(video_asset.path),
                "source_start_ms": 0,
                "source_end_ms": 3000,
                "render_start_ms": 0,
                "render_end_ms": 5400,
                "composite_signature": content_identity,
                "content_identity": content_identity,
            }
        ],
    )

    def fake_render_segment(_asset: Asset, output_path: Path, *, start_ms: int, duration_ms: int, ffmpeg_path: str, **_kwargs) -> None:
        rendered_segment_durations.append(duration_ms)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(f"{start_ms}:{duration_ms}".encode())

    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", fake_render_segment)
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=5.4,
        output_count=1,
        work_dir=str(work_dir),
    )

    generation_plan = read_json(work_dir / result["quick_mix_generation_plan_path"])
    output = generation_plan["outputs"][0]
    body_segments = [segment for segment in output["segments"] if segment["segment_kind"] == "body"]

    assert rendered_segment_durations == [5400]
    assert output["planned_duration_ms"] == 5400
    assert output["generated_duration_ms"] == 5400
    assert output["body_visual_signature"] == [content_identity]
    assert body_segments[0]["content_identity"] == content_identity
    assert body_segments[0]["base_source_id"] == content_identity


def test_quick_mix_source_materials_restores_prior_composite_identity_between_generations(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    clip_path = source_dir / "clip.mp4"
    clip_path.write_bytes(b"video")
    work_dir = tmp_path / "work"
    content_identity = "composite:history-demo"
    planner_prior_signatures: list[list[tuple[str, ...]]] = []

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 3000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    video_asset = Asset(stable_id("asset", str(clip_path.resolve())), "project", clip_path.resolve(), MediaType.VIDEO, duration_ms=3000)

    def fake_build_episode_group_diversity_plan(
        _episode_groups,
        *,
        target_duration_ms,
        output_count,
        prior_plans=(),
        **_kwargs,
    ):
        planner_prior_signatures.append([plan.asset_signature for plan in prior_plans])
        return SimpleNamespace(
            batch=_fake_diversity_batch(
                [
                    DiversityPlan(
                        output_index=1,
                        target_duration_ms=target_duration_ms,
                        segments=(
                            _fake_diversity_segment(
                                video_asset,
                                source_id="composite_take_001",
                                folder_id="episode_001",
                                duration_ms=5400,
                                content_identity=content_identity,
                            ),
                        ),
                    )
                ],
                requested_output_count=output_count,
            )
        )

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service.build_episode_group_diversity_plan", fake_build_episode_group_diversity_plan)
    monkeypatch.setattr(
        "video_mix.service.render_segments_for_plan",
        lambda *_args, **_kwargs: [
            {
                "asset": video_asset,
                "start_ms": 0,
                "duration_ms": 5400,
                "step_index": 0,
                "segment_kind": "body",
                "source_id": "composite_take_001",
                "folder_id": "episode_001",
                "take_type": "video_photo_composite",
                "content_identity": content_identity,
                "raw_take": {
                    "video_asset": video_asset,
                    "photo_assets": [],
                    "photo_duration_ms": 1200,
                    "photo_motion_mode": "static",
                },
            }
        ],
    )
    monkeypatch.setattr(
        "video_mix.service.selected_take_manifest_for_plan",
        lambda *_args, **_kwargs: [
            {
                "episode_id": "episode_001",
                "episode_label": "episode_001",
                "take_id": "composite_take_001",
                "take_index": 1,
                "marker_split": False,
                "take_type": "video_photo_composite",
                "asset_id": video_asset.asset_id,
                "media_type": "video",
                "normalized_source_group": "clip.mp4",
                "source_path": str(video_asset.path),
                "source_start_ms": 0,
                "source_end_ms": 3000,
                "render_start_ms": 0,
                "render_end_ms": 5400,
                "composite_signature": content_identity,
                "content_identity": content_identity,
            }
        ],
    )
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    quick_mix_source_materials(
        str(source_dir),
        duration_seconds=5.4,
        output_count=1,
        work_dir=str(work_dir),
    )
    quick_mix_source_materials(
        str(source_dir),
        duration_seconds=5.4,
        output_count=1,
        work_dir=str(work_dir),
    )

    assert planner_prior_signatures[0] == []
    assert planner_prior_signatures[1] == [(content_identity,)]


def test_estimate_quick_mix_capacity_returns_unique_output_estimate(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for index in range(4):
        (source_dir / f"clip_{index}.mp4").write_bytes(b"video")

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 4000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)

    result = estimate_quick_mix_capacity(
        str(source_dir),
        duration_seconds=6,
    )

    assert result["duration_source"] == "manual"
    assert result["usable_asset_count"] == 4
    assert result["episode_group_count"] == 4
    assert result["total_segment_candidates"] == 8
    assert result["selected_episode_count"] == 4
    assert result["segments_per_output"] == 4
    assert result["estimated_unique_outputs"] == 384


def test_build_episode_groups_splits_marker_delimited_takes(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "episode.mp4"
    source_path.write_bytes(b"video")
    asset = build_asset(
        {
            "asset_id": "asset_1",
            "project_id": "project_1",
            "path": str(source_path),
            "media_type": MediaType.VIDEO.value,
            "duration_ms": 3500,
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

    monkeypatch.setattr("video_mix.service._detect_magenta_marker_ranges", lambda *_args, **_kwargs: [(1000, 1400), (2200, 2600)])

    groups = _build_episode_groups([asset], "ffmpeg")

    assert len(groups) == 1
    episode = groups[0]
    assert episode["marker_split"] is True
    assert episode["take_count"] == 3
    takes = episode["takes"]
    assert takes[0]["start_ms"] == 0
    assert takes[0]["end_ms"] == 880
    assert takes[1]["start_ms"] == 1520
    assert takes[1]["end_ms"] == 2080
    assert takes[2]["start_ms"] == 2720
    assert takes[2]["end_ms"] == 3500


def test_build_episode_groups_uses_first_level_folders_as_episode_groups(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    bride_dir = source_dir / "01_Невеста"
    guests_dir = source_dir / "02_Гости"
    bride_dir.mkdir(parents=True)
    guests_dir.mkdir(parents=True)
    clip_a = bride_dir / "clip_a.mp4"
    clip_b = bride_dir / "clip_b.mp4"
    clip_c = guests_dir / "clip_c.mp4"
    for clip_path in (clip_a, clip_b, clip_c):
        clip_path.write_bytes(b"video")

    assets = [
        build_asset(
            {
                "asset_id": f"asset_{index}",
                "project_id": "project_1",
                "path": str(path),
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
        for index, path in enumerate((clip_a, clip_b, clip_c), start=1)
    ]

    monkeypatch.setattr("video_mix.service._detect_magenta_marker_ranges", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("video_mix.service._shuffle_in_place", lambda items: None)

    groups = _build_episode_groups(assets, "ffmpeg", source_dir)

    assert [group["episode_label"] for group in groups] == ["Невеста", "Гости"]
    assert groups[0]["take_count"] == 4
    assert groups[0]["group_kind"] == "directory"
    assert groups[0]["source_folder"] == "01_Невеста"
    assert len(groups[0]["assets"]) == 2
    assert [take["asset"].path.name for take in groups[0]["takes"]] == [
        "clip_a.mp4",
        "clip_a.mp4",
        "clip_b.mp4",
        "clip_b.mp4",
    ]


def test_build_episode_groups_preserves_flat_asset_based_behavior_without_folders(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    clip_a = source_dir / "clip_a.mp4"
    clip_b = source_dir / "clip_b.mp4"
    for clip_path in (clip_a, clip_b):
        clip_path.write_bytes(b"video")

    assets = [
        build_asset(
            {
                "asset_id": f"asset_{index}",
                "project_id": "project_1",
                "path": str(path),
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
        for index, path in enumerate((clip_a, clip_b), start=1)
    ]

    monkeypatch.setattr("video_mix.service._detect_magenta_marker_ranges", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("video_mix.service._shuffle_in_place", lambda items: None)

    groups = _build_episode_groups(assets, "ffmpeg", source_dir)

    assert [group["episode_label"] for group in groups] == ["clip_a", "clip_b"]
    assert all(group["group_kind"] == "asset" for group in groups)


def test_quick_mix_source_materials_uses_folder_groups_for_episode_selection(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    bride_dir = source_dir / "01_Невеста"
    guests_dir = source_dir / "02_Гости"
    bride_dir.mkdir(parents=True)
    guests_dir.mkdir(parents=True)
    for clip_path in (
        bride_dir / "bride_a.mp4",
        bride_dir / "bride_b.mp4",
        guests_dir / "guest_a.mp4",
    ):
        clip_path.write_bytes(b"video")

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 4000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._detect_magenta_marker_ranges", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))
    monkeypatch.setattr("video_mix.service._shuffle_in_place", lambda items: None)
    monkeypatch.setattr("video_mix.service._SYSTEM_RANDOM", _DeterministicChoice())

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=4,
        output_count=1,
        work_dir=str(tmp_path / "work"),
    )

    assert [group["episode_label"] for group in result["episode_groups"]] == ["Невеста", "Гости"]
    assert result["episode_groups"][0]["source_folder"] == "01_Невеста"
    assert result["episode_groups"][0]["asset_count"] == 2
    assert result["episode_groups"][1]["asset_count"] == 1
    assert len(result["variants"][0]["episode_order"]) == 2
    assert set(result["variants"][0]["episode_order"]) == {
        result["episode_groups"][0]["episode_id"],
        result["episode_groups"][1]["episode_id"],
    }


def test_quick_mix_source_materials_records_episode_variant_manifest(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    clip_a = source_dir / "clip_a.mp4"
    clip_b = source_dir / "clip_b.mp4"
    clip_a.write_bytes(b"video-a")
    clip_b.write_bytes(b"video-b")

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 3500 if asset.path.name == "clip_a.mp4" else 4000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    def fake_marker_ranges(asset: Asset, ffmpeg_path: str):
        if asset.path.name == "clip_a.mp4":
            return [(1000, 1400)]
        return []

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    asset_a = Asset(stable_id("asset", str(clip_a.resolve())), "project", clip_a.resolve(), MediaType.VIDEO, duration_ms=3500)
    asset_b = Asset(stable_id("asset", str(clip_b.resolve())), "project", clip_b.resolve(), MediaType.VIDEO, duration_ms=4000)

    monkeypatch.setattr("video_mix.service._detect_magenta_marker_ranges", fake_marker_ranges)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr(
        "video_mix.service.build_episode_group_diversity_plan",
        lambda *_args, target_duration_ms, output_count, **_kwargs: SimpleNamespace(
            batch=_fake_diversity_batch(
                [
                    DiversityPlan(
                        output_index=1,
                        target_duration_ms=target_duration_ms,
                        segments=(
                            _fake_diversity_segment(asset_a, source_id="take_a_marker", folder_id="clip_a", duration_ms=1500, source_start_ms=1000),
                            _fake_diversity_segment(asset_b, source_id="take_b", folder_id="clip_b", duration_ms=2500),
                        ),
                    )
                ],
                requested_output_count=output_count,
            )
        ),
    )
    monkeypatch.setattr(
        "video_mix.service.render_segments_for_plan",
        lambda *_args, **_kwargs: [
            {
                "asset": asset_a,
                "start_ms": 1000,
                "duration_ms": 1500,
                "step_index": 0,
                "segment_kind": "body",
                "source_id": "take_a_marker",
                "folder_id": "clip_a",
            },
            {
                "asset": asset_b,
                "start_ms": 0,
                "duration_ms": 2500,
                "step_index": 1,
                "segment_kind": "body",
                "source_id": "take_b",
                "folder_id": "clip_b",
            },
        ],
    )
    monkeypatch.setattr(
        "video_mix.service.selected_take_manifest_for_plan",
        lambda *_args, **_kwargs: [
            {
                "episode_id": "clip_a",
                "episode_label": "clip_a",
                "take_id": "take_a_marker",
                "take_index": 1,
                "marker_split": True,
                "asset_id": asset_a.asset_id,
                "media_type": "video",
                "normalized_source_group": "clip_a",
                "source_path": str(asset_a.path),
                "source_start_ms": 1000,
                "source_end_ms": 3500,
                "render_start_ms": 1000,
                "render_end_ms": 2500,
            },
            {
                "episode_id": "clip_b",
                "episode_label": "clip_b",
                "take_id": "take_b",
                "take_index": 1,
                "marker_split": False,
                "asset_id": asset_b.asset_id,
                "media_type": "video",
                "normalized_source_group": "clip_b",
                "source_path": str(asset_b.path),
                "source_start_ms": 0,
                "source_end_ms": 4000,
                "render_start_ms": 0,
                "render_end_ms": 2500,
            },
        ],
    )
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=4,
        output_count=1,
        work_dir=str(tmp_path / "work"),
    )

    assert len(result["episode_groups"]) == 2
    marker_episode = next(group for group in result["episode_groups"] if group["episode_label"] == "clip_a")
    assert marker_episode["marker_split"] is True
    assert marker_episode["take_count"] == 2
    assert result["variants"][0]["variant_id"] == "quick_mix_001"
    assert len(result["variants"][0]["episode_order"]) == 2
    assert result["variants"][0]["selected_takes"][0]["episode_label"] == "clip_a"
    assert result["variants"][0]["selected_takes"][0]["marker_split"] is True
    assert result["variants"][0]["selected_takes"][0]["source_end_ms"] == 3500


def test_quick_mix_source_materials_spreads_outputs_across_least_used_assets(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for name in ("clip_a.mp4", "clip_b.mp4", "clip_c.mp4", "clip_d.mp4"):
        (source_dir / name).write_bytes(b"video")

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 9000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    asset_paths = [source_dir / name for name in ("clip_a.mp4", "clip_b.mp4", "clip_c.mp4", "clip_d.mp4")]
    assets = [
        Asset(stable_id("asset", str(path.resolve())), "project", path.resolve(), MediaType.VIDEO, duration_ms=9000)
        for path in asset_paths
    ]

    call_index = {"value": 0}

    def fake_build_episode_group_diversity_plan(
        _episode_groups,
        *,
        target_duration_ms,
        output_count,
        **_kwargs,
    ):
        generation = call_index["value"]
        call_index["value"] += 1
        asset = assets[generation % len(assets)]
        plan = DiversityPlan(
            output_index=1,
            target_duration_ms=target_duration_ms,
            segments=(
                _fake_diversity_segment(
                    asset,
                    source_id=f"take_{generation + 1}",
                    folder_id=f"episode_{generation + 1}",
                    duration_ms=target_duration_ms,
                ),
            ),
        )
        return SimpleNamespace(batch=_fake_diversity_batch([plan], requested_output_count=output_count))

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service.build_episode_group_diversity_plan", fake_build_episode_group_diversity_plan)
    monkeypatch.setattr(
        "video_mix.service.render_segments_for_plan",
        lambda plan, _adapter_result: [
            {
                "asset": assets[(call_index["value"] - 1) % len(assets)],
                "start_ms": 0,
                "duration_ms": int(plan.segments[0].duration_ms),
                "step_index": 0,
                "segment_kind": "body",
                "source_id": plan.segments[0].source_id,
                "folder_id": plan.segments[0].folder_id,
            }
        ],
    )
    monkeypatch.setattr("video_mix.service.selected_take_manifest_for_plan", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    work_dir = tmp_path / "work"
    first = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=2,
        output_count=1,
        work_dir=str(work_dir),
    )
    second = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=2,
        output_count=1,
        work_dir=str(work_dir),
    )

    assert first["output_paths"] != second["output_paths"]
    assert (work_dir / first["output_paths"][0]).exists()
    assert (work_dir / second["output_paths"][0]).exists()
    generation_index = read_json(work_dir / "reports" / "quick_mix_generations.json")
    assert len(generation_index["generations"]) == 2


def test_quick_mix_source_materials_randomizes_episode_order_within_output(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for name in ("clip_a.mp4", "clip_b.mp4", "clip_c.mp4", "clip_d.mp4"):
        (source_dir / name).write_bytes(b"video")

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 4000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    asset_paths = [source_dir / name for name in ("clip_a.mp4", "clip_b.mp4", "clip_c.mp4", "clip_d.mp4")]
    assets = [
        Asset(stable_id("asset", str(path.resolve())), "project", path.resolve(), MediaType.VIDEO, duration_ms=4000)
        for path in asset_paths
    ]

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr(
        "video_mix.service.build_episode_group_diversity_plan",
        lambda *_args, target_duration_ms, output_count, **_kwargs: SimpleNamespace(
            batch=_fake_diversity_batch(
                [
                    DiversityPlan(
                        output_index=0,
                        target_duration_ms=target_duration_ms,
                        segments=(
                            _fake_diversity_segment(assets[0], source_id="take_a", folder_id="episode_a", duration_ms=2000),
                            _fake_diversity_segment(assets[1], source_id="take_b", folder_id="episode_b", duration_ms=2000),
                        ),
                    )
                ],
                requested_output_count=output_count,
            )
        ),
    )
    monkeypatch.setattr(
        "video_mix.service.render_segments_for_plan",
        lambda *_args, **_kwargs: [
            {
                "asset": assets[0],
                "start_ms": 0,
                "duration_ms": 2000,
                "step_index": 0,
                "segment_kind": "body",
                "source_id": "take_a",
                "folder_id": "episode_a",
            },
            {
                "asset": assets[1],
                "start_ms": 0,
                "duration_ms": 2000,
                "step_index": 1,
                "segment_kind": "body",
                "source_id": "take_b",
                "folder_id": "episode_b",
            },
        ],
    )
    monkeypatch.setattr("video_mix.service.selected_take_manifest_for_plan", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=4,
        output_count=1,
        work_dir=str(tmp_path / "work"),
    )

    quick_mix_plan = read_json(tmp_path / "work" / "reports" / "quick_mix_plan.json")
    assert result["quick_mix_warning_count"] == 0
    assert [output["output_index"] for output in quick_mix_plan["outputs"]] == [1]


def test_variant_similarity_rank_prefers_fewer_positional_take_matches() -> None:
    seen_variant = {
        "target_duration_ms": 6000,
        "music_path": "",
        "opening_media_path": "",
        "closing_media_path": "",
        "selected_takes": [
            {"episode_id": "ep_1", "take_id": "take_1"},
            {"episode_id": "ep_2", "take_id": "take_2"},
            {"episode_id": "ep_3", "take_id": "take_3"},
        ],
        "episode_order": ["ep_1", "ep_2", "ep_3"],
    }
    more_similar_variant = {
        "target_duration_ms": 6000,
        "music_path": "",
        "opening_media_path": "",
        "closing_media_path": "",
        "selected_takes": [
            {"episode_id": "ep_1", "take_id": "take_1"},
            {"episode_id": "ep_4", "take_id": "take_4"},
            {"episode_id": "ep_3", "take_id": "take_3"},
        ],
        "episode_order": ["ep_1", "ep_4", "ep_3"],
    }
    less_similar_variant = {
        "target_duration_ms": 6000,
        "music_path": "",
        "opening_media_path": "",
        "closing_media_path": "",
        "selected_takes": [
            {"episode_id": "ep_4", "take_id": "take_4"},
            {"episode_id": "ep_5", "take_id": "take_5"},
            {"episode_id": "ep_6", "take_id": "take_6"},
        ],
        "episode_order": ["ep_4", "ep_5", "ep_6"],
    }

    assert _build_variant_similarity_rank(less_similar_variant, [seen_variant]) < _build_variant_similarity_rank(
        more_similar_variant,
        [seen_variant],
    )


def test_variant_similarity_rank_prefers_lower_overlap_across_seen_variants() -> None:
    seen_variants = [
        {
            "target_duration_ms": 6000,
            "music_path": "",
            "opening_media_path": "",
            "closing_media_path": "",
            "selected_takes": [
                {"episode_id": "ep_1", "take_id": "take_1"},
                {"episode_id": "ep_2", "take_id": "take_2"},
                {"episode_id": "ep_3", "take_id": "take_3"},
            ],
            "episode_order": ["ep_1", "ep_2", "ep_3"],
        },
        {
            "target_duration_ms": 6000,
            "music_path": "",
            "opening_media_path": "",
            "closing_media_path": "",
            "selected_takes": [
                {"episode_id": "ep_4", "take_id": "take_4"},
                {"episode_id": "ep_5", "take_id": "take_5"},
                {"episode_id": "ep_6", "take_id": "take_6"},
            ],
            "episode_order": ["ep_4", "ep_5", "ep_6"],
        },
    ]
    more_similar_variant = {
        "target_duration_ms": 6000,
        "music_path": "",
        "opening_media_path": "",
        "closing_media_path": "",
        "selected_takes": [
            {"episode_id": "ep_1", "take_id": "take_1"},
            {"episode_id": "ep_5", "take_id": "take_5"},
            {"episode_id": "ep_7", "take_id": "take_7"},
        ],
        "episode_order": ["ep_1", "ep_5", "ep_7"],
    }
    less_similar_variant = {
        "target_duration_ms": 6000,
        "music_path": "",
        "opening_media_path": "",
        "closing_media_path": "",
        "selected_takes": [
            {"episode_id": "ep_7", "take_id": "take_7"},
            {"episode_id": "ep_8", "take_id": "take_8"},
            {"episode_id": "ep_9", "take_id": "take_9"},
        ],
        "episode_order": ["ep_7", "ep_8", "ep_9"],
    }

    assert _build_variant_similarity_rank(less_similar_variant, seen_variants) < _build_variant_similarity_rank(
        more_similar_variant,
        seen_variants,
    )


def test_variant_similarity_rank_penalizes_repeated_episode_transitions() -> None:
    seen_variant = {
        "target_duration_ms": 6000,
        "music_path": "",
        "opening_media_path": "",
        "closing_media_path": "",
        "selected_takes": [
            {"episode_id": "ep_1", "take_id": "take_1", "source_path": "a.mp4"},
            {"episode_id": "ep_2", "take_id": "take_2", "source_path": "b.mp4"},
            {"episode_id": "ep_3", "take_id": "take_3", "source_path": "c.mp4"},
        ],
        "episode_order": ["ep_1", "ep_2", "ep_3"],
    }
    more_similar_variant = {
        "target_duration_ms": 6000,
        "music_path": "",
        "opening_media_path": "",
        "closing_media_path": "",
        "selected_takes": [
            {"episode_id": "ep_4", "take_id": "take_4", "source_path": "d.mp4"},
            {"episode_id": "ep_2", "take_id": "take_5", "source_path": "b.mp4"},
            {"episode_id": "ep_3", "take_id": "take_6", "source_path": "c.mp4"},
        ],
        "episode_order": ["ep_4", "ep_2", "ep_3"],
    }
    less_similar_variant = {
        "target_duration_ms": 6000,
        "music_path": "",
        "opening_media_path": "",
        "closing_media_path": "",
        "selected_takes": [
            {"episode_id": "ep_4", "take_id": "take_4", "source_path": "d.mp4"},
            {"episode_id": "ep_5", "take_id": "take_5", "source_path": "e.mp4"},
            {"episode_id": "ep_6", "take_id": "take_6", "source_path": "f.mp4"},
        ],
        "episode_order": ["ep_4", "ep_5", "ep_6"],
    }

    assert _build_variant_similarity_rank(less_similar_variant, [seen_variant]) < _build_variant_similarity_rank(
        more_similar_variant,
        [seen_variant],
    )


def test_variant_similarity_rank_penalizes_reused_take_windows() -> None:
    seen_variant = {
        "target_duration_ms": 6000,
        "music_path": "",
        "opening_media_path": "",
        "closing_media_path": "",
        "selected_takes": [
            {
                "episode_id": "ep_1",
                "take_id": "take_1",
                "source_path": "a.mp4",
                "render_start_ms": 0,
                "render_end_ms": 2000,
            }
        ],
        "episode_order": ["ep_1"],
    }
    more_similar_variant = {
        "target_duration_ms": 6000,
        "music_path": "",
        "opening_media_path": "",
        "closing_media_path": "",
        "selected_takes": [
            {
                "episode_id": "ep_2",
                "take_id": "take_1",
                "source_path": "a.mp4",
                "render_start_ms": 0,
                "render_end_ms": 2000,
            }
        ],
        "episode_order": ["ep_2"],
    }
    less_similar_variant = {
        "target_duration_ms": 6000,
        "music_path": "",
        "opening_media_path": "",
        "closing_media_path": "",
        "selected_takes": [
            {
                "episode_id": "ep_2",
                "take_id": "take_1",
                "source_path": "a.mp4",
                "render_start_ms": 1500,
                "render_end_ms": 3500,
            }
        ],
        "episode_order": ["ep_2"],
    }

    assert _build_variant_similarity_rank(less_similar_variant, [seen_variant]) < _build_variant_similarity_rank(
        more_similar_variant,
        [seen_variant],
    )


def test_quick_mix_source_materials_rejects_duplicate_combinations_within_batch(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for name in ("clip_a.mp4", "clip_b.mp4", "clip_c.mp4", "clip_d.mp4", "clip_e.mp4"):
        (source_dir / name).write_bytes(b"video")

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 2000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    asset_paths = [source_dir / name for name in ("clip_a.mp4", "clip_b.mp4", "clip_c.mp4", "clip_d.mp4", "clip_e.mp4")]
    assets = [
        Asset(stable_id("asset", str(path.resolve())), "project", path.resolve(), MediaType.VIDEO, duration_ms=2000)
        for path in asset_paths
    ]

    def fake_build_episode_group_diversity_plan(
        _episode_groups,
        *,
        target_duration_ms,
        output_count,
        prior_plans=(),
        **_kwargs,
    ):
        base_segments = tuple(
            _fake_diversity_segment(
                asset,
                source_id=f"take_{index + 1}",
                folder_id=f"episode_{index + 1}",
                duration_ms=400,
            )
            for index, asset in enumerate(assets)
        )
        plans = [
            DiversityPlan(
                output_index=1,
                target_duration_ms=target_duration_ms,
                segments=base_segments,
            )
        ]
        return SimpleNamespace(
            batch=_fake_diversity_batch(
                plans,
                requested_output_count=output_count,
                warnings=(
                    {
                        "code": QUICK_MIX_DIVERSITY_EXHAUSTED,
                        "requested_output_count": output_count,
                        "achieved_output_count": 1,
                        "reason": "near_duplicate_rejected",
                    },
                ),
            )
        )

    def fake_render_segments_for_plan(plan, _adapter_result):
        rendered = []
        for step_index, segment in enumerate(plan.segments):
            asset = next(asset for asset in assets if asset.asset_id == segment.base_source_id)
            rendered.append(
                {
                    "asset": asset,
                    "start_ms": int(segment.source_start_ms),
                    "duration_ms": int(segment.duration_ms),
                    "step_index": step_index,
                    "segment_kind": "body",
                    "source_id": segment.source_id,
                    "folder_id": segment.folder_id,
                }
            )
        return rendered

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service.build_episode_group_diversity_plan", fake_build_episode_group_diversity_plan)
    monkeypatch.setattr("video_mix.service.render_segments_for_plan", fake_render_segments_for_plan)
    monkeypatch.setattr("video_mix.service.selected_take_manifest_for_plan", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=2,
        output_count=2,
        work_dir=str(tmp_path / "work"),
    )

    assert result["generated_count"] == 1
    assert result["quick_mix_warning_count"] == 2
    assert {warning["code"] for warning in result["quick_mix_warnings"]} == {QUICK_MIX_DIVERSITY_EXHAUSTED}
    quick_mix_plan = read_json(tmp_path / "work" / "reports" / "quick_mix_plan.json")
    assert [output["output_index"] for output in quick_mix_plan["outputs"]] == [1]


def test_quick_mix_source_materials_rejects_combinations_already_seen_in_workdir(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    clip_path = source_dir / "clip.mp4"
    clip_path.write_bytes(b"video")
    work_dir = tmp_path / "work"

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 2000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    asset = Asset(stable_id("asset", str(clip_path.resolve())), "project", clip_path.resolve(), MediaType.VIDEO, duration_ms=2000)
    planner_prior_counts: list[int] = []
    planner_music_values: list[tuple[str | None, int]] = []

    def fake_build_episode_group_diversity_plan(
        _episode_groups,
        *,
        target_duration_ms,
        output_count,
        prior_plans=(),
        music_path=None,
        music_start_ms=0,
        **_kwargs,
    ):
        planner_prior_counts.append(len(prior_plans))
        planner_music_values.append((str(music_path) if music_path is not None else None, int(music_start_ms)))
        plan = DiversityPlan(
            output_index=1,
            target_duration_ms=target_duration_ms,
            segments=(
                _fake_diversity_segment(asset, source_id="take_001", folder_id="episode_001", duration_ms=2000),
            ),
        )
        return SimpleNamespace(batch=_fake_diversity_batch([plan], requested_output_count=output_count))

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service.build_episode_group_diversity_plan", fake_build_episode_group_diversity_plan)
    monkeypatch.setattr(
        "video_mix.service.render_segments_for_plan",
        lambda *_args, **_kwargs: [
            {
                "asset": asset,
                "start_ms": 0,
                "duration_ms": 2000,
                "step_index": 0,
                "segment_kind": "body",
                "source_id": "take_001",
                "folder_id": "episode_001",
            }
        ],
    )
    monkeypatch.setattr(
        "video_mix.service.selected_take_manifest_for_plan",
        lambda *_args, **_kwargs: [
            {
                "episode_id": "episode_001",
                "episode_label": "episode_001",
                "take_id": "take_001",
                "take_index": 1,
                "marker_split": False,
                "asset_id": asset.asset_id,
                "media_type": "video",
                "normalized_source_group": "clip.mp4",
                "source_path": str(asset.path),
                "source_start_ms": 0,
                "source_end_ms": 2000,
                "render_start_ms": 0,
                "render_end_ms": 2000,
            }
        ],
    )
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    music_one = tmp_path / "music_one.mp3"
    music_two = tmp_path / "music_two.mp3"
    music_one.write_bytes(b"audio-1")
    music_two.write_bytes(b"audio-2")
    monkeypatch.setattr("video_mix.service._resolve_audio_track_duration_ms", lambda *_args, **_kwargs: 5000)
    monkeypatch.setattr("video_mix.service._select_music_start_ms", lambda path, **_kwargs: 1200 if Path(path) == music_two else 0)

    quick_mix_source_materials(
        str(source_dir),
        duration_seconds=2,
        output_count=1,
        work_dir=str(work_dir),
        music_path=str(music_one),
    )
    quick_mix_source_materials(
        str(source_dir),
        duration_seconds=2,
        output_count=1,
        work_dir=str(work_dir),
        music_path=str(music_two),
    )

    assert planner_prior_counts == [0, 1]
    assert planner_music_values == [(None, 0), (None, 0)]


def test_quick_mix_plan_manifest_contains_full_opening_body_closing_sequence(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    clip_path = source_dir / "clip.mp4"
    clip_path.write_bytes(b"video")
    opening_path = tmp_path / "opening.mp4"
    opening_path.write_bytes(b"opening")
    closing_path = tmp_path / "closing.mp4"
    closing_path.write_bytes(b"closing")
    work_dir = tmp_path / "work"

    def fake_probe_assets(assets, ffprobe_path="ffprobe"):
        for asset in assets:
            asset.duration_ms = 2000
            asset.width = 1080
            asset.height = 1920
            asset.fps = 30.0
            asset.orientation = Orientation.VERTICAL
            asset.probe_status = "ok"
        return assets

    body_asset = Asset(stable_id("asset", str(clip_path.resolve())), "project", clip_path.resolve(), MediaType.VIDEO, duration_ms=2000)
    opening_asset = Asset(stable_id("asset", str(opening_path.resolve())), "project", opening_path.resolve(), MediaType.VIDEO, duration_ms=1200)
    closing_asset = Asset(stable_id("asset", str(closing_path.resolve())), "project", closing_path.resolve(), MediaType.VIDEO, duration_ms=1500)

    def fake_build_episode_group_diversity_plan(
        _episode_groups,
        *,
        target_duration_ms,
        output_count,
        **_kwargs,
    ):
        plan = DiversityPlan(
            output_index=1,
            target_duration_ms=target_duration_ms,
            segments=(
                _fake_diversity_segment(
                    body_asset,
                    source_id="take_001",
                    folder_id="episode_001",
                    duration_ms=target_duration_ms,
                    source_group="clip.mp4",
                ),
            ),
        )
        return SimpleNamespace(batch=_fake_diversity_batch([plan], requested_output_count=output_count))

    monkeypatch.setattr("video_mix.service.probe_assets", fake_probe_assets)
    monkeypatch.setattr("video_mix.service._ensure_ffmpeg_available", lambda ffmpeg_path: None)
    monkeypatch.setattr("video_mix.service.build_episode_group_diversity_plan", fake_build_episode_group_diversity_plan)
    monkeypatch.setattr(
        "video_mix.service.render_segments_for_plan",
        lambda *_args, **_kwargs: [
            {
                "asset": body_asset,
                "start_ms": 400,
                "duration_ms": 4000,
                "step_index": 0,
                "segment_kind": "body",
                "source_id": "take_001",
                "folder_id": "episode_001",
            }
        ],
    )
    monkeypatch.setattr(
        "video_mix.service.selected_take_manifest_for_plan",
        lambda *_args, **_kwargs: [
            {
                "episode_id": "episode_001",
                "episode_label": "episode_001",
                "take_id": "take_001",
                "take_index": 1,
                "marker_split": False,
                "asset_id": body_asset.asset_id,
                "media_type": "video",
                "normalized_source_group": "clip.mp4",
                "source_path": str(body_asset.path),
                "source_start_ms": 0,
                "source_end_ms": 2000,
                "render_start_ms": 400,
                "render_end_ms": 4400,
            }
        ],
    )
    monkeypatch.setattr("video_mix.service._render_quick_mix_segment", lambda *args, **kwargs: Path(args[1]).write_bytes(b"seg"))
    monkeypatch.setattr("video_mix.service._render_quick_mix_output", lambda *args, **kwargs: Path(args[1]).write_bytes(b"out"))

    result = quick_mix_source_materials(
        str(source_dir),
        duration_seconds=6,
        output_count=1,
        work_dir=str(work_dir),
        opening_media_path=str(opening_path),
        closing_media_path=str(closing_path),
        use_closing_duration=True,
    )

    compatibility_plan = read_json(work_dir / "reports" / "quick_mix_plan.json")
    generation_plan = read_json(work_dir / result["quick_mix_generation_plan_path"])
    output = compatibility_plan["outputs"][0]
    assert output == generation_plan["outputs"][0]
    assert [segment["segment_kind"] for segment in output["segments"]] == [
        "opening",
        "body",
        "closing",
    ]
    assert output["body_visual_signature"] == ["take_001@0:4000"]
    assert output["generated_duration_ms"] == sum(segment["duration_ms"] for segment in output["segments"])
    body_segments = [segment for segment in output["segments"] if segment["segment_kind"] == "body"]
    assert [segment["source_start_ms"] for segment in body_segments] == [400]
    assert [segment["base_source_id"] for segment in body_segments] == [body_asset.asset_id]
    assert [segment["source_group"] for segment in body_segments] == ["clip.mp4"]
    assert opening_asset.asset_id not in {segment["base_source_id"] for segment in body_segments}
    assert closing_asset.asset_id not in {segment["base_source_id"] for segment in body_segments}
