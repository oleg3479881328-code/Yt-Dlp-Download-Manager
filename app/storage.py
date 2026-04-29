from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


DEFAULT_SETTINGS = {
    "output_directory": "downloads",
    "default_mode": "video",
    "quality": "best",
    "retry_enabled": True,
    "retry_count": 2,
}


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connect(self) -> Iterable[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT,
                    status TEXT NOT NULL,
                    stage TEXT,
                    progress REAL DEFAULT 0,
                    speed TEXT,
                    eta TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    error TEXT,
                    output_path TEXT,
                    item_total INTEGER DEFAULT 0,
                    item_completed INTEGER DEFAULT 0,
                    item_failed INTEGER DEFAULT 0,
                    current_item_id TEXT,
                    current_item_index INTEGER DEFAULT 0,
                    analysis_json TEXT,
                    mode TEXT,
                    quality TEXT,
                    queue_position INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS playlist_items (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    item_index INTEGER NOT NULL,
                    title TEXT,
                    url TEXT,
                    status TEXT NOT NULL,
                    progress REAL DEFAULT 0,
                    speed TEXT,
                    eta TEXT,
                    error TEXT,
                    output_path TEXT,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    item_id TEXT,
                    timestamp TEXT NOT NULL,
                    message TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            existing = {
                row["key"]: json.loads(row["value"])
                for row in connection.execute("SELECT key, value FROM settings")
            }
            for key, value in DEFAULT_SETTINGS.items():
                if key not in existing:
                    connection.execute(
                        "INSERT INTO settings (key, value) VALUES (?, ?)",
                        (key, json.dumps(value)),
                    )

    def _fetchone_dict(self, connection: sqlite3.Connection, query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        row = connection.execute(query, params).fetchone()
        return dict(row) if row else None

    def get_settings(self) -> dict[str, Any]:
        with self.connect() as connection:
            rows = connection.execute("SELECT key, value FROM settings").fetchall()
            return {row["key"]: json.loads(row["value"]) for row in rows}

    def update_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        with self.lock, self.connect() as connection:
            for key, value in settings.items():
                connection.execute(
                    """
                    INSERT INTO settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, json.dumps(value)),
                )
        return self.get_settings()

    def create_job(self, job: dict[str, Any], items: list[dict[str, Any]]) -> None:
        with self.lock, self.connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, url, type, title, status, stage, progress, speed, eta,
                    created_at, started_at, finished_at, error, output_path,
                    item_total, item_completed, item_failed, current_item_id,
                    current_item_index, analysis_json, mode, quality, queue_position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["id"], job["url"], job["type"], job["title"], job["status"], job["stage"],
                    job["progress"], job["speed"], job["eta"], job["created_at"], job["started_at"],
                    job["finished_at"], job["error"], job["output_path"], job["item_total"],
                    job["item_completed"], job["item_failed"], job["current_item_id"],
                    job["current_item_index"], json.dumps(job["analysis_json"]), job["mode"],
                    job["quality"], job["queue_position"],
                ),
            )
            if items:
                connection.executemany(
                    """
                    INSERT INTO playlist_items (
                        id, job_id, item_index, title, url, status, progress, speed, eta, error, output_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            item["id"], item["job_id"], item["item_index"], item["title"], item["url"],
                            item["status"], item["progress"], item["speed"], item["eta"], item["error"],
                            item["output_path"],
                        )
                        for item in items
                    ],
                )

    def update_job(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        with self.lock, self.connect() as connection:
            assignments = ", ".join(f"{key} = ?" for key in fields)
            connection.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", [*fields.values(), job_id])

    def update_playlist_item(self, item_id: str, **fields: Any) -> None:
        if not fields:
            return
        with self.lock, self.connect() as connection:
            assignments = ", ".join(f"{key} = ?" for key in fields)
            connection.execute(f"UPDATE playlist_items SET {assignments} WHERE id = ?", [*fields.values(), item_id])

    def add_log(self, job_id: str, message: str, timestamp: str, item_id: str | None = None) -> None:
        with self.lock, self.connect() as connection:
            connection.execute(
                "INSERT INTO logs (job_id, item_id, timestamp, message) VALUES (?, ?, ?, ?)",
                (job_id, item_id, timestamp, message),
            )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            job = self._fetchone_dict(connection, "SELECT * FROM jobs WHERE id = ?", (job_id,))
            if not job:
                return None
            job["analysis_json"] = json.loads(job["analysis_json"]) if job["analysis_json"] else None
            job["playlist_items"] = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM playlist_items WHERE job_id = ? ORDER BY item_index ASC",
                    (job_id,),
                )
            ]
            job["logs"] = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM logs WHERE job_id = ? ORDER BY id DESC LIMIT 200",
                    (job_id,),
                )
            ]
            return job

    def list_jobs(self, statuses: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
        with self.connect() as connection:
            if statuses:
                placeholders = ", ".join("?" for _ in statuses)
                rows = connection.execute(
                    f"SELECT * FROM jobs WHERE status IN ({placeholders}) ORDER BY queue_position ASC, created_at ASC",
                    statuses,
                ).fetchall()
            else:
                rows = connection.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
            jobs = []
            for row in rows:
                job = dict(row)
                job["analysis_json"] = json.loads(job["analysis_json"]) if job["analysis_json"] else None
                jobs.append(job)
            return jobs

    def get_dashboard_snapshot(self) -> dict[str, Any]:
        with self.connect() as connection:
            history = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM jobs WHERE status IN ('completed', 'failed') ORDER BY finished_at DESC, created_at DESC LIMIT 50"
                )
            ]
            errors_count = connection.execute(
                "SELECT COUNT(*) AS count FROM jobs WHERE status = 'failed'"
            ).fetchone()["count"]
            return {"history": history, "errors_count": errors_count}

    def get_queue(self) -> list[dict[str, Any]]:
        return self.list_jobs(("queued", "ready", "downloading", "post_processing", "canceled"))

    def get_history(self, status_filter: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as connection:
            if status_filter and status_filter != "all":
                rows = connection.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY finished_at DESC, created_at DESC",
                    (status_filter,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM jobs WHERE status IN ('completed', 'failed') ORDER BY finished_at DESC, created_at DESC"
                ).fetchall()
            return [dict(row) for row in rows]

    def refresh_queue_positions(self) -> None:
        with self.lock, self.connect() as connection:
            queued = connection.execute(
                """
                SELECT id FROM jobs
                WHERE status IN ('queued', 'ready')
                ORDER BY queue_position ASC, created_at ASC
                """
            ).fetchall()
            for index, row in enumerate(queued, start=1):
                connection.execute("UPDATE jobs SET queue_position = ? WHERE id = ?", (index, row["id"]))
