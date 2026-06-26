from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from video_mix.core.models import CandidateStatus, Clip, MediaType, Orientation, Project, SegmenterName
from video_mix.core.storage import (
    build_asset,
    build_candidate,
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
