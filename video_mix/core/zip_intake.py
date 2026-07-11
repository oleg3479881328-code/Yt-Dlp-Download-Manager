from __future__ import annotations

import re
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from .asset_scan import detect_media_type, stable_id
from .media_probe import probe_assets
from .models import Asset, MediaType, Project
from .storage import build_summary, save_assets, save_candidates, save_clips, save_project, save_summary, write_json

IGNORED_ZIP_PARTS = {"__MACOSX"}
IGNORED_ZIP_NAMES = {".DS_Store", "Thumbs.db"}
UNSORTED_BLOCK_LABEL = "Без блока"
WINDOWS_DRIVE_RE = re.compile(r"^[a-zA-Z]:")


@dataclass(slots=True)
class ZipIntakeLimits:
    max_files: int = 500
    max_total_uncompressed_bytes: int = 20 * 1024 * 1024 * 1024
    max_single_file_bytes: int = 5 * 1024 * 1024 * 1024
    max_compression_ratio: int = 100


@dataclass(slots=True)
class ZipIntakeWarning:
    code: str
    message: str
    path: str = ""


@dataclass(slots=True)
class FolderBlock:
    block_id: str
    label: str
    position: int
    source_folder: str
    takes: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ZipIntakeReport:
    zip_filename: str
    extracted_root: str
    blocks: list[FolderBlock]
    warnings: list[ZipIntakeWarning]
    ignored_files: list[str]
    supported_file_count: int
    marker_split_take_count: int
    marker_video_count: int
    total_take_count: int


def _sanitize_name(name: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in name).strip("_") or "video_mix_zip"


def _normalized_member_path(member_name: str) -> PurePosixPath:
    if "\x00" in member_name:
        raise ValueError("ZIP archive contains a null byte in a member path.")
    normalized = member_name.replace("\\", "/").strip()
    if not normalized:
        raise ValueError("ZIP archive contains an empty member path.")
    if WINDOWS_DRIVE_RE.match(normalized):
        raise ValueError(f"ZIP archive contains a Windows drive path: {member_name}")
    if normalized.startswith("//"):
        raise ValueError(f"ZIP archive contains a UNC-style path: {member_name}")
    pure_path = PurePosixPath(normalized)
    if pure_path.is_absolute():
        raise ValueError(f"ZIP archive contains an absolute path: {member_name}")
    if any(part in {"", ".", ".."} for part in pure_path.parts):
        raise ValueError(f"ZIP archive contains an unsafe path: {member_name}")
    return pure_path


def _should_ignore_member(relative_path: PurePosixPath) -> bool:
    if any(part in IGNORED_ZIP_PARTS for part in relative_path.parts):
        return True
    return relative_path.name in IGNORED_ZIP_NAMES


def _validate_zip_archive(archive: zipfile.ZipFile, limits: ZipIntakeLimits) -> dict[str, PurePosixPath]:
    file_count = 0
    total_uncompressed_bytes = 0
    normalized_destinations: dict[str, PurePosixPath] = {}
    for member in archive.infolist():
        relative_path = _normalized_member_path(member.filename)
        if member.is_dir():
            continue
        file_count += 1
        if file_count > limits.max_files:
            raise ValueError(f"ZIP archive exceeds the maximum file count ({limits.max_files}).")
        total_uncompressed_bytes += int(member.file_size or 0)
        if total_uncompressed_bytes > limits.max_total_uncompressed_bytes:
            raise ValueError("ZIP archive exceeds the maximum total uncompressed size.")
        if int(member.file_size or 0) > limits.max_single_file_bytes:
            raise ValueError(f"ZIP member exceeds the maximum single-file size: {relative_path.as_posix()}")
        if member.compress_size == 0:
            compression_ratio = float("inf") if member.file_size else 1.0
        else:
            compression_ratio = member.file_size / member.compress_size
        if compression_ratio > limits.max_compression_ratio:
            raise ValueError(f"ZIP member exceeds the compression ratio limit: {relative_path.as_posix()}")
        normalized_key = relative_path.as_posix().casefold()
        if normalized_key in normalized_destinations:
            raise ValueError(
                "ZIP archive contains duplicate destination paths after normalization: "
                f"{relative_path.as_posix()}"
            )
        normalized_destinations[normalized_key] = relative_path
    bad_member = archive.testzip()
    if bad_member:
        raise ValueError(f"ZIP archive failed CRC validation for member: {bad_member}")
    return normalized_destinations


def extract_zip_to_directory(
    zip_path: Path,
    destination_root: Path,
    *,
    limits: ZipIntakeLimits | None = None,
) -> Path:
    limits = limits or ZipIntakeLimits()
    if destination_root.exists():
        shutil.rmtree(destination_root)
    destination_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as archive:
        _validate_zip_archive(archive, limits)
        for member in archive.infolist():
            if member.is_dir():
                continue
            relative_path = _normalized_member_path(member.filename)
            if _should_ignore_member(relative_path):
                continue
            target_path = (destination_root / relative_path).resolve()
            if destination_root.resolve() not in target_path.parents:
                raise ValueError(f"ZIP member escapes the extraction root: {relative_path.as_posix()}")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source_stream, target_path.open("wb") as target_stream:
                shutil.copyfileobj(source_stream, target_stream)
    return destination_root


def _normalize_extracted_root(extracted_root: Path) -> Path:
    top_level_dirs = sorted(path for path in extracted_root.iterdir() if path.is_dir())
    top_level_files = [path for path in extracted_root.iterdir() if path.is_file()]
    if len(top_level_dirs) == 1 and not top_level_files:
        return top_level_dirs[0]
    return extracted_root


def _sort_block_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
        position = row["position"]
        if position is None:
            return (1, 10**9, row["label"].casefold())
        return (0, int(position), row["label"].casefold())

    return sorted(rows, key=sort_key)


def _parse_block_label(folder_name: str) -> tuple[int | None, str]:
    match = re.match(r"^\s*(\d+)[\s._-]+(.+?)\s*$", folder_name)
    if match:
        return int(match.group(1)), match.group(2).strip() or folder_name.strip()
    return None, folder_name.strip() or folder_name


def _ensure_work_dir_isolated(work_dir: Path) -> None:
    if not work_dir.exists():
        return
    marker_files = [
        work_dir / "reports" / "project.json",
        work_dir / "reports" / "assets.json",
        work_dir / "reports" / "clips.json",
        work_dir / "reports" / "candidates.json",
    ]
    if any(path.exists() for path in marker_files):
        raise ValueError(
            f"Refusing to import ZIP into an existing VIDEO MIX work_dir: {work_dir}. "
            "Choose a new work_dir for this ZIP intake."
        )


def _build_blocks_from_extracted_root(normalized_root: Path) -> tuple[list[dict[str, Any]], list[ZipIntakeWarning], list[str]]:
    blocks: list[dict[str, Any]] = []
    warnings: list[ZipIntakeWarning] = []
    ignored_files: list[str] = []

    top_level_entries = sorted(normalized_root.iterdir(), key=lambda path: path.name.casefold())
    for entry in top_level_entries:
        if entry.is_file():
            if _should_ignore_member(PurePosixPath(entry.name)):
                ignored_files.append(entry.name)
                continue
            warnings.append(
                ZipIntakeWarning(
                    code="root_file_reassigned",
                    message="ZIP root files were placed into the service block 'Без блока'.",
                    path=entry.name,
                )
            )
            break

    numbered_position = 1
    folder_rows: list[dict[str, Any]] = []
    for entry in top_level_entries:
        if entry.is_dir():
            explicit_position, label = _parse_block_label(entry.name)
            folder_rows.append(
                {
                    "entry": entry,
                    "label": label,
                    "position": explicit_position,
                    "source_folder": entry.name,
                }
            )

    for row in _sort_block_rows(folder_rows):
        position = row["position"]
        if position is None:
            position = numbered_position
            numbered_position += 1
        else:
            numbered_position = max(numbered_position, int(position) + 1)
        blocks.append(
            {
                "block_id": stable_id("block", f"{normalized_root}:{row['source_folder']}"),
                "label": row["label"],
                "position": int(position),
                "source_folder": row["source_folder"],
                "root_path": row["entry"],
                "takes": [],
            }
        )

    root_files = [entry for entry in top_level_entries if entry.is_file()]
    if root_files:
        blocks.append(
            {
                "block_id": stable_id("block", f"{normalized_root}:{UNSORTED_BLOCK_LABEL}"),
                "label": UNSORTED_BLOCK_LABEL,
                "position": numbered_position,
                "source_folder": ".",
                "root_path": normalized_root,
                "takes": [],
            }
        )

    return blocks, warnings, ignored_files


def _build_assets_for_blocks(project: Project, blocks: list[dict[str, Any]]) -> tuple[list[Asset], list[ZipIntakeWarning], list[str]]:
    assets: list[Asset] = []
    warnings: list[ZipIntakeWarning] = []
    ignored_files: list[str] = []
    for block in blocks:
        block_root = Path(block["root_path"])
        if block["source_folder"] == ".":
            candidate_files = sorted(path for path in block_root.iterdir() if path.is_file())
        else:
            candidate_files = sorted(path for path in block_root.rglob("*") if path.is_file())
        for file_path in candidate_files:
            relative_path = file_path.relative_to(project.root_path)
            relative_posix = relative_path.as_posix()
            if _should_ignore_member(PurePosixPath(relative_posix)):
                ignored_files.append(relative_posix)
                continue
            media_type = detect_media_type(file_path)
            if media_type is None:
                warnings.append(
                    ZipIntakeWarning(
                        code="unsupported_file_ignored",
                        message="Unsupported file was ignored during ZIP intake.",
                        path=relative_posix,
                    )
                )
                ignored_files.append(relative_posix)
                continue
            nested_relative = ""
            if block["source_folder"] == ".":
                nested_relative = ""
            else:
                nested_relative = file_path.parent.relative_to(block_root).as_posix() if file_path.parent != block_root else ""
            metadata = {
                "block_id": block["block_id"],
                "block_label": block["label"],
                "block_position": int(block["position"]),
                "source_folder": block["source_folder"],
                "relative_path": relative_posix,
            }
            if nested_relative:
                metadata["subfolder"] = nested_relative
            if block["source_folder"] == ".":
                metadata["root_file"] = True
            assets.append(
                Asset(
                    asset_id=stable_id("asset", str(file_path.resolve())),
                    project_id=project.project_id,
                    path=file_path.resolve(),
                    media_type=media_type,
                    metadata=metadata,
                )
            )
    return assets, warnings, ignored_files


def _build_project_materials_state(
    assets: list[Asset],
    *,
    ffmpeg_path: str,
) -> tuple[dict[str, Any], list[FolderBlock], int, int]:
    from video_mix.service import _build_marker_take_candidates, _detect_magenta_marker_ranges

    assets_by_block: dict[str, list[Asset]] = {}
    block_rows: dict[str, dict[str, Any]] = {}
    for asset in assets:
        block_id = str(asset.metadata.get("block_id") or "")
        block_rows[block_id] = {
            "block_id": block_id,
            "label": str(asset.metadata.get("block_label") or asset.path.parent.name),
            "position": int(asset.metadata.get("block_position") or 0),
            "source_folder": str(asset.metadata.get("source_folder") or ""),
        }
        assets_by_block.setdefault(block_id, []).append(asset)

    folder_blocks: list[FolderBlock] = []
    episodes: list[dict[str, Any]] = []
    next_take_sequence = 1
    marker_split_take_count = 0
    marker_video_count = 0

    for block_row in sorted(block_rows.values(), key=lambda item: (int(item["position"]), item["label"].casefold())):
        block_assets = sorted(
            assets_by_block.get(block_row["block_id"], []),
            key=lambda asset: (
                str(asset.metadata.get("subfolder") or "").casefold(),
                asset.path.name.casefold(),
            ),
        )
        folder_block = FolderBlock(
            block_id=str(block_row["block_id"]),
            label=str(block_row["label"]),
            position=int(block_row["position"]),
            source_folder=str(block_row["source_folder"]),
            takes=[],
        )
        episode_takes: list[dict[str, Any]] = []
        for asset in block_assets:
            if asset.media_type == MediaType.VIDEO:
                marker_ranges = _detect_magenta_marker_ranges(asset, ffmpeg_path)
                if marker_ranges:
                    marker_video_count += 1
                    take_candidates = _build_marker_take_candidates(asset, marker_ranges)
                    marker_split_take_count += len(take_candidates)
                else:
                    take_candidates = [
                        {
                            "take_id": f"{asset.asset_id}_take_001",
                            "asset": asset,
                            "start_ms": 0,
                            "end_ms": max(int(asset.duration_ms or 0), 1000),
                        }
                    ]
            else:
                take_candidates = [
                    {
                        "take_id": f"{asset.asset_id}_take_001",
                        "asset": asset,
                        "start_ms": 0,
                        "end_ms": max(int(asset.duration_ms or 0), 1000),
                    }
                ]

            for candidate_index, take_candidate in enumerate(take_candidates, start=1):
                take_id = f"{asset.asset_id}_take_{next_take_sequence:03d}"
                next_take_sequence += 1
                start_ms = max(0, int(take_candidate.get("start_ms") or 0))
                end_ms = max(start_ms + 1, int(take_candidate.get("end_ms") or 0))
                take_metadata = {
                    "take_id": take_id,
                    "asset_id": asset.asset_id,
                    "mode": "assigned",
                    "order": len(episode_takes) + 1,
                    "source_start_ms": start_ms,
                    "source_end_ms": end_ms,
                }
                if asset.metadata.get("subfolder"):
                    take_metadata["subfolder"] = asset.metadata["subfolder"]
                episode_takes.append(take_metadata)
                folder_block.takes.append(
                    {
                        "take_id": take_id,
                        "file_name": asset.path.name,
                        "relative_path": str(asset.metadata.get("relative_path") or asset.path.name),
                        "source_start_ms": start_ms,
                        "source_end_ms": end_ms,
                        "marker_split": len(take_candidates) > 1,
                        "subfolder": str(asset.metadata.get("subfolder") or ""),
                        "segment_index": candidate_index,
                    }
                )

        episodes.append(
            {
                "episode_id": folder_block.block_id,
                "label": folder_block.label,
                "position": folder_block.position,
                "takes": episode_takes,
            }
        )
        folder_blocks.append(folder_block)

    return {
        "version": 2,
        "next_take_sequence": next_take_sequence,
        "episodes": episodes,
    }, folder_blocks, marker_split_take_count, marker_video_count


def _report_to_payload(report: ZipIntakeReport) -> dict[str, Any]:
    return {
        "zip_filename": report.zip_filename,
        "extracted_root": report.extracted_root,
        "blocks": [
            {
                "block_id": block.block_id,
                "label": block.label,
                "position": block.position,
                "source_folder": block.source_folder,
                "takes": block.takes,
            }
            for block in report.blocks
        ],
        "warnings": [
            {"code": warning.code, "message": warning.message, "path": warning.path}
            for warning in report.warnings
        ],
        "ignored_files": report.ignored_files,
        "supported_file_count": report.supported_file_count,
        "marker_split_take_count": report.marker_split_take_count,
        "marker_video_count": report.marker_video_count,
        "total_take_count": report.total_take_count,
        "block_count": len(report.blocks),
        "warning_count": len(report.warnings),
        "ignored_file_count": len(report.ignored_files),
    }


def import_video_mix_zip(
    zip_path: str | Path,
    *,
    project_name: str | None = None,
    work_dir: str | None = None,
    ffprobe_path: str = "ffprobe",
    ffmpeg_path: str = "ffmpeg",
    limits: ZipIntakeLimits | None = None,
) -> dict[str, Any]:
    source_zip = Path(zip_path).expanduser().resolve()
    if not source_zip.exists() or not source_zip.is_file():
        raise FileNotFoundError(f"ZIP file does not exist: {source_zip}")
    if source_zip.suffix.lower() != ".zip":
        raise ValueError(f"Source file is not a ZIP archive: {source_zip}")

    resolved_work_dir = Path(work_dir).expanduser().resolve() if work_dir else (source_zip.parent / f"{source_zip.stem}_video_mix_work").resolve()
    _ensure_work_dir_isolated(resolved_work_dir)

    import_root = resolved_work_dir / "imports"
    extract_dir = import_root / f"{_sanitize_name(source_zip.stem)}_{uuid.uuid4().hex[:8]}"
    extracted_root = extract_zip_to_directory(source_zip, extract_dir, limits=limits)
    normalized_root = _normalize_extracted_root(extracted_root)

    project = Project(
        project_id=stable_id("project", str(normalized_root.resolve())),
        name=project_name or source_zip.stem,
        root_path=normalized_root.resolve(),
        industry_pack="wedding",
    )
    blocks, block_warnings, ignored_files = _build_blocks_from_extracted_root(normalized_root)
    assets, asset_warnings, ignored_asset_files = _build_assets_for_blocks(project, blocks)
    ignored_files = sorted({*ignored_files, *ignored_asset_files})
    if not assets:
        raise ValueError("No supported media files were found in the uploaded ZIP archive.")

    assets = probe_assets(assets, ffprobe_path=ffprobe_path)
    project_materials_state, folder_blocks, marker_split_take_count, marker_video_count = _build_project_materials_state(
        assets,
        ffmpeg_path=ffmpeg_path,
    )

    save_project(resolved_work_dir, project)
    save_assets(resolved_work_dir, assets)
    save_clips(resolved_work_dir, [])
    save_candidates(resolved_work_dir, [])
    save_summary(resolved_work_dir, build_summary(project, assets, [], []))
    write_json(resolved_work_dir / "reports" / "project_materials_state.json", project_materials_state)

    report = ZipIntakeReport(
        zip_filename=source_zip.name,
        extracted_root=str(normalized_root.resolve()),
        blocks=folder_blocks,
        warnings=[*block_warnings, *asset_warnings],
        ignored_files=ignored_files,
        supported_file_count=len(assets),
        marker_split_take_count=marker_split_take_count,
        marker_video_count=marker_video_count,
        total_take_count=sum(len(block.takes) for block in folder_blocks),
    )
    report_payload = _report_to_payload(report)
    write_json(resolved_work_dir / "reports" / "zip_import.json", report_payload)

    return {
        "source_zip": str(source_zip),
        "work_dir": str(resolved_work_dir),
        "project_name": project.name,
        "project_root": str(project.root_path),
        "zip_import_report": report_payload,
        "warnings": report_payload["warnings"],
    }


def stage_upload_file(upload_name: str, content: bytes) -> Path:
    staged_root = Path(tempfile.gettempdir()) / "yt_dlp_video_mix_zip_uploads"
    staged_root.mkdir(parents=True, exist_ok=True)
    safe_name = Path(upload_name).name or "upload.zip"
    staged_path = staged_root / f"{uuid.uuid4().hex}_{safe_name}"
    staged_path.write_bytes(content)
    return staged_path
