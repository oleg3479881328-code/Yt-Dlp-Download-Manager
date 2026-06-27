from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from video_mix.core.models import CandidateStatus, Clip, MediaType, Orientation, Project, SegmenterName
from video_mix.core.storage import (
    build_asset,
    build_candidate,
    load_candidates,
    save_assets,
    save_candidates,
    save_clips,
    save_project,
    save_summary,
)

client = TestClient(app)


def create_video_mix_workdir(tmp_path: Path, status: CandidateStatus = CandidateStatus.GENERATED) -> Path:
    work_dir = tmp_path / "work"
    source_path = tmp_path / "input" / "rings_detail.mp4"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"demo-video")

    project = Project(
        project_id="project_1",
        name="Wedding Validation",
        root_path=tmp_path / "input",
        industry_pack="wedding",
    )
    asset = build_asset(
        {
            "asset_id": "asset_1",
            "project_id": "project_1",
            "path": str(source_path),
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
    clip = Clip(
        clip_id="clip_1",
        project_id="project_1",
        asset_id="asset_1",
        source_path=source_path,
        source_start_ms=0,
        source_end_ms=3000,
        segmenter=SegmenterName.FIXED_INTERVAL,
        working_path=tmp_path / "work" / "clips" / "clip_1.mp4",
        tags=["details", "rings"],
        quality_score=88.0,
    )
    candidate = build_candidate(
        {
            "candidate_id": "cand_1",
            "project_id": "project_1",
            "pack_id": "wedding",
            "template_id": "romantic_story",
            "status": status.value,
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

    save_project(work_dir, project)
    save_assets(work_dir, [asset])
    save_clips(work_dir, [clip])
    save_candidates(work_dir, [candidate])
    save_summary(
        work_dir,
        {
            "project_id": project.project_id,
            "project_name": project.name,
            "pack_id": project.industry_pack,
            "asset_count": 1,
            "clip_count": 1,
            "candidate_count": 1,
            "approved_candidate_count": 1 if status == CandidateStatus.APPROVED else 0,
            "exported_candidate_count": 1 if status == CandidateStatus.EXPORTED else 0,
            "generated_candidate_ids": ["cand_1"],
        },
    )

    reports_dir = work_dir / "reports"
    thumbnails_dir = reports_dir / "thumbnails"
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "review.html").write_text("<html>review</html>", encoding="utf-8")
    (thumbnails_dir / "clip_1.jpg").write_bytes(b"jpg-data")
    if status == CandidateStatus.EXPORTED:
        exports_dir = work_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        (exports_dir / "wedding_validation_wedding_romantic_story_cand_1.mp4").write_bytes(b"mp4")

    return work_dir


def test_video_mix_dashboard_reads_candidate_cards(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)

    response = client.get("/api/video-mix/dashboard", params={"work_dir": str(work_dir)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["name"] == "Wedding Validation"
    assert payload["summary"]["candidate_count"] == 1
    assert payload["candidates"][0]["candidate_id"] == "cand_1"
    assert payload["candidates"][0]["thumbnail_path"] == "reports/thumbnails/clip_1.jpg"
    assert payload["candidates"][0]["source_filenames"] == ["rings_detail.mp4"]


def test_video_mix_dashboard_approve_updates_candidate_status(tmp_path: Path, monkeypatch) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    monkeypatch.setattr("app.video_mix_dashboard.write_review_html", lambda *args, **kwargs: (work_dir / "reports" / "review.html", 1, {}))

    response = client.post(
        "/api/video-mix/candidates/cand_1/approve",
        json={"work_dir": str(work_dir), "note": "owner approved"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dashboard"]["candidates"][0]["status"] == "approved"
    assert payload["dashboard"]["candidates"][0]["review_notes"] == "owner approved"


def test_video_mix_dashboard_export_uses_existing_export_flow(tmp_path: Path, monkeypatch) -> None:
    work_dir = create_video_mix_workdir(tmp_path, status=CandidateStatus.APPROVED)
    export_path = work_dir / "exports" / "wedding_validation_wedding_romantic_story_cand_1.mp4"
    export_path.parent.mkdir(parents=True, exist_ok=True)

    def fake_export_candidate(**_: object):
        export_path.write_bytes(b"mp4")

        class Plan:
            output_path = export_path

        return Plan()

    monkeypatch.setattr("app.video_mix_dashboard.export_candidate", fake_export_candidate)
    monkeypatch.setattr("app.video_mix_dashboard.write_review_html", lambda *args, **kwargs: (work_dir / "reports" / "review.html", 1, {}))

    response = client.post("/api/video-mix/export", json={"work_dir": str(work_dir), "ffmpeg": "ffmpeg"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["exported_paths"] == ["exports/wedding_validation_wedding_romantic_story_cand_1.mp4"]
    assert payload["dashboard"]["candidates"][0]["status"] == "exported"


def test_video_mix_file_endpoint_restricts_allowed_artifacts(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    secret = work_dir / "reports" / "assets.json"
    secret.write_text("not allowed", encoding="utf-8")

    response = client.get(
        "/api/video-mix/file",
        params={"work_dir": str(work_dir), "relative_path": "reports/assets.json"},
    )

    assert response.status_code == 403
    assert "allowed dashboard artifacts" in response.json()["detail"]


def test_video_mix_dashboard_approve_does_not_regenerate_thumbnails(tmp_path: Path, monkeypatch) -> None:
    work_dir = create_video_mix_workdir(tmp_path)

    def fail_generate(*_args, **_kwargs):
        raise AssertionError("thumbnail generation should not run for metadata-only approve")

    monkeypatch.setattr("video_mix.core.review.generate_thumbnails", fail_generate)

    response = client.post(
        "/api/video-mix/candidates/cand_1/approve",
        json={"work_dir": str(work_dir), "note": "owner approved"},
    )

    assert response.status_code == 200
    assert response.json()["dashboard"]["candidates"][0]["status"] == "approved"


def test_video_mix_dashboard_bulk_approve_updates_multiple_candidates(tmp_path: Path, monkeypatch) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    candidates = load_candidates(work_dir)
    second = build_candidate(
        {
            "candidate_id": "cand_2",
            "project_id": "project_1",
            "pack_id": "wedding",
            "template_id": "fast_highlight",
            "status": CandidateStatus.GENERATED.value,
            "score": 77.0,
            "duration_ms": 2500,
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
            "review_notes": "",
        }
    )
    save_candidates(work_dir, [*candidates, second])
    monkeypatch.setattr("app.video_mix_dashboard.write_review_html", lambda *args, **kwargs: (work_dir / "reports" / "review.html", 1, {}))

    response = client.post(
        "/api/video-mix/candidates/bulk/approve",
        json={"work_dir": str(work_dir), "candidate_ids": ["cand_1", "cand_2"], "note": "bulk approved"},
    )

    assert response.status_code == 200
    statuses = {candidate["candidate_id"]: candidate["status"] for candidate in response.json()["dashboard"]["candidates"]}
    assert statuses["cand_1"] == "approved"
    assert statuses["cand_2"] == "approved"


def test_video_mix_dashboard_bulk_reject_reports_invalid_candidate_id(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)

    response = client.post(
        "/api/video-mix/candidates/bulk/reject",
        json={"work_dir": str(work_dir), "candidate_ids": ["cand_missing"]},
    )

    assert response.status_code == 404
    assert "Candidate not found" in response.json()["detail"]


def test_video_mix_dashboard_pick_workdir_returns_selected_valid_directory(tmp_path: Path, monkeypatch) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    monkeypatch.setattr("app.video_mix_dashboard._show_windows_folder_picker", lambda *_args, **_kwargs: str(work_dir))

    response = client.post("/api/video-mix/pick-workdir", json={"initial_dir": str(tmp_path)})

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "canceled": False,
        "work_dir": str(work_dir.resolve()),
    }


def test_video_mix_dashboard_pick_workdir_reports_cancel_without_error(tmp_path: Path, monkeypatch) -> None:
    create_video_mix_workdir(tmp_path)
    monkeypatch.setattr("app.video_mix_dashboard._show_windows_folder_picker", lambda *_args, **_kwargs: "")

    response = client.post("/api/video-mix/pick-workdir", json={"initial_dir": str(tmp_path)})

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "canceled": True,
        "work_dir": "",
    }


def test_video_mix_dashboard_pick_source_folder_returns_selected_directory(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    monkeypatch.setattr("app.video_mix_dashboard._show_windows_folder_picker", lambda *_args, **_kwargs: str(source_dir))

    response = client.post("/api/video-mix/pick-source-folder", json={"initial_dir": str(tmp_path)})

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "canceled": False,
        "source_dir": str(source_dir.resolve()),
    }


def test_video_mix_dashboard_source_scan_returns_summary(tmp_path: Path, monkeypatch) -> None:
    expected = {
        "source_dir": str(tmp_path.resolve()),
        "total_files": 4,
        "supported_media_count": 2,
        "supported_video_count": 1,
        "supported_photo_count": 1,
        "ignored_or_unsupported_count": 2,
        "ignored_skipped_dir_count": 0,
        "preview_files": ["a.mp4", "b.jpg"],
        "suggested_work_dir": str((tmp_path / "_video_mix_work").resolve()),
    }
    monkeypatch.setattr("app.main.scan_source_materials", lambda source_dir: expected)

    response = client.post("/api/video-mix/source/scan", json={"source_dir": str(tmp_path)})

    assert response.status_code == 200
    assert response.json() == {"ok": True, **expected}


def test_video_mix_dashboard_source_plan_returns_dashboard_payload(tmp_path: Path, monkeypatch) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    expected = {
        "source_dir": str((tmp_path / "source").resolve()),
        "work_dir": str(work_dir.resolve()),
        "project_name": "Wedding Validation",
        "pack": "wedding",
        "asset_count": 1,
        "clip_count": 1,
        "candidate_count": 1,
        "review_path": str((work_dir / "reports" / "review.html").resolve()),
        "thumbnail_count": 1,
        "thumbnail_warning_count": 0,
    }
    monkeypatch.setattr("app.main.plan_source_materials", lambda *args, **kwargs: expected)

    response = client.post(
        "/api/video-mix/source/plan",
        json={"source_dir": str(tmp_path / "source"), "project_name": "Wedding Validation", "work_dir": str(work_dir)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["work_dir"] == expected["work_dir"]
    assert payload["asset_count"] == 1
    assert payload["dashboard"]["summary"]["candidate_count"] == 1
