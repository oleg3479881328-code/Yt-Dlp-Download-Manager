from __future__ import annotations

from pathlib import Path

import pytest

from native_host import ytdlp_host

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_context_menu_always_downloads_without_opening_full_page() -> None:
    source = (REPO_ROOT / "chrome_extension" / "background.js").read_text(encoding="utf-8")
    handler = source.split("async function handleContextAction", maxsplit=1)[1].split(
        "chrome.runtime.onInstalled",
        maxsplit=1,
    )[0]

    assert "queueDownload(" in handler
    assert "chrome.tabs.create" not in handler
    assert 'source === "context-menu"' in source


def test_context_menu_url_extraction_rejects_blob_urls() -> None:
    source = (REPO_ROOT / "chrome_extension" / "background.js").read_text(encoding="utf-8")
    extractor = source.split("function extractUrl", maxsplit=1)[1].split("function notify", maxsplit=1)[0]

    assert r"/^https?:\/\//i" in extractor


def test_folder_opens_after_successful_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    media_path = tmp_path / "finished.mp4"
    media_path.write_bytes(b"media")
    log_path = tmp_path / "job.log"
    opened: list[tuple[str | None, Path]] = []

    def fake_open(output_path: str | None, output_dir: Path) -> None:
        opened.append((output_path, output_dir))

    monkeypatch.setattr(ytdlp_host, "open_completed_download_folder", fake_open)

    ytdlp_host.maybe_open_completed_download_folder(
        {"openFolderOnComplete": True},
        str(media_path),
        tmp_path,
        log_path,
    )

    assert opened == [(str(media_path), tmp_path)]
    assert "Output folder opened" in log_path.read_text(encoding="utf-8")


def test_folder_does_not_open_without_explicit_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened = False

    def fake_open(output_path: str | None, output_dir: Path) -> None:
        nonlocal opened
        opened = True

    monkeypatch.setattr(ytdlp_host, "open_completed_download_folder", fake_open)

    ytdlp_host.maybe_open_completed_download_folder({}, None, tmp_path, tmp_path / "job.log")

    assert opened is False
