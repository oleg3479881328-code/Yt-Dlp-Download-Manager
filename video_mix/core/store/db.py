from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import Any


def foundation_db_path(work_dir: Path) -> Path:
    return work_dir / "video_mix.db"


class VideoMixFoundationStore:
    def __init__(self, work_dir: Path) -> None:
        self.work_dir = work_dir.resolve()
        self.db_path = foundation_db_path(self.work_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    @contextmanager
    def connect(self) -> Iterable[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_versions (
                    component TEXT PRIMARY KEY,
                    version INTEGER NOT NULL
                );

                INSERT INTO schema_versions (component, version)
                VALUES ('video_mix_foundation', 1)
                ON CONFLICT(component) DO NOTHING;

                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    work_dir TEXT NOT NULL,
                    source_root TEXT NOT NULL,
                    name TEXT NOT NULL,
                    industry_pack TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS assets (
                    project_id TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    original_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    duration_ms INTEGER,
                    width INTEGER,
                    height INTEGER,
                    fps REAL,
                    orientation TEXT,
                    has_audio INTEGER NOT NULL DEFAULT 0,
                    probe_status TEXT NOT NULL DEFAULT 'pending',
                    quality_score REAL NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (project_id, asset_id),
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );

                CREATE TABLE IF NOT EXISTS proxies (
                    project_id TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    proxy_path TEXT NOT NULL DEFAULT '',
                    source_fingerprint TEXT NOT NULL DEFAULT '',
                    profile_fingerprint TEXT NOT NULL DEFAULT '',
                    original_duration_ms INTEGER NOT NULL DEFAULT 0,
                    proxy_duration_ms INTEGER NOT NULL DEFAULT 0,
                    original_width INTEGER NOT NULL DEFAULT 0,
                    original_height INTEGER NOT NULL DEFAULT 0,
                    proxy_width INTEGER NOT NULL DEFAULT 0,
                    proxy_height INTEGER NOT NULL DEFAULT 0,
                    error TEXT NOT NULL DEFAULT '',
                    has_audio INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (project_id, asset_id),
                    FOREIGN KEY(project_id, asset_id) REFERENCES assets(project_id, asset_id)
                );

                CREATE TABLE IF NOT EXISTS analysis_runs (
                    project_id TEXT NOT NULL,
                    analysis_run_id TEXT PRIMARY KEY,
                    algorithm_name TEXT NOT NULL,
                    algorithm_version TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    settings_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );

                CREATE TABLE IF NOT EXISTS scenes (
                    project_id TEXT NOT NULL,
                    scene_id TEXT PRIMARY KEY,
                    analysis_run_id TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    start_ms INTEGER NOT NULL,
                    end_ms INTEGER NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    keyframe_path TEXT NOT NULL DEFAULT '',
                    score_json TEXT NOT NULL DEFAULT '{}',
                    detector_json TEXT NOT NULL DEFAULT '{}',
                    schema_version TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id),
                    FOREIGN KEY(analysis_run_id) REFERENCES analysis_runs(analysis_run_id),
                    FOREIGN KEY(project_id, asset_id) REFERENCES assets(project_id, asset_id)
                );

                CREATE TABLE IF NOT EXISTS edit_plans (
                    project_id TEXT NOT NULL,
                    plan_id TEXT PRIMARY KEY,
                    analysis_run_id TEXT NOT NULL DEFAULT '',
                    generation_id TEXT NOT NULL,
                    requested_duration_ms INTEGER NOT NULL,
                    actual_duration_ms INTEGER NOT NULL,
                    output_index INTEGER NOT NULL,
                    seed INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    warnings_json TEXT NOT NULL DEFAULT '[]',
                    provenance_key TEXT NOT NULL DEFAULT '',
                    schema_version TEXT NOT NULL,
                    items_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    idempotency_key TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    lease_owner TEXT NOT NULL DEFAULT '',
                    lease_expires_at TEXT NOT NULL DEFAULT '',
                    heartbeat_at TEXT NOT NULL DEFAULT '',
                    progress REAL NOT NULL DEFAULT 0,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    started_at TEXT NOT NULL DEFAULT '',
                    finished_at TEXT NOT NULL DEFAULT '',
                    UNIQUE(project_id, idempotency_key),
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );

                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );

                CREATE TABLE IF NOT EXISTS quality_reports (
                    report_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    findings_json TEXT NOT NULL DEFAULT '{}',
                    schema_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id),
                    FOREIGN KEY(plan_id) REFERENCES edit_plans(plan_id)
                );

                CREATE TABLE IF NOT EXISTS render_provenance (
                    provenance_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    renderer_version TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    output_sha256 TEXT NOT NULL DEFAULT '',
                    source_asset_ids_json TEXT NOT NULL DEFAULT '[]',
                    source_ranges_json TEXT NOT NULL DEFAULT '[]',
                    settings_json TEXT NOT NULL DEFAULT '{}',
                    qc_status TEXT NOT NULL DEFAULT '',
                    review_status TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id),
                    FOREIGN KEY(plan_id) REFERENCES edit_plans(plan_id)
                );
                """
            )

    def _execute(self, query: str, params: tuple[Any, ...]) -> None:
        with self._lock, self.connect() as connection:
            connection.execute(query, params)

    def _upsert_json_row(self, table: str, fields: dict[str, Any], conflict_keys: str) -> None:
        columns = list(fields)
        placeholders = ", ".join("?" for _ in columns)
        assignments = ", ".join(
            f"{column}=excluded.{column}"
            for column in columns
            if column not in {part.strip() for part in conflict_keys.split(",")}
        )
        values = [
            json.dumps(value, ensure_ascii=False)
            if isinstance(value, (dict, list))
            else int(value)
            if isinstance(value, bool)
            else value
            for value in fields.values()
        ]
        query = (
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT({conflict_keys}) DO UPDATE SET {assignments}"
        )
        with self._lock, self.connect() as connection:
            connection.execute(query, tuple(values))

    def upsert_project(self, **fields: Any) -> None:
        self._upsert_json_row("projects", fields, "project_id")

    def upsert_asset(self, **fields: Any) -> None:
        self._upsert_json_row("assets", fields, "project_id, asset_id")

    def upsert_proxy(self, **fields: Any) -> None:
        self._upsert_json_row("proxies", fields, "project_id, asset_id")

    def upsert_analysis_run(self, **fields: Any) -> None:
        self._upsert_json_row("analysis_runs", fields, "analysis_run_id")

    def upsert_scene(self, **fields: Any) -> None:
        self._upsert_json_row("scenes", fields, "scene_id")

    def upsert_edit_plan(self, **fields: Any) -> None:
        self._upsert_json_row("edit_plans", fields, "plan_id")

    def upsert_job(self, **fields: Any) -> None:
        self._upsert_json_row("jobs", fields, "job_id")

    def upsert_quality_report(self, **fields: Any) -> None:
        self._upsert_json_row("quality_reports", fields, "report_id")

    def upsert_render_provenance(self, **fields: Any) -> None:
        self._upsert_json_row("render_provenance", fields, "provenance_id")

    def append_event(
        self,
        *,
        project_id: str,
        event_id: str,
        entity_type: str,
        entity_id: str,
        event_type: str,
        payload_json: dict[str, Any],
    ) -> None:
        self._execute(
            """
            INSERT INTO events (event_id, project_id, entity_type, entity_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (event_id, project_id, entity_type, entity_id, event_type, json.dumps(payload_json, ensure_ascii=False)),
        )

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(query, params).fetchone()
            return dict(row) if row else None

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query, params).fetchall()]
