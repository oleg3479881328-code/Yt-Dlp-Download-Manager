from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
UPDATER_PATH = ROOT / "installer" / "quick_downloader_updater.py"
SPEC = importlib.util.spec_from_file_location("quick_downloader_updater", UPDATER_PATH)
assert SPEC is not None
assert SPEC.loader is not None
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)


def make_source(root: Path, version: str = "0.2.1") -> Path:
    source = root / "source"
    required_contents = {
        "chrome_extension/manifest.json": json.dumps(
            {"name": "Quick Downloader", "version": version}
        ),
        "native_host/ytdlp_host.py": "print('host')\n",
        "native_host/build_host.ps1": "Write-Output 'build'\n",
        "native_host/register_host.ps1": "Write-Output 'register'\n",
        "requirements.txt": "yt-dlp\n",
        "INSTALL_QUICK_DOWNLOADER.cmd": "@echo install\n",
        "UPDATE_QUICK_DOWNLOADER.cmd": "@echo update\n",
        "REGISTER_QUICK_DOWNLOADER.cmd": "@echo register\n",
        "installer/quick_downloader_updater.py": "# updater\n",
    }
    for relative, content in required_contents.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return source


def test_validate_source_root_reports_missing_required_file(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    (source / "UPDATE_QUICK_DOWNLOADER.cmd").unlink()

    with pytest.raises(updater.UpdateError, match="UPDATE_QUICK_DOWNLOADER.cmd"):
        updater.validate_source_root(source)


def test_install_payload_uses_stable_layout_and_preserves_local_state(
    tmp_path: Path,
) -> None:
    source = make_source(tmp_path, version="0.2.1")
    stable_root = tmp_path / "LocalAppData" / "QuickDownloader"
    old_manifest = stable_root / "native_host" / "com.oleg.ytdlp.json"
    old_manifest.parent.mkdir(parents=True)
    old_manifest.write_text('{"saved": true}\n', encoding="utf-8")
    config = stable_root / "config" / "extension-id.txt"
    config.parent.mkdir()
    config.write_text("abcdefghijklmnopabcdefghijklmnop\n", encoding="utf-8")
    downloads = stable_root / "downloads" / "keep.mp4"
    downloads.parent.mkdir()
    downloads.write_bytes(b"keep")

    metadata = updater.install_payload(source, stable_root)

    assert metadata["version"] == "0.2.1"
    assert (stable_root / "extension" / "manifest.json").is_file()
    assert (stable_root / "UPDATE_QUICK_DOWNLOADER.cmd").is_file()
    assert old_manifest.read_text(encoding="utf-8") == '{"saved": true}\n'
    assert config.read_text(encoding="utf-8").strip() == (
        "abcdefghijklmnopabcdefghijklmnop"
    )
    assert downloads.read_bytes() == b"keep"


def test_second_install_replaces_extension_but_keeps_registration(
    tmp_path: Path,
) -> None:
    source = make_source(tmp_path, version="0.2.1")
    stable_root = tmp_path / "QuickDownloader"
    updater.install_payload(source, stable_root)
    saved_manifest = stable_root / "native_host" / "com.oleg.ytdlp.json"
    saved_manifest.write_text('{"extension": "saved"}\n', encoding="utf-8")
    (stable_root / "extension" / "obsolete.js").write_text(
        "old",
        encoding="utf-8",
    )

    manifest = source / "chrome_extension" / "manifest.json"
    manifest.write_text(
        json.dumps({"name": "Quick Downloader", "version": "0.2.2"}),
        encoding="utf-8",
    )
    updater.install_payload(source, stable_root)

    installed_manifest = json.loads(
        (stable_root / "extension" / "manifest.json").read_text(encoding="utf-8")
    )
    assert installed_manifest["version"] == "0.2.2"
    assert not (stable_root / "extension" / "obsolete.js").exists()
    assert saved_manifest.read_text(encoding="utf-8") == '{"extension": "saved"}\n'


def test_archive_root_detection_rejects_multiple_valid_projects(
    tmp_path: Path,
) -> None:
    extract_root = tmp_path / "extract"
    first = make_source(extract_root / "one")
    second = make_source(extract_root / "two")
    assert first != second

    with pytest.raises(updater.UpdateError, match="exactly one"):
        updater.find_archive_source_root(extract_root)


def test_safe_extract_rejects_parent_path(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    destination = tmp_path / "destination"
    destination.mkdir()
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.txt", "bad")

    with pytest.raises(updater.UpdateError, match="unsafe path"):
        updater._safe_extract(archive_path, destination)


def test_downloaded_archive_is_resolved_and_validated(tmp_path: Path) -> None:
    source = make_source(tmp_path / "package", version="0.2.3")
    archive_path = tmp_path / "quick-downloader.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for path in source.rglob("*"):
            if path.is_file():
                archive.write(
                    path,
                    Path("Yt-Dlp-Download-Manager-master") / path.relative_to(source),
                )

    with updater.resolved_source_root(None, archive_path.as_uri()) as resolved:
        metadata = updater.validate_source_root(resolved)

    assert metadata == {"name": "Quick Downloader", "version": "0.2.3"}


def test_extension_id_is_validated_and_saved(tmp_path: Path) -> None:
    stable_root = tmp_path / "QuickDownloader"

    saved = updater.save_extension_id(
        stable_root,
        "abcdefghijklmnopabcdefghijklmnop",
    )

    assert saved == "abcdefghijklmnopabcdefghijklmnop"
    assert updater.load_saved_extension_id(stable_root) == saved
    with pytest.raises(updater.UpdateError, match="Invalid Chrome extension ID"):
        updater.save_extension_id(stable_root, "not-a-chrome-id")


def test_validate_only_does_not_create_stable_install(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    stable_root = tmp_path / "QuickDownloader"
    args = updater.build_parser().parse_args(
        [
            "--mode",
            "update",
            "--source-root",
            str(source),
            "--stable-root",
            str(stable_root),
            "--skip-build",
            "--no-launch",
            "--validate-only",
        ]
    )

    metadata = updater.execute(args)

    assert metadata == {"name": "Quick Downloader", "version": "0.2.1"}
    assert not stable_root.exists()


def test_cmd_entrypoints_call_the_updater_in_expected_mode() -> None:
    expected_modes = {
        "INSTALL_QUICK_DOWNLOADER.cmd": "install",
        "UPDATE_QUICK_DOWNLOADER.cmd": "update",
        "REGISTER_QUICK_DOWNLOADER.cmd": "register",
    }

    for filename, mode in expected_modes.items():
        source = (ROOT / filename).read_text(encoding="utf-8")
        assert "installer\\quick_downloader_updater.py" in source
        assert f"--mode {mode}" in source

    installer_source = (ROOT / "INSTALL_QUICK_DOWNLOADER.cmd").read_text(
        encoding="utf-8"
    )
    assert '--source-root "%~dp0"' in installer_source
