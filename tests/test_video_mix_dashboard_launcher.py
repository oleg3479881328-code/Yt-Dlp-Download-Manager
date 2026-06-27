from __future__ import annotations

from pathlib import Path

from tests.test_video_mix_dashboard_api import create_video_mix_workdir
from video_mix.dashboard_launcher import detect_work_dir, run_diagnostics


def test_detect_work_dir_prefers_requested_path(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)

    detected = detect_work_dir(tmp_path, work_dir)

    assert detected == work_dir.resolve()


def test_detect_work_dir_finds_validation_default(tmp_path: Path) -> None:
    validation_root = tmp_path / "video_mix_validation"
    work_dir = create_video_mix_workdir(validation_root)

    detected = detect_work_dir(tmp_path)

    assert detected == work_dir.resolve()


def test_run_diagnostics_reports_valid_work_dir(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)

    result = run_diagnostics(tmp_path, work_dir)

    assert result["checks"]["work_dir"]["ok"] is True
    assert result["checks"]["work_dir"]["review_exists"] is True
    assert result["work_dir"] == str(work_dir.resolve())


def test_run_diagnostics_reports_missing_work_dir(tmp_path: Path) -> None:
    result = run_diagnostics(tmp_path, None)

    assert result["checks"]["work_dir"]["ok"] is False
    assert result["work_dir"] is None
