from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from video_mix import cli
from video_mix.analysis.foundation import SceneAnalysisResult
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


def test_worker_loop_does_not_complete_cancelled_job(monkeypatch, tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    manager = ProductionRunManager()
    completed: list[str] = []
    canceled: list[str] = []

    class _Queue:
        def __init__(self, _store) -> None:
            self.calls = 0

        def recover_stale_running(self) -> None:
            return None

        def lease_next(self, **_kwargs):
            if self.calls:
                return None
            self.calls += 1
            return {"job_id": "run_1", "payload_json": {}}

        def complete(self, job_id: str) -> None:
            completed.append(job_id)

        def fail(self, *_args, **_kwargs) -> None:
            raise AssertionError("fail() should not be called")

    monkeypatch.setattr("video_mix.foundation_runtime.VideoMixFoundationJobQueue", _Queue)
    monkeypatch.setattr(manager, "_execute_job", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(manager, "_job_row", lambda *_args, **_kwargs: {"status": "canceled", "cancel_requested": True})
    monkeypatch.setattr(manager, "_mark_canceled", lambda _store, run_id: canceled.append(run_id))

    manager._worker_loop(work_dir)

    assert completed == []
    assert canceled == ["run_1"]


def test_wait_for_terminal_status_returns_completed(monkeypatch) -> None:
    manager = ProductionRunManager()
    states = iter(
        [
            {"status": "queued"},
            {"status": "running"},
            {"status": "completed", "job_id": "run_1"},
        ]
    )
    monkeypatch.setattr(manager, "get_status", lambda *_args, **_kwargs: next(states))
    monkeypatch.setattr("video_mix.foundation_runtime.time.sleep", lambda *_args, **_kwargs: None)

    status = manager.wait_for_terminal_status("C:/demo/work", "run_1", poll_interval_seconds=0.0, timeout_seconds=5.0)

    assert status["status"] == "completed"


def test_cli_production_run_waits_for_terminal_status(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli.production_run_manager,
        "start",
        lambda _request: {"run_id": "run_1", "project_id": "project_1", "work_dir": "C:/demo/work"},
    )
    monkeypatch.setattr(
        cli.production_run_manager,
        "wait_for_terminal_status",
        lambda *_args, **_kwargs: {"status": "completed"},
    )
    args = argparse.Namespace(
        source_dir="C:/demo/source",
        work_dir="",
        project_name="Demo",
        count=2,
        duration_seconds=10.0,
        episode_duration_min_seconds=1.5,
        episode_duration_max_seconds=2.0,
        ffmpeg="ffmpeg",
        ffprobe="ffprobe",
        music_paths=[],
        use_music_duration=False,
        opening_media_paths=[],
        closing_media_paths=[],
        use_closing_duration=False,
        pack="wedding",
        poll_interval_seconds=0.0,
        timeout_seconds=5.0,
    )

    cli.run_production_run(args)

    output = capsys.readouterr().out
    assert "final_status=completed" in output


def test_cli_production_run_exits_non_zero_on_failed_status(monkeypatch) -> None:
    monkeypatch.setattr(
        cli.production_run_manager,
        "start",
        lambda _request: {"run_id": "run_1", "project_id": "project_1", "work_dir": "C:/demo/work"},
    )
    monkeypatch.setattr(
        cli.production_run_manager,
        "wait_for_terminal_status",
        lambda *_args, **_kwargs: {"status": "failed"},
    )
    args = argparse.Namespace(
        source_dir="C:/demo/source",
        work_dir="",
        project_name="Demo",
        count=2,
        duration_seconds=10.0,
        episode_duration_min_seconds=1.5,
        episode_duration_max_seconds=2.0,
        ffmpeg="ffmpeg",
        ffprobe="ffprobe",
        music_paths=[],
        use_music_duration=False,
        opening_media_paths=[],
        closing_media_paths=[],
        use_closing_duration=False,
        pack="wedding",
        poll_interval_seconds=0.0,
        timeout_seconds=5.0,
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.run_production_run(args)

    assert exc_info.value.code == 1


@pytest.mark.parametrize(
    ("cancel_on_call", "expected_last_stage"),
    [
        (3, "analysis"),
        (4, "planning"),
        (5, "rendering"),
    ],
)
def test_execute_job_cancels_after_stage_without_publishing(monkeypatch, tmp_path: Path, cancel_on_call: int, expected_last_stage: str) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    manager = ProductionRunManager()
    job_row = {
        "job_id": "run_1",
        "project_id": "project_1",
        "status": "running",
        "cancel_requested": False,
        "payload_json": {"request": {"source_dir": "C:/demo/source", "work_dir": str(work_dir)}},
    }
    canceled: list[str] = []
    heartbeat_stages: list[str] = []
    publishing_called = False
    rendering_called = False
    quality_called = False
    cancel_calls = 0

    class _StoreStub:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def upsert_job(self, **kwargs) -> None:
            job_row.update(kwargs)

    def _is_cancelled(*_args, **_kwargs) -> bool:
        nonlocal cancel_calls
        cancel_calls += 1
        return cancel_calls >= cancel_on_call

    monkeypatch.setattr("video_mix.foundation_runtime.VideoMixFoundationStore", _StoreStub)
    monkeypatch.setattr("video_mix.foundation_runtime.bootstrap_foundation_state", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        "video_mix.foundation_runtime.load_project",
        lambda *_args, **_kwargs: type("ProjectStub", (), {"project_id": "project_1"})(),
    )
    monkeypatch.setattr("video_mix.foundation_runtime.append_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(manager, "_job_row", lambda *_args, **_kwargs: job_row)
    monkeypatch.setattr(manager, "_is_cancelled", _is_cancelled)
    monkeypatch.setattr(manager, "_prepare_analysis_proxies", lambda *_args, **_kwargs: {"summary": {}, "queue": {}})
    monkeypatch.setattr(
        manager,
        "_mark_canceled",
        lambda _store, run_id: (job_row.update({"status": "canceled", "cancel_requested": True}), canceled.append(run_id)),
    )

    def _heartbeat(_store, _run_id, _progress, stage: str) -> None:
        heartbeat_stages.append(stage)
        payload = dict(job_row.get("payload_json") or {})
        payload["stage"] = stage
        job_row["payload_json"] = payload

    monkeypatch.setattr(manager, "_heartbeat", _heartbeat)
    monkeypatch.setattr(
        "video_mix.foundation_runtime.analyze_project_scenes",
        lambda *_args, **_kwargs: SceneAnalysisResult(
            analysis_run_id="analysis_1",
            scene_count=1,
            scene_manifest_path="reports/scene_manifest.json",
            scenes=[{"scene_id": "scene_1"}],
        ),
    )
    monkeypatch.setattr(
        "video_mix.foundation_runtime.build_foundation_edit_plans",
        lambda *_args, **_kwargs: {
            "generation_id": "gen_1",
            "selected_count": 1,
            "candidate_count": 12,
            "plan_path": "reports/edit_plan.json",
            "selected_plans": [{"plan_id": "plan_1", "items": [], "requested_duration_ms": 1000}],
        },
    )

    def _render(*_args, **_kwargs):
        nonlocal rendering_called
        rendering_called = True
        return [{"plan": {"plan_id": "plan_1", "items": [], "requested_duration_ms": 1000}, "output_path": "exports/out.mp4"}]

    def _quality(*_args, **_kwargs):
        nonlocal quality_called
        quality_called = True
        return {"report_id": "qc_1", "status": "qc_passed"}

    def _publish(*_args, **_kwargs):
        nonlocal publishing_called
        publishing_called = True
        return {"manifest_path": "publishing/manifest.json"}

    monkeypatch.setattr("video_mix.foundation_runtime.render_foundation_outputs", _render)
    monkeypatch.setattr("video_mix.foundation_runtime.build_quality_report", _quality)
    monkeypatch.setattr("video_mix.foundation_runtime.build_publishing_package", _publish)

    manager._execute_job(
        work_dir,
        "run_1",
        {"request": {"source_dir": "C:/demo/source", "work_dir": str(work_dir)}},
    )

    assert canceled == ["run_1"]
    assert job_row["status"] == "canceled"
    assert heartbeat_stages[-1] == expected_last_stage
    assert publishing_called is False
    if expected_last_stage == "analysis":
        assert rendering_called is False
        assert quality_called is False
    elif expected_last_stage == "planning":
        assert rendering_called is False
        assert quality_called is False
    elif expected_last_stage == "rendering":
        assert rendering_called is True
        assert quality_called is False
