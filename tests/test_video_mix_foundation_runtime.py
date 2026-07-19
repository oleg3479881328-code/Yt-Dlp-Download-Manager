from __future__ import annotations

from pathlib import Path

from video_mix.foundation_runtime import ProductionRunManager, ProductionRunRequest


class _QueueStub:
    def __init__(self, store) -> None:
        self.store = store
        self.enqueued: list[dict[str, object]] = []

    def enqueue(self, **kwargs):
        self.enqueued.append(kwargs)
        return "run_1"


def test_production_run_start_serializes_slots_dataclass_request(monkeypatch, tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    queue_holder: dict[str, _QueueStub] = {}

    monkeypatch.setattr(
        "video_mix.foundation_runtime.plan_source_materials",
        lambda *args, **kwargs: {"work_dir": str(work_dir)},
    )
    monkeypatch.setattr("video_mix.foundation_runtime.bootstrap_foundation_state", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        "video_mix.foundation_runtime.load_project",
        lambda *_args, **_kwargs: type("ProjectStub", (), {"project_id": "project_1"})(),
    )
    monkeypatch.setattr(
        "video_mix.foundation_runtime.VideoMixFoundationJobQueue",
        lambda store: queue_holder.setdefault("queue", _QueueStub(store)),
    )

    manager = ProductionRunManager()
    monkeypatch.setattr(manager, "_ensure_worker", lambda *_args, **_kwargs: None)

    result = manager.start(
        ProductionRunRequest(
            source_dir=str(source_dir),
            work_dir=str(work_dir),
            project_name="Issue64 smoke",
            count=5,
            duration_seconds=8,
        )
    )

    assert result["run_id"] == "run_1"
    payload = queue_holder["queue"].enqueued[0]["payload"]
    assert payload["request"]["project_name"] == "Issue64 smoke"
    assert payload["request"]["duration_seconds"] == 8


def test_production_run_start_serializes_path_fields_to_strings(monkeypatch, tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    music_path = tmp_path / "music.mp3"
    music_path.write_bytes(b"demo")
    opening_path = tmp_path / "opening.mp4"
    opening_path.write_bytes(b"demo")

    queue_holder: dict[str, _QueueStub] = {}

    monkeypatch.setattr(
        "video_mix.foundation_runtime.plan_source_materials",
        lambda *args, **kwargs: {"work_dir": str(work_dir)},
    )
    monkeypatch.setattr("video_mix.foundation_runtime.bootstrap_foundation_state", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        "video_mix.foundation_runtime.load_project",
        lambda *_args, **_kwargs: type("ProjectStub", (), {"project_id": "project_1"})(),
    )
    monkeypatch.setattr(
        "video_mix.foundation_runtime.VideoMixFoundationJobQueue",
        lambda store: queue_holder.setdefault("queue", _QueueStub(store)),
    )

    manager = ProductionRunManager()
    monkeypatch.setattr(manager, "_ensure_worker", lambda *_args, **_kwargs: None)

    manager.start(
        ProductionRunRequest(
            source_dir=source_dir,  # type: ignore[arg-type]
            work_dir=work_dir,  # type: ignore[arg-type]
            project_name="Issue64 smoke",
            count=5,
            duration_seconds=8,
            music_paths=[music_path],  # type: ignore[list-item]
            opening_media_paths=[opening_path],  # type: ignore[list-item]
        )
    )

    payload = queue_holder["queue"].enqueued[0]["payload"]
    request_payload = payload["request"]
    assert request_payload["source_dir"] == str(source_dir)
    assert request_payload["work_dir"] == str(work_dir)
    assert request_payload["music_paths"] == [str(music_path)]
    assert request_payload["opening_media_paths"] == [str(opening_path)]


def test_execute_job_accepts_json_payload_from_sqlite(monkeypatch, tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    manager = ProductionRunManager()
    captured: dict[str, object] = {}

    monkeypatch.setattr(manager, "_is_cancelled", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        manager,
        "_mark_canceled",
        lambda _store, run_id: captured.setdefault("run_id", run_id),
    )

    manager._execute_job(
        work_dir,
        "run_1",
        '{"request":{"source_dir":"C:\\\\demo\\\\source","project_name":"sqlite-json","count":5,"duration_seconds":8}}',
    )

    assert captured["run_id"] == "run_1"
