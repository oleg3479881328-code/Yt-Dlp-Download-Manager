from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from video_mix.core.models import CandidateStatus, Clip, MediaType, Orientation, Project, SegmenterName
from video_mix.core.storage import (
    build_asset,
    build_candidate,
    load_assets,
    load_candidates,
    read_json,
    save_assets,
    save_candidates,
    save_clips,
    save_project,
    save_summary,
    work_file,
)
from video_mix.proxy_pipeline import PROXY_MISSING, ProxyQueueManager, load_proxy_manifest, save_proxy_manifest

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


def add_video_mix_asset(tmp_path: Path, work_dir: Path, asset_id: str, file_name: str, duration_ms: int = 5000) -> None:
    source_path = tmp_path / "input" / file_name
    source_path.write_bytes(b"demo-video")
    existing_assets = load_assets(work_dir)
    existing_assets.append(
        build_asset(
            {
                "asset_id": asset_id,
                "project_id": "project_1",
                "path": str(source_path),
                "media_type": MediaType.VIDEO.value,
                "duration_ms": duration_ms,
                "width": 1080,
                "height": 1920,
                "fps": 30.0,
                "orientation": Orientation.VERTICAL.value,
                "has_audio": True,
                "probe_status": "ok",
                "quality_score": 79.0,
                "metadata": {},
            }
        )
    )
    save_assets(work_dir, existing_assets)


def add_photo_mix_asset(tmp_path: Path, work_dir: Path, asset_id: str, file_name: str) -> None:
    source_path = tmp_path / "input" / file_name
    source_path.write_bytes(b"demo-photo")
    existing_assets = load_assets(work_dir)
    existing_assets.append(
        build_asset(
            {
                "asset_id": asset_id,
                "project_id": "project_1",
                "path": str(source_path),
                "media_type": MediaType.PHOTO.value,
                "duration_ms": None,
                "width": 1080,
                "height": 1920,
                "fps": None,
                "orientation": Orientation.VERTICAL.value,
                "has_audio": False,
                "probe_status": "skipped_photo",
                "quality_score": 70.0,
                "metadata": {},
            }
        )
    )
    save_assets(work_dir, existing_assets)


def test_video_mix_dashboard_reads_candidate_cards(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    (work_dir / "reports" / "quick_mix.json").write_text(
        '{"source_dir":"C:\\\\demo\\\\source","work_dir":"C:\\\\demo\\\\work","duration_seconds":10,"output_count":2,"generated_count":2,"music_path":"","opening_media_path":"","closing_media_path":"","output_paths":["exports/quick_mix_001.mp4"]}',
        encoding="utf-8",
    )

    response = client.get("/api/video-mix/dashboard", params={"work_dir": str(work_dir)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["name"] == "Wedding Validation"
    assert payload["summary"]["candidate_count"] == 1
    assert payload["quick_mix"]["source_dir"] == "C:\\demo\\source"
    assert payload["candidates"][0]["candidate_id"] == "cand_1"
    assert payload["candidates"][0]["thumbnail_path"] == "reports/thumbnails/clip_1.jpg"
    assert payload["candidates"][0]["source_filenames"] == ["rings_detail.mp4"]
    assert payload["project_files"]["file_count"] == 1
    assert payload["project_files"]["files"][0]["relative_path"] == "rings_detail.mp4"
    assert payload["video_proxies"]["summary"]["total"] == 1
    assert payload["video_proxies"]["summary"]["missing"] == 1


def test_video_mix_proxies_endpoint_returns_missing_proxy_summary(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)

    response = client.get("/api/video-mix/proxies", params={"work_dir": str(work_dir)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 1
    assert payload["summary"]["missing"] == 1
    assert payload["items"][0]["asset_id"] == "asset_1"
    assert payload["items"][0]["proxy_absolute_path"] == ""


def test_video_mix_dashboard_handles_missing_original_without_crashing(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    missing_original = tmp_path / "input" / "rings_detail.mp4"
    missing_original.unlink()

    response = client.get("/api/video-mix/dashboard", params={"work_dir": str(work_dir)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["video_proxies"]["summary"]["total"] == 1
    assert payload["video_proxies"]["summary"]["missing"] == 1
    assert payload["video_proxies"]["items"][0]["asset_id"] == "asset_1"
    assert payload["video_proxies"]["items"][0]["status"] == PROXY_MISSING
    assert "Original source is missing" in payload["video_proxies"]["items"][0]["error"]


def test_video_mix_proxies_endpoint_reports_missing_original_asset(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    missing_original = tmp_path / "input" / "rings_detail.mp4"
    missing_original.unlink()

    response = client.get("/api/video-mix/proxies", params={"work_dir": str(work_dir)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 1
    assert payload["summary"]["missing"] == 1
    assert payload["items"][0]["status"] == PROXY_MISSING
    assert "Original source is missing" in payload["items"][0]["error"]


def test_video_mix_proxies_dashboard_recovers_cancelled_pending_entry_without_proxy_file(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    manifest = load_proxy_manifest(work_dir)
    manifest["entries"]["asset_1"] = {
        "asset_id": "asset_1",
        "original_path": str((tmp_path / "input" / "rings_detail.mp4").resolve()),
        "proxy_path": "video_proxies/asset_1.proxy.mp4",
        "source_fingerprint": "source-fingerprint",
        "profile_fingerprint": "profile-fingerprint",
        "status": "pending",
        "original_duration_ms": 4000,
        "proxy_duration_ms": 0,
        "original_width": 1080,
        "original_height": 1920,
        "proxy_width": 0,
        "proxy_height": 0,
        "created_at": "",
        "updated_at": "",
        "error": "Proxy job was cancelled",
        "has_audio": True,
    }
    save_proxy_manifest(work_dir, manifest)

    payload = ProxyQueueManager().dashboard_payload(work_dir)

    assert payload["summary"]["running"] == 0
    assert payload["summary"]["missing"] == 1
    assert payload["items"][0]["status"] == PROXY_MISSING
    assert payload["items"][0]["error"] == "Proxy job was cancelled"


def test_video_mix_delete_proxy_clears_stale_job_progress_from_dashboard(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    proxy_path = work_dir / "video_proxies" / "asset_1.proxy.mp4"
    proxy_path.parent.mkdir(parents=True, exist_ok=True)
    proxy_path.write_bytes(b"proxy-data")

    manifest = load_proxy_manifest(work_dir)
    manifest["entries"]["asset_1"] = {
        "asset_id": "asset_1",
        "original_path": str((tmp_path / "input" / "rings_detail.mp4").resolve()),
        "proxy_path": "video_proxies/asset_1.proxy.mp4",
        "source_fingerprint": "source-fingerprint",
        "profile_fingerprint": "profile-fingerprint",
        "status": "ready",
        "original_duration_ms": 4000,
        "proxy_duration_ms": 4010,
        "original_width": 1080,
        "original_height": 1920,
        "proxy_width": 720,
        "proxy_height": 1280,
        "created_at": "",
        "updated_at": "",
        "error": "",
        "has_audio": True,
    }
    save_proxy_manifest(work_dir, manifest)

    manager = ProxyQueueManager()
    work_key = str(work_dir.resolve())
    manager._jobs_by_work_dir[work_key] = {
        "asset_1": manager._jobs_by_work_dir.get(work_key, {}).get("asset_1")
    }
    manager._jobs_by_work_dir[work_key]["asset_1"] = type("JobStub", (), {"asset_id": "asset_1"})()

    payload = manager.delete_proxy(work_dir, "asset_1")

    assert not proxy_path.exists()
    assert "asset_1" not in manager._jobs_by_work_dir[work_key]
    assert payload["summary"]["missing"] == 1
    assert payload["items"][0]["status"] == PROXY_MISSING


def test_video_mix_project_files_endpoint_lists_source_files(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    extra = tmp_path / "input" / "notes.txt"
    extra.write_text("hello", encoding="utf-8")

    response = client.get("/api/video-mix/project-files", params={"work_dir": str(work_dir)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_count"] == 2
    assert {item["relative_path"] for item in payload["files"]} == {"rings_detail.mp4", "notes.txt"}


def test_gitignore_covers_video_proxy_derived_artifacts() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "**/video_proxies/" in gitignore
    assert "**/reports/video_proxy_manifest.json" in gitignore
    assert "**/reports/video_proxy_jobs/" in gitignore


def test_video_mix_project_files_add_copies_files_into_project(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    external_file = tmp_path / "external" / "new_clip.mp4"
    external_file.parent.mkdir(parents=True, exist_ok=True)
    external_file.write_bytes(b"fresh-video")

    response = client.post(
        "/api/video-mix/project-files/add",
        json={"work_dir": str(work_dir), "file_paths": [str(external_file)]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["added_files"] == ["new_clip.mp4"]
    assert (tmp_path / "input" / "new_clip.mp4").exists()
    assert payload["project_files"]["file_count"] == 2
    assert {item["relative_path"] for item in payload["project_files"]["files"]} == {"rings_detail.mp4", "new_clip.mp4"}


def test_video_mix_project_files_remove_deletes_file_from_project(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    extra = tmp_path / "input" / "nested" / "remove_me.mp4"
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_bytes(b"remove")

    response = client.post(
        "/api/video-mix/project-files/remove",
        json={"work_dir": str(work_dir), "relative_path": "nested/remove_me.mp4"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["removed_file"] == "nested/remove_me.mp4"
    assert not extra.exists()
    assert payload["project_files"]["file_count"] == 1
    assert payload["project_files"]["files"][0]["relative_path"] == "rings_detail.mp4"


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


def test_video_mix_dashboard_pick_file_returns_selected_file(tmp_path: Path, monkeypatch) -> None:
    selected_file = tmp_path / "music.mp3"
    selected_file.write_bytes(b"audio")
    monkeypatch.setattr("app.video_mix_dashboard._show_windows_file_picker", lambda *_args, **_kwargs: str(selected_file))

    response = client.post("/api/video-mix/pick-file", json={"initial_dir": str(tmp_path), "title": "Select music track"})

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "canceled": False,
        "file_path": str(selected_file.resolve()),
    }


def test_video_mix_dashboard_upload_file_returns_staged_temp_path() -> None:
    response = client.post(
        "/api/video-mix/upload-file",
        content=b"audio-bytes",
        headers={
            "x-video-mix-upload-purpose": "music",
            "x-video-mix-upload-filename": "track.mp3",
            "content-type": "audio/mpeg",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["purpose"] == "music"
    assert payload["original_filename"] == "track.mp3"
    assert payload["file_path"].endswith(".mp3")
    assert Path(payload["file_path"]).exists()


def test_video_mix_dashboard_upload_file_decodes_encoded_unicode_filename() -> None:
    response = client.post(
        "/api/video-mix/upload-file",
        content=b"zip-bytes",
        headers={
            "x-video-mix-upload-purpose": "source_zip",
            "x-video-mix-upload-filename": "%D0%A1%D0%B2%D0%B0%D0%B4%D1%8C%D0%B1%D0%B0%20%D0%B2%20%D0%A7%D0%B8%D0%BA%D0%B0%D0%B3%D0%BE.zip",
            "content-type": "application/zip",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["original_filename"] == "Свадьба в Чикаго.zip"
    assert payload["file_path"].endswith(".zip")
    assert Path(payload["file_path"]).exists()


def test_video_mix_dashboard_upload_file_supports_source_tree_session() -> None:
    response = client.post(
        "/api/video-mix/upload-file",
        content=b"video-bytes",
        headers={
            "x-video-mix-upload-purpose": "source_tree",
            "x-video-mix-upload-filename": "clip.mp4",
            "x-video-mix-upload-session": "session_1",
            "x-video-mix-upload-relative-path": "nested/clip.mp4",
            "content-type": "video/mp4",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["upload_session"] == "session_1"
    assert payload["relative_path"] == "nested/clip.mp4"
    assert Path(payload["root_dir"]).exists()
    assert Path(payload["file_path"]).exists()


def test_video_mix_import_zip_path_returns_dashboard_payload(tmp_path: Path, monkeypatch) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    expected = {
        "source_zip": str((tmp_path / "bundle.zip").resolve()),
        "work_dir": str(work_dir.resolve()),
        "project_name": "ZIP Import",
        "project_root": str((tmp_path / "imports" / "bundle").resolve()),
        "zip_import_report": {
            "zip_filename": "bundle.zip",
            "extracted_root": str((tmp_path / "imports" / "bundle").resolve()),
            "blocks": [{"block_id": "block_1", "label": "Невеста", "position": 1, "source_folder": "01_Невеста", "takes": []}],
            "warnings": [],
            "ignored_files": [],
            "supported_file_count": 1,
            "marker_split_take_count": 0,
            "marker_video_count": 0,
            "total_take_count": 1,
            "block_count": 1,
            "warning_count": 0,
            "ignored_file_count": 0,
        },
        "warnings": [],
    }
    monkeypatch.setattr("app.main.import_video_mix_zip", lambda *args, **kwargs: expected)

    response = client.post(
        "/api/video-mix/import-zip-path",
        json={
            "zip_path": str(tmp_path / "bundle.zip"),
            "project_name": "ZIP Import",
            "work_dir": str(work_dir),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["project_name"] == "ZIP Import"
    assert payload["zip_import_report"]["block_count"] == 1
    assert payload["dashboard"]["summary"]["candidate_count"] == 1


def test_video_mix_import_zip_upload_accepts_multipart(tmp_path: Path, monkeypatch) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    expected = {
        "source_zip": str((tmp_path / "bundle.zip").resolve()),
        "work_dir": str(work_dir.resolve()),
        "project_name": "ZIP Upload",
        "project_root": str((tmp_path / "imports" / "bundle").resolve()),
        "zip_import_report": {
            "zip_filename": "bundle.zip",
            "extracted_root": str((tmp_path / "imports" / "bundle").resolve()),
            "blocks": [],
            "warnings": [],
            "ignored_files": [],
            "supported_file_count": 1,
            "marker_split_take_count": 0,
            "marker_video_count": 0,
            "total_take_count": 0,
            "block_count": 0,
            "warning_count": 0,
            "ignored_file_count": 0,
        },
        "warnings": [],
    }
    monkeypatch.setattr("app.main.import_video_mix_zip", lambda *args, **kwargs: expected)

    response = client.post(
        "/api/video-mix/import-zip",
        data={"project_name": "ZIP Upload", "work_dir": str(work_dir)},
        files={"file": ("bundle.zip", b"zip-bytes", "application/zip")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["project_name"] == "ZIP Upload"
    assert payload["dashboard"]["project"]["name"] == "Wedding Validation"


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


def test_video_mix_dashboard_quick_mix_returns_output_paths_and_dashboard(tmp_path: Path, monkeypatch) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    captured: dict[str, object] = {}
    expected = {
        "source_dir": str((tmp_path / "source").resolve()),
        "work_dir": str(work_dir.resolve()),
        "project_name": "Quick Mix Validation",
        "pack": "wedding",
        "duration_seconds": 10,
        "episode_duration_min_seconds": 1.2,
        "episode_duration_max_seconds": 2.7,
        "duration_source": "manual",
        "output_count": 2,
        "generated_count": 2,
        "video_count": 1,
        "image_count": 1,
        "quick_mix_warning_count": 0,
        "quick_mix_warnings": [],
        "quick_mix_plan_path": "reports/quick_mix_plan.json",
        "photo_support": True,
        "music_path": str((tmp_path / "music.mp3").resolve()),
        "opening_media_path": str((tmp_path / "opening.jpg").resolve()),
        "closing_media_path": str((tmp_path / "closing.mp4").resolve()),
        "output_paths": ["exports/quick_mix_001.mp4", "exports/quick_mix_002.mp4"],
    }
    def fake_quick_mix_source_materials(*args, **kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr("app.main.quick_mix_source_materials", fake_quick_mix_source_materials)

    response = client.post(
        "/api/video-mix/quick-mix",
        json={
            "source_dir": str(tmp_path / "source"),
            "duration_seconds": 10,
            "output_count": 2,
            "episode_duration_min_seconds": 1.2,
            "episode_duration_max_seconds": 2.7,
            "project_name": "Quick Mix Validation",
            "work_dir": str(work_dir),
            "music_path": str(tmp_path / "music.mp3"),
            "opening_media_path": str(tmp_path / "opening.jpg"),
            "closing_media_path": str(tmp_path / "closing.mp4"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["generated_count"] == 2
    assert payload["photo_support"] is True
    assert payload["duration_source"] == "manual"
    assert payload["episode_duration_min_seconds"] == 1.2
    assert payload["episode_duration_max_seconds"] == 2.7
    assert payload["quick_mix_warning_count"] == 0
    assert payload["quick_mix_warnings"] == []
    assert payload["quick_mix_plan_path"] == "reports/quick_mix_plan.json"
    assert payload["music_path"] == str((tmp_path / "music.mp3").resolve())
    assert payload["output_paths"] == ["exports/quick_mix_001.mp4", "exports/quick_mix_002.mp4"]
    assert payload["dashboard"]["summary"]["candidate_count"] == 1
    assert captured["episode_duration_min_seconds"] == 1.2
    assert captured["episode_duration_max_seconds"] == 2.7


def test_video_mix_dashboard_quick_mix_estimate_accepts_episode_duration_range(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_estimate_quick_mix_capacity(*args, **kwargs):
        captured.update(kwargs)
        return {
            "source_dir": str(tmp_path.resolve()),
            "resolved_source_dir": str(tmp_path.resolve()),
            "duration_seconds": 15,
            "episode_duration_min_seconds": 1.1,
            "episode_duration_max_seconds": 2.4,
            "duration_source": "manual",
            "use_music_duration": False,
            "usable_asset_count": 10,
            "unique_asset_count": 10,
            "episode_group_count": 10,
            "total_segment_candidates": 25,
            "segments_per_output": 8,
            "body_segments_per_output": 7,
            "selected_episode_count": 7,
            "estimated_unique_outputs": 123,
            "opening_enabled": False,
            "closing_enabled": False,
            "music_paths": [],
            "opening_media_paths": [],
            "closing_media_paths": [],
            "episode_groups": [],
        }

    monkeypatch.setattr("app.main.estimate_quick_mix_capacity", fake_estimate_quick_mix_capacity)

    response = client.post(
        "/api/video-mix/quick-mix-estimate",
        json={
            "source_dir": str(tmp_path),
            "duration_seconds": 15,
            "episode_duration_min_seconds": 1.1,
            "episode_duration_max_seconds": 2.4,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["episode_duration_min_seconds"] == 1.1
    assert payload["episode_duration_max_seconds"] == 2.4
    assert captured["episode_duration_min_seconds"] == 1.1
    assert captured["episode_duration_max_seconds"] == 2.4


def test_video_mix_project_material_take_trim_persists(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)

    assign_response = client.post(
        "/api/video-mix/project-materials/assign",
        json={"work_dir": str(work_dir), "asset_id": "asset_1", "episode_id": "episode_001"},
    )
    assert assign_response.status_code == 200
    take = assign_response.json()["dashboard"]["project_materials"]["episodes"][0]["takes"][0]

    response = client.post(
        "/api/video-mix/project-materials/takes/update",
        json={
            "work_dir": str(work_dir),
            "episode_id": "episode_001",
            "take_id": take["take_id"],
            "source_start_ms": 500,
            "source_end_ms": 2200,
        },
    )

    assert response.status_code == 200
    updated_take = response.json()["dashboard"]["project_materials"]["episodes"][0]["takes"][0]
    assert updated_take["source_start_ms"] == 500
    assert updated_take["source_end_ms"] == 2200
    assert updated_take["duration_ms"] == 1700

    state_payload = read_json(work_file(work_dir, "project_materials_state.json"))
    assert state_payload["episodes"][0]["takes"][0]["source_start_ms"] == 500
    assert state_payload["episodes"][0]["takes"][0]["source_end_ms"] == 2200


def test_video_mix_project_material_take_trim_rejects_invalid_range(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)

    assign_response = client.post(
        "/api/video-mix/project-materials/assign",
        json={"work_dir": str(work_dir), "asset_id": "asset_1", "episode_id": "episode_001"},
    )
    take_id = assign_response.json()["dashboard"]["project_materials"]["episodes"][0]["takes"][0]["take_id"]

    response = client.post(
        "/api/video-mix/project-materials/takes/update",
        json={
            "work_dir": str(work_dir),
            "episode_id": "episode_001",
            "take_id": take_id,
            "source_start_ms": 2500,
            "source_end_ms": 1200,
        },
    )

    assert response.status_code == 400
    assert "start < end" in response.json()["detail"]


def test_video_mix_project_material_photo_take_can_save_and_resave_as_simple_take(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    add_photo_mix_asset(tmp_path, work_dir, "photo_1", "photo_1.jpg")

    assign_response = client.post(
        "/api/video-mix/project-materials/assign",
        json={"work_dir": str(work_dir), "asset_id": "photo_1", "episode_id": "episode_001"},
    )
    assert assign_response.status_code == 200
    take_id = assign_response.json()["dashboard"]["project_materials"]["episodes"][0]["takes"][0]["take_id"]

    first_save = client.post(
        "/api/video-mix/project-materials/takes/update",
        json={
            "work_dir": str(work_dir),
            "episode_id": "episode_001",
            "take_id": take_id,
            "take_type": "asset_take",
            "video_asset_id": "photo_1",
            "source_start_ms": 100,
            "source_end_ms": 900,
        },
    )
    assert first_save.status_code == 200

    second_save = client.post(
        "/api/video-mix/project-materials/takes/update",
        json={
            "work_dir": str(work_dir),
            "episode_id": "episode_001",
            "take_id": take_id,
            "take_type": "asset_take",
            "video_asset_id": "photo_1",
            "source_start_ms": 200,
            "source_end_ms": 800,
        },
    )

    assert second_save.status_code == 200
    take = second_save.json()["dashboard"]["project_materials"]["episodes"][0]["takes"][0]
    assert take["take_type"] == "asset_take"
    assert take["asset_id"] == "photo_1"
    assert take["source_start_ms"] == 200
    assert take["source_end_ms"] == 800
    assert take["duration_ms"] == 600
    assert take["media_type"] == "photo"
    assert "video_asset_id" not in take
    assert "photo_asset_ids" not in take
    assert "photo_duration_ms" not in take
    assert "photo_motion_mode" not in take

    timeline_block = second_save.json()["dashboard"]["project_materials"]["timeline"]["rows"][0]["blocks"][0]
    assert timeline_block["take_type"] == "asset_take"
    assert timeline_block["asset_id"] == "photo_1"
    assert timeline_block["duration_ms"] == 600

    state_payload = read_json(work_file(work_dir, "project_materials_state.json"))
    persisted_take = state_payload["episodes"][0]["takes"][0]
    assert persisted_take["take_type"] == "asset_take"
    assert persisted_take["asset_id"] == "photo_1"
    assert persisted_take["source_start_ms"] == 200
    assert persisted_take["source_end_ms"] == 800
    assert "video_asset_id" not in persisted_take
    assert "photo_asset_ids" not in persisted_take
    assert "photo_duration_ms" not in persisted_take
    assert "photo_motion_mode" not in persisted_take


def test_video_mix_project_material_take_reorder_persists_and_updates_timeline(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    add_video_mix_asset(tmp_path, work_dir, "asset_2", "bride_portrait.mp4", duration_ms=6000)

    first_assign = client.post(
        "/api/video-mix/project-materials/assign",
        json={"work_dir": str(work_dir), "asset_id": "asset_1", "episode_id": "episode_001"},
    )
    assert first_assign.status_code == 200
    second_assign = client.post(
        "/api/video-mix/project-materials/assign",
        json={"work_dir": str(work_dir), "asset_id": "asset_2", "episode_id": "episode_001"},
    )
    assert second_assign.status_code == 200

    takes = second_assign.json()["dashboard"]["project_materials"]["episodes"][0]["takes"]
    assert [take["order"] for take in takes] == [1, 2]

    update_second = client.post(
        "/api/video-mix/project-materials/takes/update",
        json={
            "work_dir": str(work_dir),
            "episode_id": "episode_001",
            "take_id": takes[1]["take_id"],
            "source_start_ms": 1000,
            "source_end_ms": 3500,
        },
    )
    assert update_second.status_code == 200

    reorder_response = client.post(
        "/api/video-mix/project-materials/takes/reorder",
        json={
            "work_dir": str(work_dir),
            "episode_id": "episode_001",
            "ordered_take_ids": [takes[1]["take_id"], takes[0]["take_id"]],
        },
    )

    assert reorder_response.status_code == 200
    episode_takes = reorder_response.json()["dashboard"]["project_materials"]["episodes"][0]["takes"]
    assert [take["take_id"] for take in episode_takes] == [takes[1]["take_id"], takes[0]["take_id"]]
    assert [take["order"] for take in episode_takes] == [1, 2]

    timeline_blocks = reorder_response.json()["dashboard"]["project_materials"]["timeline"]["rows"][0]["blocks"]
    assert [block["take_id"] for block in timeline_blocks] == [takes[1]["take_id"], takes[0]["take_id"]]
    assert timeline_blocks[0]["duration_ms"] == 2500
    assert timeline_blocks[1]["duration_ms"] == 4000

    state_payload = read_json(work_file(work_dir, "project_materials_state.json"))
    assert [take["take_id"] for take in state_payload["episodes"][0]["takes"]] == [takes[1]["take_id"], takes[0]["take_id"]]
    assert [take["order"] for take in state_payload["episodes"][0]["takes"]] == [1, 2]


def test_video_mix_project_material_take_can_become_composite_and_persist_order(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    add_photo_mix_asset(tmp_path, work_dir, "photo_1", "photo_1.jpg")
    add_photo_mix_asset(tmp_path, work_dir, "photo_2", "photo_2.jpg")

    assign_response = client.post(
        "/api/video-mix/project-materials/assign",
        json={"work_dir": str(work_dir), "asset_id": "asset_1", "episode_id": "episode_001"},
    )
    take_id = assign_response.json()["dashboard"]["project_materials"]["episodes"][0]["takes"][0]["take_id"]

    response = client.post(
        "/api/video-mix/project-materials/takes/update",
        json={
            "work_dir": str(work_dir),
            "episode_id": "episode_001",
            "take_id": take_id,
            "take_type": "video_photo_composite",
            "video_asset_id": "asset_1",
            "photo_asset_ids": ["photo_2", "photo_1"],
            "photo_duration_ms": 1200,
            "photo_motion_mode": "ken_burns",
        },
    )

    assert response.status_code == 200
    take = response.json()["dashboard"]["project_materials"]["episodes"][0]["takes"][0]
    assert take["take_type"] == "video_photo_composite"
    assert take["asset_id"] == "asset_1"
    assert take["video_asset_id"] == "asset_1"
    assert take["photo_asset_ids"] == ["photo_2", "photo_1"]
    assert take["photo_duration_ms"] == 1200
    assert take["photo_motion_mode"] == "ken_burns"
    assert take["photo_count"] == 2
    assert take["summary"]["photo_count"] == 2
    assert take["summary"]["photo_motion_mode"] == "ken_burns"

    timeline_block = response.json()["dashboard"]["project_materials"]["timeline"]["rows"][0]["blocks"][0]
    assert timeline_block["take_type"] == "video_photo_composite"
    assert timeline_block["asset_id"] == "asset_1"
    assert timeline_block["photo_asset_ids"] == ["photo_2", "photo_1"]

    state_payload = read_json(work_file(work_dir, "project_materials_state.json"))
    persisted_take = state_payload["episodes"][0]["takes"][0]
    assert persisted_take["take_type"] == "video_photo_composite"
    assert persisted_take["video_asset_id"] == "asset_1"
    assert persisted_take["photo_asset_ids"] == ["photo_2", "photo_1"]
    assert persisted_take["photo_duration_ms"] == 1200
    assert persisted_take["photo_motion_mode"] == "ken_burns"


def test_video_mix_project_material_composite_rejects_photo_base_video_asset(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    add_photo_mix_asset(tmp_path, work_dir, "photo_1", "photo_1.jpg")
    add_photo_mix_asset(tmp_path, work_dir, "photo_2", "photo_2.jpg")

    assign_response = client.post(
        "/api/video-mix/project-materials/assign",
        json={"work_dir": str(work_dir), "asset_id": "asset_1", "episode_id": "episode_001"},
    )
    take_id = assign_response.json()["dashboard"]["project_materials"]["episodes"][0]["takes"][0]["take_id"]

    response = client.post(
        "/api/video-mix/project-materials/takes/update",
        json={
            "work_dir": str(work_dir),
            "episode_id": "episode_001",
            "take_id": take_id,
            "take_type": "video_photo_composite",
            "video_asset_id": "photo_1",
            "photo_asset_ids": ["photo_2"],
            "photo_duration_ms": 1200,
            "photo_motion_mode": "static",
        },
    )

    assert response.status_code == 400
    assert "base asset must be a video" in response.json()["detail"]


def test_video_mix_project_material_composite_rejects_video_asset_inside_photo_list(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    add_photo_mix_asset(tmp_path, work_dir, "photo_1", "photo_1.jpg")

    assign_response = client.post(
        "/api/video-mix/project-materials/assign",
        json={"work_dir": str(work_dir), "asset_id": "asset_1", "episode_id": "episode_001"},
    )
    take_id = assign_response.json()["dashboard"]["project_materials"]["episodes"][0]["takes"][0]["take_id"]

    response = client.post(
        "/api/video-mix/project-materials/takes/update",
        json={
            "work_dir": str(work_dir),
            "episode_id": "episode_001",
            "take_id": take_id,
            "take_type": "video_photo_composite",
            "video_asset_id": "asset_1",
            "photo_asset_ids": ["asset_1"],
            "photo_duration_ms": 1200,
            "photo_motion_mode": "static",
        },
    )

    assert response.status_code == 400
    assert "photo list can contain only photo assets" in response.json()["detail"]


def test_video_mix_project_material_take_can_return_from_composite_to_simple(tmp_path: Path) -> None:
    work_dir = create_video_mix_workdir(tmp_path)
    add_photo_mix_asset(tmp_path, work_dir, "photo_1", "photo_1.jpg")

    assign_response = client.post(
        "/api/video-mix/project-materials/assign",
        json={"work_dir": str(work_dir), "asset_id": "asset_1", "episode_id": "episode_001"},
    )
    take_id = assign_response.json()["dashboard"]["project_materials"]["episodes"][0]["takes"][0]["take_id"]

    composite_response = client.post(
        "/api/video-mix/project-materials/takes/update",
        json={
            "work_dir": str(work_dir),
            "episode_id": "episode_001",
            "take_id": take_id,
            "take_type": "video_photo_composite",
            "video_asset_id": "asset_1",
            "photo_asset_ids": ["photo_1"],
            "photo_duration_ms": 900,
            "photo_motion_mode": "static",
        },
    )
    assert composite_response.status_code == 200

    simple_response = client.post(
        "/api/video-mix/project-materials/takes/update",
        json={
            "work_dir": str(work_dir),
            "episode_id": "episode_001",
            "take_id": take_id,
            "take_type": "asset_take",
            "video_asset_id": "asset_1",
            "source_start_ms": 500,
            "source_end_ms": 2500,
        },
    )

    assert simple_response.status_code == 200
    take = simple_response.json()["dashboard"]["project_materials"]["episodes"][0]["takes"][0]
    assert take["take_type"] == "asset_take"
    assert take["asset_id"] == "asset_1"
    assert take["source_start_ms"] == 500
    assert take["source_end_ms"] == 2500
    assert take["duration_ms"] == 2000

    state_payload = read_json(work_file(work_dir, "project_materials_state.json"))
    persisted_take = state_payload["episodes"][0]["takes"][0]
    assert persisted_take["take_type"] == "asset_take"
    assert persisted_take["asset_id"] == "asset_1"
    assert persisted_take["source_start_ms"] == 500
    assert persisted_take["source_end_ms"] == 2500
    assert "photo_asset_ids" not in persisted_take
    assert "photo_duration_ms" not in persisted_take
    assert "photo_motion_mode" not in persisted_take
