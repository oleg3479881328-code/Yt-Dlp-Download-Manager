from __future__ import annotations

from pathlib import Path

ALLOWED_MEDIA_EXTENSIONS = {
    ".3gp",
    ".aac",
    ".avi",
    ".flac",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".png",
    ".wav",
    ".webm",
}


def resolve_project_path(project_root: Path, candidate_path: str | Path) -> Path:
    root = project_root.expanduser().resolve()
    candidate = Path(candidate_path).expanduser().resolve()
    if candidate == root or root in candidate.parents:
        return candidate
    raise ValueError(f"Path escapes project root: {candidate}")


def ensure_media_extension_allowed(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.suffix.lower() not in ALLOWED_MEDIA_EXTENSIONS:
        raise ValueError(f"Unsupported media extension: {candidate.suffix}")
    return candidate


def safe_delete_derived(project_root: Path, target_path: str | Path, *, originals: set[Path] | None = None) -> None:
    resolved = resolve_project_path(project_root, target_path)
    if originals and resolved in originals:
        raise ValueError(f"Refusing to delete registered original: {resolved}")
    if resolved.is_dir():
        raise ValueError(f"Refusing to delete directory through safe_delete_derived: {resolved}")
    resolved.unlink(missing_ok=True)
