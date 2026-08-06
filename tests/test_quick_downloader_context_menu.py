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


def test_context_menu_exposes_video_and_mp3_actions() -> None:
    source = (REPO_ROOT / "chrome_extension" / "background.js").read_text(encoding="utf-8")

    assert 'id: "download-video-with-ytdlp"' in source
    assert 'title: "Скачать видео"' in source
    assert 'id: "download-mp3-with-ytdlp"' in source
    assert 'title: "Скачать MP3"' in source
    assert '"download-video-with-ytdlp": "video"' in source
    assert '"download-mp3-with-ytdlp": "audio"' in source
    assert "handleContextAction(info, tab, mode)" in source


def test_native_host_audio_mode_extracts_best_quality_mp3(tmp_path: Path) -> None:
    yt_dlp = tmp_path / "yt-dlp.exe"
    ffmpeg = tmp_path / "ffmpeg.exe"
    yt_dlp.write_bytes(b"")
    ffmpeg.write_bytes(b"")

    command, output_dir = ytdlp_host.build_download_command(
        {
            "ytDlpPath": str(yt_dlp),
            "ffmpegPath": str(ffmpeg),
            "outputDirectory": str(tmp_path / "downloads"),
            "mode": "audio",
            "quality": "best",
            "url": "https://example.com/watch?v=audio",
        }
    )

    assert output_dir == tmp_path / "downloads"
    assert "-x" in command
    assert command[command.index("--audio-format") + 1] == "mp3"
    assert command[command.index("--audio-quality") + 1] == "0"
    assert "--merge-output-format" not in command


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
