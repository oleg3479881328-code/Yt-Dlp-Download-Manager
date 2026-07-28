from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    "INSTALL_QUICK_DOWNLOADER.cmd",
    "UPDATE_QUICK_DOWNLOADER.cmd",
    "REGISTER_QUICK_DOWNLOADER.cmd",
    "requirements.txt",
)
TREE_FILES = (
    "chrome_extension",
    "native_host",
)
INSTALLER_FILES = (
    "installer/quick_downloader_updater.py",
)


def extension_version() -> str:
    manifest = json.loads(
        (ROOT / "chrome_extension" / "manifest.json").read_text(encoding="utf-8")
    )
    return str(manifest["version"])


def setup_files() -> list[Path]:
    files = [ROOT / relative for relative in (*ROOT_FILES, *INSTALLER_FILES)]
    for directory in TREE_FILES:
        files.extend(
            path
            for path in (ROOT / directory).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    return sorted(files)


def build_setup_zip(output_path: Path) -> Path:
    version = extension_version()
    package_root = Path(f"QuickDownloader-Setup-v{version}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for source_path in setup_files():
            relative_path = source_path.relative_to(ROOT)
            archive.write(source_path, package_root / relative_path)

    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the compact Windows Quick Downloader setup ZIP."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT.parent
        / f"QuickDownloader-Setup-v{extension_version()}.zip",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_path = build_setup_zip(args.output.resolve())
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
