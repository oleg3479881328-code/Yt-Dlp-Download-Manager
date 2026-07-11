from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from video_mix.core.models import Orientation
from video_mix.core.storage import read_json
from video_mix.core.zip_intake import import_video_mix_zip


def _write_zip(zip_path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(zip_path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def _fake_probe_assets(assets, ffprobe_path="ffprobe"):
    for asset in assets:
        asset.duration_ms = 4000 if asset.path.suffix.lower() == ".mp4" else 1000
        asset.width = 1080
        asset.height = 1920
        asset.fps = 30.0
        asset.orientation = Orientation.VERTICAL
        asset.has_audio = asset.path.suffix.lower() == ".mp4"
        asset.probe_status = "ok"
    return assets


def test_zip_first_level_folders_become_blocks_and_numeric_prefix_sets_order(tmp_path: Path, monkeypatch) -> None:
    zip_path = tmp_path / "wedding_project.zip"
    _write_zip(
        zip_path,
        {
            "wedding_project/02_Гости/guests_01.mp4": b"video",
            "wedding_project/01_Невеста/bride_01.mp4": b"video",
            "wedding_project/03_Атмосфера/candles.jpg": b"image",
        },
    )
    monkeypatch.setattr("video_mix.core.zip_intake.probe_assets", _fake_probe_assets)
    monkeypatch.setattr("video_mix.service._detect_magenta_marker_ranges", lambda *_args, **_kwargs: [])

    result = import_video_mix_zip(zip_path, work_dir=str(tmp_path / "work"))

    report = result["zip_import_report"]
    assert [block["label"] for block in report["blocks"]] == ["Невеста", "Гости", "Атмосфера"]
    assert [block["position"] for block in report["blocks"]] == [1, 2, 3]
    assert report["block_count"] == 3
    assert report["total_take_count"] == 3

    state_payload = read_json(tmp_path / "work" / "reports" / "project_materials_state.json")
    assert [episode["label"] for episode in state_payload["episodes"]] == ["Невеста", "Гости", "Атмосфера"]


def test_zip_root_files_go_to_unsorted_block_with_warning(tmp_path: Path, monkeypatch) -> None:
    zip_path = tmp_path / "root_files.zip"
    _write_zip(
        zip_path,
        {
            "root_files/clip.mp4": b"video",
            "root_files/01_Невеста/bride.mp4": b"video",
        },
    )
    monkeypatch.setattr("video_mix.core.zip_intake.probe_assets", _fake_probe_assets)
    monkeypatch.setattr("video_mix.service._detect_magenta_marker_ranges", lambda *_args, **_kwargs: [])

    result = import_video_mix_zip(zip_path, work_dir=str(tmp_path / "work"))

    report = result["zip_import_report"]
    assert report["warning_count"] >= 1
    assert any(block["label"] == "Без блока" for block in report["blocks"])


def test_zip_nested_folders_stay_inside_parent_block(tmp_path: Path, monkeypatch) -> None:
    zip_path = tmp_path / "nested.zip"
    _write_zip(
        zip_path,
        {
            "nested/01_Невеста/утро/bride_01.mp4": b"video",
            "nested/01_Невеста/утро/bride_02.jpg": b"image",
        },
    )
    monkeypatch.setattr("video_mix.core.zip_intake.probe_assets", _fake_probe_assets)
    monkeypatch.setattr("video_mix.service._detect_magenta_marker_ranges", lambda *_args, **_kwargs: [])

    result = import_video_mix_zip(zip_path, work_dir=str(tmp_path / "work"))

    block = result["zip_import_report"]["blocks"][0]
    assert block["label"] == "Невеста"
    assert len(block["takes"]) == 2
    assert all(take["subfolder"] == "утро" for take in block["takes"])


def test_zip_rejects_path_traversal_members(tmp_path: Path, monkeypatch) -> None:
    zip_path = tmp_path / "unsafe.zip"
    _write_zip(
        zip_path,
        {
            "../evil.mp4": b"video",
        },
    )
    monkeypatch.setattr("video_mix.core.zip_intake.probe_assets", _fake_probe_assets)

    with pytest.raises(ValueError, match="unsafe path"):
        import_video_mix_zip(zip_path, work_dir=str(tmp_path / "work"))


def test_zip_rejects_duplicate_normalized_destinations(tmp_path: Path, monkeypatch) -> None:
    zip_path = tmp_path / "duplicate.zip"
    _write_zip(
        zip_path,
        {
            "folder/clip.mp4": b"video-a",
            "folder\\clip.mp4": b"video-b",
        },
    )
    monkeypatch.setattr("video_mix.core.zip_intake.probe_assets", _fake_probe_assets)

    with pytest.raises(ValueError, match="duplicate destination paths"):
        import_video_mix_zip(zip_path, work_dir=str(tmp_path / "work"))


def test_zip_marker_video_creates_multiple_takes_inside_same_block(tmp_path: Path, monkeypatch) -> None:
    zip_path = tmp_path / "markers.zip"
    _write_zip(
        zip_path,
        {
            "markers/01_Невеста/bride_long.mp4": b"video",
        },
    )
    monkeypatch.setattr("video_mix.core.zip_intake.probe_assets", _fake_probe_assets)
    monkeypatch.setattr("video_mix.service._detect_magenta_marker_ranges", lambda *_args, **_kwargs: [(1000, 1400), (2200, 2600)])

    result = import_video_mix_zip(zip_path, work_dir=str(tmp_path / "work"))

    report = result["zip_import_report"]
    assert report["marker_video_count"] == 1
    assert report["marker_split_take_count"] == 3
    assert report["blocks"][0]["label"] == "Невеста"
    assert len(report["blocks"][0]["takes"]) == 3
