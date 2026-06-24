from __future__ import annotations

from pathlib import Path


class MissingPathError(FileNotFoundError):
    """Raised when a stored output path is missing or no longer exists."""


class UnsafePathError(PermissionError):
    """Raised when a stored output path points outside the configured output root."""


def resolve_output_root(output_directory: str | Path, base_dir: Path) -> Path:
    """Resolve the configured output directory against the project base directory."""

    output_root = Path(output_directory)
    if not output_root.is_absolute():
        output_root = base_dir / output_root
    return output_root.resolve()


def resolve_existing_output_path(raw_path: str | Path | None, output_directory: str | Path, base_dir: Path) -> Path:
    """Return an existing path only when it is inside the configured output directory.

    The dashboard stores file paths produced by yt-dlp. Even though this is a local
    single-user tool, API endpoints that open or return files should not trust a
    database path blindly. A corrupted database row or malformed future integration
    must not be able to make the app open arbitrary local files.
    """

    if not raw_path:
        raise MissingPathError("Path not available")

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = base_dir / candidate

    candidate = candidate.resolve()
    if not candidate.exists():
        raise MissingPathError("Path not found on disk")

    output_root = resolve_output_root(output_directory, base_dir)
    try:
        candidate.relative_to(output_root)
    except ValueError as exc:
        raise UnsafePathError(f"Path outside output directory: {candidate}") from exc

    return candidate
