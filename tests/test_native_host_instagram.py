from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from native_host import ytdlp_host


@pytest.fixture
def tool_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    yt_dlp = tmp_path / "yt-dlp.exe"
    ffmpeg = tmp_path / "ffmpeg.exe"
    output_dir = tmp_path / "downloads"
    yt_dlp.write_bytes(b"test")
    ffmpeg.write_bytes(b"test")
    return yt_dlp, ffmpeg, output_dir


def test_instagram_download_uses_current_mp4_flow_and_no_playlist(
    tool_paths: tuple[Path, Path, Path],
) -> None:
    yt_dlp, ffmpeg, output_dir = tool_paths

    command, resolved_output = ytdlp_host.build_download_command(
        {
            "ytDlpPath": str(yt_dlp),
            "ffmpegPath": str(ffmpeg),
            "outputDirectory": str(output_dir),
            "url": "https://www.instagram.com/reels/DbOG_7gox2Q/",
            "mode": "video",
            "quality": "best",
            "cookiesBrowser": "none",
            "impersonateBrowser": False,
        }
    )

    assert resolved_output == output_dir
    assert "--ignore-config" in command
    assert "--no-playlist" in command
    assert command[command.index("-f") + 1] == "bv*+ba/b"
    assert command[command.index("--merge-output-format") + 1] == "mp4"
    assert command[command.index("--remux-video") + 1] == "mp4"
    assert command[-2:] == ["--", "https://www.instagram.com/reels/DbOG_7gox2Q/"]


def test_non_instagram_download_keeps_playlist_support(
    tool_paths: tuple[Path, Path, Path],
) -> None:
    yt_dlp, ffmpeg, output_dir = tool_paths

    command, _ = ytdlp_host.build_download_command(
        {
            "ytDlpPath": str(yt_dlp),
            "ffmpegPath": str(ffmpeg),
            "outputDirectory": str(output_dir),
            "url": "https://www.youtube.com/playlist?list=example",
            "mode": "video",
            "quality": "best",
        }
    )

    assert "--no-playlist" not in command


def test_browser_cookie_and_impersonation_options_are_explicit(
    tool_paths: tuple[Path, Path, Path],
) -> None:
    yt_dlp, ffmpeg, output_dir = tool_paths

    command, _ = ytdlp_host.build_download_command(
        {
            "ytDlpPath": str(yt_dlp),
            "ffmpegPath": str(ffmpeg),
            "outputDirectory": str(output_dir),
            "url": "https://www.instagram.com/reel/example/",
            "mode": "video",
            "quality": "best",
            "cookiesBrowser": "chrome",
            "impersonateBrowser": True,
        }
    )

    assert command[command.index("--cookies-from-browser") + 1] == "chrome"
    assert command[command.index("--impersonate") + 1] == "chrome"


def test_unknown_cookie_browser_is_rejected(
    tool_paths: tuple[Path, Path, Path],
) -> None:
    yt_dlp, ffmpeg, output_dir = tool_paths

    with pytest.raises(ValueError, match="Unsupported cookies browser"):
        ytdlp_host.build_download_command(
            {
                "ytDlpPath": str(yt_dlp),
                "ffmpegPath": str(ffmpeg),
                "outputDirectory": str(output_dir),
                "url": "https://www.instagram.com/reel/example/",
                "mode": "video",
                "quality": "best",
                "cookiesBrowser": "unknown-browser",
            }
        )


def test_instagram_analyze_uses_same_browser_access_options(
    tool_paths: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    yt_dlp, _, output_dir = tool_paths
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "title": "Instagram test",
                    "extractor_key": "Instagram",
                    "duration": 9.17,
                    "thumbnail": None,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(ytdlp_host.subprocess, "run", fake_run)

    response = ytdlp_host.handle_analyze(
        {
            "ytDlpPath": str(yt_dlp),
            "outputDirectory": str(output_dir),
            "url": "https://www.instagram.com/reels/DbOG_7gox2Q/",
            "autoUpdateYtDlp": False,
            "cookiesBrowser": "edge",
            "impersonateBrowser": True,
        }
    )

    command = captured["command"]
    assert isinstance(command, list)
    assert "--no-playlist" in command
    assert command[command.index("--cookies-from-browser") + 1] == "edge"
    assert command[command.index("--impersonate") + 1] == "chrome"
    assert response["ok"] is True
    assert response["analysis"]["extractor"] == "Instagram"


def test_auto_update_is_cached_for_one_day(
    tool_paths: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    yt_dlp, _, output_dir = tool_paths
    calls: list[str] = []

    def fake_update(path: Path, channel: str) -> dict[str, str]:
        assert path == yt_dlp
        calls.append(channel)
        return {
            "channel": channel,
            "versionBefore": "2026.01.01",
            "versionAfter": "2026.07.04",
            "message": "updated",
        }

    monkeypatch.setattr(ytdlp_host, "update_yt_dlp", fake_update)
    message = {"autoUpdateYtDlp": True, "updateChannel": "nightly"}

    first = ytdlp_host.maybe_update_yt_dlp(message, yt_dlp, output_dir)
    second = ytdlp_host.maybe_update_yt_dlp(message, yt_dlp, output_dir)

    assert first and first["ok"] is True
    assert second and second["ok"] is True
    assert calls == ["nightly"]
