from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

REPOSITORY_ARCHIVE_URL = (
    "https://github.com/oleg3479881328-code/"
    "Yt-Dlp-Download-Manager/archive/refs/heads/master.zip"
)
STABLE_DIRECTORY_NAME = "QuickDownloader"
EXTENSION_ID_PATTERN = re.compile(r"^[a-p]{32}$")

REQUIRED_SOURCE_PATHS = (
    "chrome_extension/manifest.json",
    "native_host/ytdlp_host.py",
    "native_host/build_host.ps1",
    "native_host/register_host.ps1",
    "requirements.txt",
    "INSTALL_QUICK_DOWNLOADER.cmd",
    "UPDATE_QUICK_DOWNLOADER.cmd",
    "REGISTER_QUICK_DOWNLOADER.cmd",
    "installer/quick_downloader_updater.py",
)

TREE_TARGETS = (
    ("chrome_extension", "extension"),
    ("native_host", "native_host"),
    ("installer", "installer"),
)

FILE_TARGETS = (
    "requirements.txt",
    "INSTALL_QUICK_DOWNLOADER.cmd",
    "UPDATE_QUICK_DOWNLOADER.cmd",
    "REGISTER_QUICK_DOWNLOADER.cmd",
)


class UpdateError(RuntimeError):
    """Raised when a stable install or update cannot be completed safely."""


def default_stable_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / STABLE_DIRECTORY_NAME
    return Path.home() / "AppData" / "Local" / STABLE_DIRECTORY_NAME


def validate_source_root(source_root: Path) -> dict[str, str]:
    source_root = source_root.resolve()
    missing = [
        relative
        for relative in REQUIRED_SOURCE_PATHS
        if not (source_root / Path(relative)).is_file()
    ]
    if missing:
        details = "\n".join(f"- {item}" for item in missing)
        raise UpdateError(f"Downloaded package is incomplete:\n{details}")

    manifest_path = source_root / "chrome_extension" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateError(f"Invalid extension manifest: {exc}") from exc

    version = manifest.get("version")
    name = manifest.get("name")
    if not isinstance(version, str) or not version.strip():
        raise UpdateError("Extension manifest does not contain a valid version.")
    if not isinstance(name, str) or not name.strip():
        raise UpdateError("Extension manifest does not contain a valid name.")

    return {"name": name, "version": version}


def find_archive_source_root(extract_root: Path) -> Path:
    candidates = [
        path.parent.parent
        for path in extract_root.rglob("chrome_extension/manifest.json")
        if path.is_file()
    ]
    unique_candidates = sorted(set(candidates))
    valid_candidates = []
    for candidate in unique_candidates:
        try:
            validate_source_root(candidate)
        except UpdateError:
            continue
        valid_candidates.append(candidate)

    if len(valid_candidates) != 1:
        raise UpdateError(
            "The downloaded archive must contain exactly one valid Quick Downloader source tree."
        )
    return valid_candidates[0]


def _safe_extract(archive_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise UpdateError(
                    f"Archive contains an unsafe path: {member.filename}"
                ) from exc
        archive.extractall(destination)


def _download_archive(url: str, archive_path: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "QuickDownloaderStableUpdater/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            with archive_path.open("wb") as destination:
                shutil.copyfileobj(response, destination)
    except (OSError, urllib.error.URLError) as exc:
        raise UpdateError(f"Could not download the current GitHub version: {exc}") from exc


@contextmanager
def resolved_source_root(
    source_root: Path | None,
    archive_url: str = REPOSITORY_ARCHIVE_URL,
) -> Iterator[Path]:
    if source_root is not None:
        resolved = source_root.resolve()
        validate_source_root(resolved)
        yield resolved
        return

    with tempfile.TemporaryDirectory(prefix="quick-downloader-download-") as temp_dir:
        temp_root = Path(temp_dir)
        archive_path = temp_root / "quick-downloader.zip"
        extract_root = temp_root / "extracted"
        extract_root.mkdir()
        print("Downloading the current Quick Downloader version from GitHub...")
        _download_archive(archive_url, archive_path)
        _safe_extract(archive_path, extract_root)
        resolved = find_archive_source_root(extract_root)
        validate_source_root(resolved)
        yield resolved


def _prepare_payload(source_root: Path, payload_root: Path, stable_root: Path) -> None:
    payload_root.mkdir(parents=True)

    for source_name, target_name in TREE_TARGETS:
        shutil.copytree(source_root / source_name, payload_root / target_name)

    for filename in FILE_TARGETS:
        shutil.copy2(source_root / filename, payload_root / filename)

    existing_native_manifest = (
        stable_root / "native_host" / "com.oleg.ytdlp.json"
    )
    if existing_native_manifest.is_file():
        shutil.copy2(
            existing_native_manifest,
            payload_root / "native_host" / "com.oleg.ytdlp.json",
        )


def install_payload(source_root: Path, stable_root: Path) -> dict[str, str]:
    metadata = validate_source_root(source_root)
    stable_root = stable_root.resolve()
    stable_root.parent.mkdir(parents=True, exist_ok=True)

    transaction_root = stable_root.parent / (
        f".{STABLE_DIRECTORY_NAME}.update-{uuid.uuid4().hex}"
    )
    payload_root = transaction_root / "payload"
    backup_root = transaction_root / "backup"
    installed_targets: list[Path] = []
    backed_up_targets: list[tuple[Path, Path]] = []

    try:
        _prepare_payload(source_root, payload_root, stable_root)
        backup_root.mkdir(parents=True)
        stable_root.mkdir(parents=True, exist_ok=True)

        target_names = [
            *(target_name for _, target_name in TREE_TARGETS),
            *FILE_TARGETS,
        ]
        for target_name in target_names:
            staged_target = payload_root / target_name
            final_target = stable_root / target_name
            backup_target = backup_root / target_name

            if final_target.exists():
                backup_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(final_target), str(backup_target))
                backed_up_targets.append((final_target, backup_target))

            shutil.move(str(staged_target), str(final_target))
            installed_targets.append(final_target)
    except Exception as exc:
        for target in reversed(installed_targets):
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            elif target.exists():
                target.unlink()
        for final_target, backup_target in reversed(backed_up_targets):
            if backup_target.exists():
                final_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(backup_target), str(final_target))
        if isinstance(exc, UpdateError):
            raise
        raise UpdateError(f"Could not replace the stable installation: {exc}") from exc
    finally:
        shutil.rmtree(transaction_root, ignore_errors=True)

    return metadata


def load_saved_extension_id(stable_root: Path) -> str | None:
    path = stable_root / "config" / "extension-id.txt"
    if not path.is_file():
        return None
    value = path.read_text(encoding="utf-8").strip().lower()
    return value if EXTENSION_ID_PATTERN.fullmatch(value) else None


def save_extension_id(stable_root: Path, extension_id: str) -> str:
    normalized = extension_id.strip().lower()
    if not EXTENSION_ID_PATTERN.fullmatch(normalized):
        raise UpdateError(
            "Invalid Chrome extension ID. Expected 32 letters in the a-p range."
        )
    config_dir = stable_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    temp_path = config_dir / "extension-id.txt.tmp"
    final_path = config_dir / "extension-id.txt"
    temp_path.write_text(f"{normalized}\n", encoding="utf-8")
    temp_path.replace(final_path)
    return normalized


def _powershell_executable() -> str:
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if not executable:
        raise UpdateError("Windows PowerShell was not found.")
    return executable


def rebuild_native_host(stable_root: Path) -> None:
    build_script = stable_root / "native_host" / "build_host.ps1"
    if not build_script.is_file():
        raise UpdateError(f"Native host build script was not found: {build_script}")

    host_dir = stable_root / "dist_v2" / "ytdlp_host"
    backup_dir = stable_root / "dist_v2" / "ytdlp_host.before-update"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    if host_dir.exists():
        backup_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(host_dir), str(backup_dir))

    try:
        subprocess.run(
            [
                _powershell_executable(),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(build_script),
            ],
            cwd=stable_root,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        if host_dir.exists():
            shutil.rmtree(host_dir, ignore_errors=True)
        if backup_dir.exists():
            shutil.move(str(backup_dir), str(host_dir))
        raise UpdateError(f"Native host build failed: {exc}") from exc
    else:
        shutil.rmtree(backup_dir, ignore_errors=True)


def register_native_host(stable_root: Path, extension_id: str) -> None:
    register_script = stable_root / "native_host" / "register_host.ps1"
    if not register_script.is_file():
        raise UpdateError(
            f"Native host registration script was not found: {register_script}"
        )
    try:
        subprocess.run(
            [
                _powershell_executable(),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(register_script),
                "-ExtensionId",
                extension_id,
            ],
            cwd=stable_root,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise UpdateError(f"Native host registration failed: {exc}") from exc


def _launch_windows_target(target: str) -> None:
    if os.name != "nt":
        return
    subprocess.Popen(
        ["cmd.exe", "/c", "start", "", target],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def open_install_surfaces(stable_root: Path, include_folder: bool) -> None:
    if include_folder:
        _launch_windows_target(str(stable_root / "extension"))
    _launch_windows_target("chrome://extensions")


def prompt_for_extension_id(stable_root: Path) -> str | None:
    print()
    print("FIRST-TIME CHROME STEP")
    print("1. In chrome://extensions enable Developer mode.")
    print("2. Choose Load unpacked.")
    print(f"3. Select: {stable_root / 'extension'}")
    print("4. Copy the 32-letter extension ID.")
    print()
    if not sys.stdin.isatty():
        return None
    entered = input(
        "Paste the extension ID now, or press Enter and run "
        "REGISTER_QUICK_DOWNLOADER.cmd later: "
    ).strip()
    return entered or None


def execute(args: argparse.Namespace) -> dict[str, str] | None:
    stable_root = args.stable_root.resolve()

    if args.mode == "register":
        extension_id = args.extension_id or load_saved_extension_id(stable_root)
        if not extension_id:
            extension_id = prompt_for_extension_id(stable_root)
        if not extension_id:
            raise UpdateError("Registration was not completed: extension ID is missing.")
        extension_id = save_extension_id(stable_root, extension_id)
        if not args.skip_build:
            register_native_host(stable_root, extension_id)
        print(f"Registered native host for extension: {extension_id}")
        return None

    with resolved_source_root(args.source_root, args.archive_url) as source_root:
        metadata = validate_source_root(source_root)
        print(
            f"Validated {metadata['name']} version {metadata['version']} "
            f"from {source_root}"
        )
        if args.validate_only:
            return metadata

        metadata = install_payload(source_root, stable_root)

    if not args.skip_build:
        rebuild_native_host(stable_root)

    extension_id = args.extension_id or load_saved_extension_id(stable_root)
    first_install_without_id = args.mode == "install" and not extension_id

    if first_install_without_id and not args.no_launch:
        open_install_surfaces(stable_root, include_folder=True)
        extension_id = prompt_for_extension_id(stable_root)

    if extension_id:
        extension_id = save_extension_id(stable_root, extension_id)
        if not args.skip_build:
            register_native_host(stable_root, extension_id)

    if not args.no_launch and not first_install_without_id:
        open_install_surfaces(stable_root, include_folder=False)

    print()
    print(f"Stable installation: {stable_root}")
    print(f"Extension version: {metadata['version']}")
    print(
        "Future updates: "
        f"{stable_root / 'UPDATE_QUICK_DOWNLOADER.cmd'}"
    )
    if extension_id:
        print("Native host registration: ready")
        print("Chrome opened chrome://extensions; press Reload for Quick Downloader.")
    else:
        print(
            "Native host registration: pending. Run "
            f"{stable_root / 'REGISTER_QUICK_DOWNLOADER.cmd'} after loading the extension."
        )
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install or update the stable local Quick Downloader extension."
    )
    parser.add_argument(
        "--mode",
        choices=("install", "update", "register"),
        default="update",
    )
    parser.add_argument(
        "--stable-root",
        type=Path,
        default=default_stable_root(),
    )
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--archive-url", default=REPOSITORY_ARCHIVE_URL)
    parser.add_argument("--extension-id")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        execute(args)
    except UpdateError as exc:
        print()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
