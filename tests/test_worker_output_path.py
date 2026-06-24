from __future__ import annotations

from pathlib import Path

from app.storage import Storage
from app.worker import DownloadWorker


class StubYDL:
    def prepare_filename(self, info):
        return f"prepared::{info['id']}.{info['ext']}"


def make_worker(tmp_path: Path) -> DownloadWorker:
    storage = Storage(tmp_path / "data" / "app.db")
    return DownloadWorker(storage, tmp_path)


def test_resolve_final_output_path_prefers_postprocessed_filepath(tmp_path):
    worker = make_worker(tmp_path)
    ydl = StubYDL()
    info = {
        "id": "abc123",
        "ext": "webm",
        "requested_downloads": [
            {
                "filepath": str(tmp_path / "downloads" / "clip.mp3"),
            }
        ],
    }

    resolved = worker._resolve_final_output_path(info, ydl)

    assert resolved.endswith("clip.mp3")


def test_resolve_final_output_path_falls_back_to_prepare_filename(tmp_path):
    worker = make_worker(tmp_path)
    ydl = StubYDL()
    info = {
        "id": "abc123",
        "ext": "mp4",
        "requested_downloads": [],
    }

    resolved = worker._resolve_final_output_path(info, ydl)

    assert resolved == "prepared::abc123.mp4"
