from __future__ import annotations

import json
import math
import random
import re
import shutil
import subprocess
import tempfile
import time
from collections import deque
from hashlib import sha1
from pathlib import Path

from .core.asset_scan import detect_media_type, scan_project_assets, should_skip_project_path, stable_id
from .core.candidate_builder import build_candidates
from .core.duplicate_detection import apply_duplicate_detection
from .core.media_probe import probe_assets
from .core.models import Asset, MediaType, Project
from .core.quick_mix_planner import (
    QUICK_MIX_ASSET_REPEAT_RELAXED,
    QUICK_MIX_SOURCE_GROUP_RELAXED,
    QUICK_MIX_UNIQUE_MATERIAL_EXHAUSTED,
    QuickMixSource,
    build_quick_mix_warning,
    normalize_quick_mix_source_group,
)
from .core.review import write_review_html
from .core.scoring import score_assets, score_clips
from .core.segmenters import FixedIntervalSegmenter, PySceneDetectSegmenter, plan_segments_for_assets
from .core.storage import (
    build_summary,
    save_assets,
    save_candidates,
    save_clips,
    save_project,
    save_summary,
    write_json,
)
from .core.tagging import apply_filename_tags
from .packs.wedding import get_wedding_templates

_SYSTEM_RANDOM = random.SystemRandom()
QUICK_MIX_VARIANT_SEARCH_ATTEMPTS = 192
MAGENTA_MARKER_SAMPLE_FPS = 20
MAGENTA_MARKER_MIN_DURATION_MS = 250
MAGENTA_MARKER_TRIM_PADDING_MS = 120
SUPPORTED_MUSIC_SOURCE_SUFFIXES = {
    ".aac",
    ".aif",
    ".aiff",
    ".flac",
    ".m4a",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
    ".webm",
}
UNSORTED_EPISODE_LABEL = "Без блока"


def _decode_subprocess_stdout(stdout: str | bytes | None) -> str:
    if stdout is None:
        return ""
    if isinstance(stdout, bytes):
        return stdout.decode("utf-8", errors="replace")
    return stdout


def _shuffle_in_place(items: list) -> None:
    _SYSTEM_RANDOM.shuffle(items)


def _random_int_inclusive(max_value: int) -> int:
    if max_value <= 0:
        return 0
    randint = getattr(_SYSTEM_RANDOM, "randint", None)
    if callable(randint):
        return int(randint(0, max_value))
    randrange = getattr(_SYSTEM_RANDOM, "randrange", None)
    if callable(randrange):
        return int(randrange(max_value + 1))
    return 0


def _default_work_dir_for_source_input(source_path: Path) -> Path:
    if source_path.is_file() and source_path.suffix.lower() == ".zip":
        return source_path.parent / f"{source_path.stem}_video_mix_work"
    return source_path / "_video_mix_work"


def _extract_zip_source(zip_path: Path) -> Path:
    from .core.zip_intake import extract_zip_to_directory

    extract_root = Path(tempfile.gettempdir()) / "yt_dlp_video_mix_zip_sources"
    digest = sha1(str(zip_path).encode("utf-8")).hexdigest()[:12]
    extract_dir = extract_root / f"{zip_path.stem}_{digest}"
    return extract_zip_to_directory(zip_path, extract_dir)


def resolve_source_dir(raw_source_dir: str) -> Path:
    source_dir = Path(raw_source_dir).expanduser().resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"Source folder or ZIP does not exist: {source_dir}")
    if source_dir.is_file():
        if source_dir.suffix.lower() != ".zip":
            raise NotADirectoryError(f"Source path is neither a directory nor a ZIP file: {source_dir}")
        return _extract_zip_source(source_dir)
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_dir}")
    return source_dir


def resolve_work_dir(source_dir: Path, work_dir: str | None = None, *, cwd: Path | None = None, source_hint: Path | None = None) -> Path:
    if not work_dir:
        return _default_work_dir_for_source_input(source_hint or source_dir).resolve()
    raw = Path(work_dir).expanduser()
    if raw.is_absolute():
        return raw.resolve()
    base_dir = cwd.resolve() if cwd is not None else Path.cwd().resolve()
    return (base_dir / raw).resolve()


def scan_source_materials(raw_source_dir: str, preview_limit: int = 8) -> dict:
    source_input = Path(raw_source_dir).expanduser().resolve()
    source_dir = resolve_source_dir(raw_source_dir)
    project = Project(
        project_id=stable_id("project", str(source_input)),
        name=source_input.stem if source_input.is_file() else source_dir.name,
        root_path=source_dir,
        industry_pack="wedding",
    )
    assets = scan_project_assets(project)

    total_files = 0
    ignored_directories = 0
    supported_videos = 0
    supported_photos = 0
    preview_files: list[str] = []

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        total_files += 1
        if should_skip_project_path(source_dir, path):
            ignored_directories += 1
            continue
        media_type = detect_media_type(path)
        if media_type == MediaType.VIDEO:
            supported_videos += 1
        elif media_type == MediaType.PHOTO:
            supported_photos += 1
        if media_type is not None and len(preview_files) < preview_limit:
            preview_files.append(str(path.relative_to(source_dir)).replace("\\", "/"))

    if not assets:
        raise ValueError("No supported media files were found in the selected source folder.")

    supported_count = supported_videos + supported_photos
    return {
        "source_dir": str(source_input),
        "resolved_source_dir": str(source_dir),
        "source_kind": "zip" if source_input.is_file() else "directory",
        "total_files": total_files,
        "video_count": supported_videos,
        "image_count": supported_photos,
        "usable_count": supported_count,
        "supported_media_count": supported_count,
        "supported_video_count": supported_videos,
        "supported_photo_count": supported_photos,
        "ignored_or_unsupported_count": max(0, total_files - supported_count),
        "ignored_skipped_dir_count": ignored_directories,
        "preview_files": preview_files,
        "suggested_work_dir": str(resolve_work_dir(source_dir, source_hint=source_input)),
    }


def _build_segmenters(
    *,
    clip_ms: int = 3000,
    max_clips_per_asset: int = 12,
    prefer_pyscenedetect: bool = False,
    scenedetect_path: str = "scenedetect",
):
    fixed = FixedIntervalSegmenter(clip_ms=clip_ms, max_clips_per_asset=max_clips_per_asset)
    if prefer_pyscenedetect:
        return [PySceneDetectSegmenter(scenedetect_path), fixed]
    return [fixed]


def _ensure_ffmpeg_available(ffmpeg_path: str) -> None:
    candidate = Path(ffmpeg_path).expanduser()
    if candidate.is_absolute() and candidate.exists():
        return
    if shutil.which(ffmpeg_path):
        return
    raise FileNotFoundError(f"ffmpeg was not found in PATH: {ffmpeg_path}")


def _validate_quick_mix_inputs(duration_seconds: float, output_count: int) -> tuple[int, int]:
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than 0.")
    if output_count <= 0:
        raise ValueError("output_count must be greater than 0.")
    return max(1000, int(duration_seconds * 1000)), output_count


def _resolve_audio_track_duration_ms(audio_path: Path, ffprobe_path: str) -> int:
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(audio_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, check=True)
        payload = json.loads(_decode_subprocess_stdout(result.stdout))
        audio_streams = [stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"]
        if not audio_streams:
            raise ValueError(f"Music source has no audio track: {audio_path}")
        duration_seconds = audio_streams[0].get("duration") or payload.get("format", {}).get("duration")
        duration_ms = int(float(duration_seconds) * 1000) if duration_seconds is not None else 0
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Could not read music track duration: {audio_path}") from exc
    if duration_ms <= 0:
        raise ValueError(f"Music track has no usable duration: {audio_path}")
    return duration_ms


def _select_music_start_ms(
    music_path: Path | None,
    *,
    target_duration_ms: int,
    ffprobe_path: str,
    use_music_duration: bool,
    duration_cache: dict[Path, int],
) -> int:
    if music_path is None or use_music_duration:
        return 0
    music_duration_ms = duration_cache.get(music_path)
    if music_duration_ms is None:
        music_duration_ms = _resolve_audio_track_duration_ms(music_path, ffprobe_path)
        duration_cache[music_path] = music_duration_ms
    max_start_ms = max(0, music_duration_ms - target_duration_ms)
    return _random_int_inclusive(max_start_ms)


def _normalize_optional_path_list(primary_path: str | None, path_list: list[str] | None) -> list[Path]:
    raw_values: list[str] = []
    if primary_path:
        raw_values.append(primary_path)
    for item in path_list or []:
        if item:
            raw_values.append(item)
    normalized: list[Path] = []
    seen: set[Path] = set()
    for raw_value in raw_values:
        path = Path(raw_value).expanduser().resolve()
        if path in seen:
            continue
        normalized.append(path)
        seen.add(path)
    return normalized


def _resolve_music_paths(primary_path: str | None, path_list: list[str] | None) -> list[Path]:
    resolved_paths = _normalize_optional_path_list(primary_path, path_list)
    for path in resolved_paths:
        if not path.exists():
            raise FileNotFoundError(f"Music track does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"Music track path is not a file: {path}")
        if path.suffix.lower() not in SUPPORTED_MUSIC_SOURCE_SUFFIXES:
            raise ValueError(f"Music source must be a supported audio or video file: {path}")
    return resolved_paths


def _resolve_optional_media_assets(
    primary_path: str | None,
    path_list: list[str] | None,
    *,
    project: Project,
    assets_by_path: dict[Path, Asset],
    ffprobe_path: str,
    label: str,
) -> list[Asset]:
    return [
        _resolve_optional_media_asset(
            str(path),
            project=project,
            assets_by_path=assets_by_path,
            ffprobe_path=ffprobe_path,
            label=label,
        )
        for path in _normalize_optional_path_list(primary_path, path_list)
    ]


def _take_next_variant[T](variants: list[T], pool: list[T]) -> T | None:
    if not variants:
        return None
    if not pool:
        pool.extend(variants)
        _shuffle_in_place(pool)
    return pool.pop()


def _take_identifier(candidate: dict[str, object]) -> str:
    return str(candidate.get("take_id", ""))


def _asset_identifier(candidate: dict[str, object]) -> str:
    asset = candidate.get("asset")
    if isinstance(asset, Asset):
        return asset.asset_id
    return ""


def _source_group_identifier(candidate: dict[str, object]) -> str:
    asset = candidate.get("asset")
    if isinstance(asset, Asset):
        return normalize_quick_mix_source_group(asset.path)
    return ""


def _take_next_balanced_variant(
    variants: list[dict[str, object]],
    pool: list[dict[str, object]],
    take_usage_counts: dict[str, int],
    asset_usage_counts: dict[str, int] | None = None,
    source_group_usage_counts: dict[str, int] | None = None,
    avoid_take_ids: set[str] | None = None,
    avoid_asset_ids: set[str] | None = None,
    avoid_source_groups: set[str] | None = None,
) -> dict[str, object] | None:
    if not variants:
        return None
    effective_asset_usage_counts = asset_usage_counts or {}
    effective_source_group_usage_counts = source_group_usage_counts or {}
    effective_avoid_take_ids = avoid_take_ids or set()
    effective_avoid_asset_ids = avoid_asset_ids or set()
    effective_avoid_source_groups = avoid_source_groups or set()

    if pool:
        pool[:] = [
            candidate
            for candidate in pool
            if (
                _take_identifier(candidate) not in effective_avoid_take_ids
                and _asset_identifier(candidate) not in effective_avoid_asset_ids
                and _source_group_identifier(candidate) not in effective_avoid_source_groups
            )
        ]

    if not pool:
        filtered_variants = [
            candidate
            for candidate in variants
            if (
                _take_identifier(candidate) not in effective_avoid_take_ids
                and _asset_identifier(candidate) not in effective_avoid_asset_ids
                and _source_group_identifier(candidate) not in effective_avoid_source_groups
            )
        ]
        if not filtered_variants:
            return None
        shuffled_variants = list(filtered_variants)
        _shuffle_in_place(shuffled_variants)
        shuffled_variants.sort(
            key=lambda candidate: (
                take_usage_counts.get(_take_identifier(candidate), 0),
                effective_asset_usage_counts.get(_asset_identifier(candidate), 0),
                effective_source_group_usage_counts.get(_source_group_identifier(candidate), 0),
            ),
            reverse=True,
        )
        pool.extend(shuffled_variants)
    return pool.pop()


def _candidate_to_quick_mix_source(candidate: dict[str, object]) -> QuickMixSource:
    asset = candidate.get("asset")
    if not isinstance(asset, Asset):
        raise ValueError("Quick Mix candidate is missing Asset payload.")
    return QuickMixSource(
        source_id=str(candidate.get("take_id") or asset.asset_id),
        base_source_id=asset.asset_id,
        path=asset.path,
        media_type=asset.media_type.value,
        duration_ms=asset.duration_ms,
        source_start_ms=int(candidate.get("start_ms") or 0),
        metadata={"episode_id": str(candidate.get("episode_id") or "")},
    )


def _select_balanced_take_variant(
    variants: list[dict[str, object]],
    pool: list[dict[str, object]],
    take_usage_counts: dict[str, int],
    asset_usage_counts: dict[str, int],
    source_group_usage_counts: dict[str, int],
    *,
    avoid_take_ids: set[str],
    avoid_asset_ids: set[str],
    avoid_source_groups: set[str],
    output_index: int,
    step_index: int,
) -> tuple[dict[str, object] | None, dict | None]:
    selection_stages = (
        (avoid_take_ids, avoid_asset_ids, avoid_source_groups, None),
        (avoid_take_ids, avoid_asset_ids, set(), QUICK_MIX_SOURCE_GROUP_RELAXED),
        (avoid_take_ids, set(), avoid_source_groups, QUICK_MIX_ASSET_REPEAT_RELAXED),
        (set(), set(), set(), QUICK_MIX_UNIQUE_MATERIAL_EXHAUSTED),
    )
    for stage_take_ids, stage_asset_ids, stage_source_groups, warning_code in selection_stages:
        stage_pool = list(pool)
        selected_take = _take_next_balanced_variant(
            variants,
            stage_pool,
            take_usage_counts,
            asset_usage_counts=asset_usage_counts,
            source_group_usage_counts=source_group_usage_counts,
            avoid_take_ids=stage_take_ids,
            avoid_asset_ids=stage_asset_ids,
            avoid_source_groups=stage_source_groups,
        )
        if selected_take is None:
            continue
        pool[:] = stage_pool
        if warning_code is None:
            return selected_take, None
        return selected_take, build_quick_mix_warning(
            warning_code,
            output_index=output_index,
            step_index=step_index + 1,
            source=_candidate_to_quick_mix_source(selected_take),
        )
    return None, None


def _resolve_optional_media_asset(
    raw_path: str | None,
    *,
    project: Project,
    assets_by_path: dict[Path, Asset],
    ffprobe_path: str,
    label: str,
) -> Asset | None:
    if not raw_path:
        return None
    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{label} path is not a file: {path}")

    existing = assets_by_path.get(path)
    if existing is not None:
        return existing

    media_type = detect_media_type(path)
    if media_type is None:
        raise ValueError(f"{label} must be a supported video or photo file: {path}")

    asset = Asset(
        asset_id=stable_id("asset", str(path)),
        project_id=project.project_id,
        path=path,
        media_type=media_type,
    )
    return probe_assets([asset], ffprobe_path=ffprobe_path)[0]


def _is_magenta_marker_sample(rgb: bytes) -> bool:
    if len(rgb) != 3:
        return False
    red, green, blue = rgb
    return red >= 245 and green <= 15 and blue >= 245


def _detect_magenta_marker_ranges(asset: Asset, ffmpeg_path: str) -> list[tuple[int, int]]:
    if asset.media_type != MediaType.VIDEO or not asset.duration_ms:
        return []
    frame_interval_ms = int(1000 / MAGENTA_MARKER_SAMPLE_FPS)
    command = [
        ffmpeg_path,
        "-v",
        "error",
        "-i",
        str(asset.path),
        "-vf",
        f"fps={MAGENTA_MARKER_SAMPLE_FPS},scale=1:1",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, check=True)
    except Exception:  # noqa: BLE001
        return []

    raw = result.stdout or b""
    if not raw:
        return []

    marker_ranges: list[tuple[int, int]] = []
    marker_start_index: int | None = None
    total_frames = len(raw) // 3

    for frame_index in range(total_frames):
        sample = raw[frame_index * 3:(frame_index + 1) * 3]
        is_marker = _is_magenta_marker_sample(sample)
        if is_marker and marker_start_index is None:
            marker_start_index = frame_index
            continue
        if is_marker:
            continue
        if marker_start_index is None:
            continue
        start_ms = marker_start_index * frame_interval_ms
        end_ms = frame_index * frame_interval_ms
        if end_ms - start_ms >= MAGENTA_MARKER_MIN_DURATION_MS:
            marker_ranges.append((start_ms, end_ms))
        marker_start_index = None

    if marker_start_index is not None:
        start_ms = marker_start_index * frame_interval_ms
        end_ms = total_frames * frame_interval_ms
        if end_ms - start_ms >= MAGENTA_MARKER_MIN_DURATION_MS:
            marker_ranges.append((start_ms, end_ms))

    return marker_ranges


def _build_marker_take_candidates(asset: Asset, marker_ranges: list[tuple[int, int]]) -> list[dict[str, int | str | Asset | bool]]:
    if not asset.duration_ms:
        return []
    take_candidates: list[dict[str, int | str | Asset | bool]] = []
    cursor_ms = 0
    take_index = 1

    for marker_start_ms, marker_end_ms in marker_ranges:
        trimmed_end_ms = max(cursor_ms, marker_start_ms - MAGENTA_MARKER_TRIM_PADDING_MS)
        if trimmed_end_ms > cursor_ms:
            take_candidates.append(
                {
                    "asset": asset,
                    "start_ms": cursor_ms,
                    "end_ms": trimmed_end_ms,
                    "max_duration_ms": trimmed_end_ms - cursor_ms,
                    "episode_id": asset.asset_id,
                    "take_index": take_index,
                    "take_id": f"{asset.asset_id}_take_{take_index:03d}",
                    "marker_split": True,
                }
            )
            take_index += 1
        cursor_ms = min(asset.duration_ms, marker_end_ms + MAGENTA_MARKER_TRIM_PADDING_MS)

    if cursor_ms < asset.duration_ms:
        take_candidates.append(
            {
                "asset": asset,
                "start_ms": cursor_ms,
                "end_ms": asset.duration_ms,
                "max_duration_ms": asset.duration_ms - cursor_ms,
                "episode_id": asset.asset_id,
                "take_index": take_index,
                "take_id": f"{asset.asset_id}_take_{take_index:03d}",
                "marker_split": True,
            }
        )

    return [candidate for candidate in take_candidates if int(candidate["max_duration_ms"]) > 0]


def _build_default_take_candidates(asset: Asset) -> list[dict[str, int | str | Asset | bool]]:
    if asset.media_type == MediaType.PHOTO:
        return [
            {
                "asset": asset,
                "start_ms": 0,
                "end_ms": 2000,
                "max_duration_ms": 2000,
                "episode_id": asset.asset_id,
                "take_index": 1,
                "take_id": f"{asset.asset_id}_take_001",
                "marker_split": False,
            }
        ]

    if not asset.duration_ms:
        return [
            {
                "asset": asset,
                "start_ms": 0,
                "end_ms": 2000,
                "max_duration_ms": 2000,
                "episode_id": asset.asset_id,
                "take_index": 1,
                "take_id": f"{asset.asset_id}_take_001",
                "marker_split": False,
            }
        ]

    segment_ms = min(3000, asset.duration_ms)
    stride_ms = max(1000, min(3000, segment_ms))
    max_start = max(0, asset.duration_ms - segment_ms)
    starts = list(range(0, max_start + 1, stride_ms)) or [0]
    if starts[-1] != max_start:
        starts.append(max_start)
    _shuffle_in_place(starts)
    return [
        {
            "asset": asset,
            "start_ms": start_ms,
            "end_ms": min(asset.duration_ms, start_ms + segment_ms),
            "max_duration_ms": min(segment_ms, asset.duration_ms - start_ms),
            "episode_id": asset.asset_id,
            "take_index": index + 1,
            "take_id": f"{asset.asset_id}_take_{index + 1:03d}",
            "marker_split": False,
        }
        for index, start_ms in enumerate(reversed(starts))
    ]


def _normalize_group_label(folder_name: str) -> tuple[int | None, str]:
    match = re.match(r"^\s*(\d+)[\s._-]+(.+?)\s*$", folder_name)
    if match:
        return int(match.group(1)), match.group(2).strip() or folder_name.strip()
    return None, folder_name.strip() or folder_name


def _build_asset_take_candidates(
    asset: Asset,
    *,
    ffmpeg_path: str,
    episode_id: str,
) -> tuple[list[dict[str, int | str | Asset | bool]], list[tuple[int, int]]]:
    marker_ranges = _detect_magenta_marker_ranges(asset, ffmpeg_path)
    if marker_ranges:
        take_candidates = _build_marker_take_candidates(asset, marker_ranges)
    else:
        take_candidates = _build_default_take_candidates(asset)
    normalized_candidates: list[dict[str, int | str | Asset | bool]] = []
    for candidate in take_candidates:
        normalized_candidate = dict(candidate)
        normalized_candidate["episode_id"] = episode_id
        normalized_candidates.append(normalized_candidate)
    return normalized_candidates, marker_ranges


def _group_assets_by_episode_folder(usable_assets: list[Asset], project_root: Path) -> list[dict[str, object]]:
    top_level_dirs = {
        path.name.casefold()
        for path in project_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    }
    if not top_level_dirs:
        return []

    grouped_assets: dict[str, dict[str, object]] = {}
    for asset in usable_assets:
        try:
            relative_path = asset.path.resolve().relative_to(project_root.resolve())
        except ValueError:
            continue
        parts = relative_path.parts
        if len(parts) >= 2 and parts[0].casefold() in top_level_dirs:
            folder_name = parts[0]
            explicit_position, label = _normalize_group_label(folder_name)
            group_key = f"dir::{folder_name.casefold()}"
            group = grouped_assets.setdefault(
                group_key,
                {
                    "episode_id": stable_id("episode", str((project_root / folder_name).resolve())),
                    "episode_label": label,
                    "group_kind": "directory",
                    "position": explicit_position,
                    "source_folder": folder_name,
                    "assets": [],
                },
            )
            group["assets"].append(asset)
            continue

        group = grouped_assets.setdefault(
            "root::__unsorted__",
            {
                "episode_id": stable_id("episode", f"{project_root.resolve()}::{UNSORTED_EPISODE_LABEL}"),
                "episode_label": UNSORTED_EPISODE_LABEL,
                "group_kind": "root_files",
                "position": None,
                "source_folder": ".",
                "assets": [],
            },
        )
        group["assets"].append(asset)

    def sort_key(item: dict[str, object]) -> tuple[int, int, str]:
        position = item.get("position")
        if position is None:
            return (1, 10**9, str(item["episode_label"]).casefold())
        return (0, int(position), str(item["episode_label"]).casefold())

    return sorted(grouped_assets.values(), key=sort_key)


def _build_episode_groups(usable_assets: list[Asset], ffmpeg_path: str, project_root: Path | None = None) -> list[dict[str, object]]:
    grouped_asset_rows = _group_assets_by_episode_folder(usable_assets, project_root.resolve()) if project_root is not None else []
    if not grouped_asset_rows:
        grouped_asset_rows = [
            {
                "episode_id": asset.asset_id,
                "episode_label": asset.path.stem,
                "group_kind": "asset",
                "position": None,
                "source_folder": asset.path.parent.name,
                "assets": [asset],
            }
            for asset in usable_assets
        ]

    episode_groups: list[dict[str, object]] = []
    for grouped_row in grouped_asset_rows:
        takes: list[dict[str, int | str | Asset | bool]] = []
        marker_assets: list[dict[str, object]] = []
        group_assets = sorted(
            grouped_row["assets"],
            key=lambda asset: (
                str(asset.path.parent).casefold(),
                asset.path.name.casefold(),
            ),
        )
        for asset in group_assets:
            take_candidates, marker_ranges = _build_asset_take_candidates(
                asset,
                ffmpeg_path=ffmpeg_path,
                episode_id=str(grouped_row["episode_id"]),
            )
            if marker_ranges:
                marker_assets.append(
                    {
                        "asset_id": asset.asset_id,
                        "source_path": str(asset.path.resolve()),
                        "marker_ranges": marker_ranges,
                    }
                )
            takes.extend(take_candidates)
        if not takes:
            continue
        episode_groups.append(
            {
                "episode_id": str(grouped_row["episode_id"]),
                "episode_label": grouped_row["episode_label"],
                "assets": group_assets,
                "asset": group_assets[0],
                "group_kind": grouped_row["group_kind"],
                "source_folder": grouped_row["source_folder"],
                "takes": takes,
                "take_count": len(takes),
                "marker_ranges": marker_assets[0]["marker_ranges"] if len(group_assets) == 1 and marker_assets else [],
                "marker_assets": marker_assets,
                "marker_split": bool(marker_assets),
            }
        )

    return episode_groups


def _serialize_episode_group(group: dict[str, object]) -> dict[str, object]:
    assets = list(group.get("assets", []))
    marker_assets = list(group.get("marker_assets", []))
    return {
        "episode_id": str(group["episode_id"]),
        "episode_label": group["episode_label"],
        "source_path": str(group["asset"].path.resolve()),
        "source_paths": [str(asset.path.resolve()) for asset in assets],
        "source_folder": str(group.get("source_folder") or ""),
        "group_kind": str(group.get("group_kind") or "asset"),
        "asset_count": len(assets),
        "take_count": int(group["take_count"]),
        "marker_split": bool(group["marker_split"]),
        "marker_ranges": [
            {"start_ms": start_ms, "end_ms": end_ms}
            for start_ms, end_ms in group["marker_ranges"]
        ],
        "marker_assets": [
            {
                "asset_id": str(item.get("asset_id") or ""),
                "source_path": str(item.get("source_path") or ""),
                "marker_ranges": [
                    {"start_ms": start_ms, "end_ms": end_ms}
                    for start_ms, end_ms in item.get("marker_ranges", [])
                ],
            }
            for item in marker_assets
        ],
    }


def _count_episode_combinations(take_counts: list[int], selected_episode_count: int) -> int:
    if selected_episode_count <= 0 or not take_counts:
        return 0
    selected_episode_count = min(selected_episode_count, len(take_counts))
    dp = [0] * (selected_episode_count + 1)
    dp[0] = 1
    for take_count in take_counts:
        for index in range(selected_episode_count, 0, -1):
            dp[index] += dp[index - 1] * take_count
    return math.factorial(selected_episode_count) * dp[selected_episode_count]


def _preferred_segment_ms(asset: Asset, remaining_ms: int) -> int:
    minimum_body_ms = 1500
    target_body_ms = 2000
    if asset.media_type == MediaType.PHOTO:
        if remaining_ms <= minimum_body_ms:
            return remaining_ms
        return min(remaining_ms, target_body_ms)
    if not asset.duration_ms:
        if remaining_ms <= minimum_body_ms:
            return remaining_ms
        return min(remaining_ms, target_body_ms)
    if remaining_ms <= minimum_body_ms:
        return min(remaining_ms, asset.duration_ms)
    return min(remaining_ms, min(target_body_ms, asset.duration_ms))


def _validate_episode_duration_range(
    episode_duration_min_seconds: float,
    episode_duration_max_seconds: float,
) -> tuple[int, int]:
    if episode_duration_min_seconds <= 0:
        raise ValueError("episode_duration_min_seconds must be greater than 0.")
    if episode_duration_max_seconds <= 0:
        raise ValueError("episode_duration_max_seconds must be greater than 0.")
    if episode_duration_max_seconds < episode_duration_min_seconds:
        raise ValueError("episode_duration_max_seconds must be greater than or equal to episode_duration_min_seconds.")
    minimum_ms = max(100, int(round(episode_duration_min_seconds * 1000)))
    maximum_ms = max(minimum_ms, int(round(episode_duration_max_seconds * 1000)))
    return minimum_ms, maximum_ms


def _choose_body_segment_ms(
    asset: Asset,
    remaining_ms: int,
    minimum_body_ms: int,
    maximum_body_ms: int,
) -> int:
    if remaining_ms <= 0:
        return 0
    effective_max_ms = min(remaining_ms, maximum_body_ms)
    if asset.duration_ms:
        effective_max_ms = min(effective_max_ms, asset.duration_ms)
    if effective_max_ms <= 0:
        return 0
    effective_min_ms = min(effective_max_ms, minimum_body_ms)
    if effective_max_ms <= effective_min_ms:
        return effective_max_ms
    return effective_max_ms - _random_int_inclusive(effective_max_ms - effective_min_ms)


def _choose_take_render_window(
    selected_take: dict[str, int | str | Asset | bool],
    asset: Asset,
    preferred_ms: int,
) -> tuple[int, int]:
    if preferred_ms <= 0:
        return 0, 0

    take_start_ms = max(0, int(selected_take["start_ms"]))
    take_end_ms = max(take_start_ms, int(selected_take["end_ms"]))
    max_duration_ms = max(0, int(selected_take["max_duration_ms"]))

    if asset.media_type == MediaType.VIDEO and asset.duration_ms:
        take_end_ms = min(asset.duration_ms, take_end_ms)
        available_duration_ms = max(0, take_end_ms - take_start_ms)
        segment_ms = min(preferred_ms, max_duration_ms, available_duration_ms, asset.duration_ms)
        if segment_ms <= 0:
            return take_start_ms, 0
        max_start_ms = max(take_start_ms, take_end_ms - segment_ms)
        start_ms = take_start_ms + _random_int_inclusive(max_start_ms - take_start_ms)
        return start_ms, segment_ms

    segment_ms = min(preferred_ms, max_duration_ms)
    return 0, segment_ms


def _pinned_segment_ms(asset: Asset, remaining_ms: int, *, use_full_duration: bool = False) -> int:
    if remaining_ms <= 0:
        return 0
    if asset.media_type == MediaType.PHOTO:
        return min(remaining_ms, 1500)
    if not asset.duration_ms:
        return min(remaining_ms, 1500)
    if use_full_duration:
        return min(remaining_ms, asset.duration_ms)
    return min(remaining_ms, min(2000, asset.duration_ms))


def _build_episode_order_queue(
    ordered_episode_ids: list[str],
    used_episode_ids: set[str],
    reserved_episode_ids: set[str],
    episode_usage_counts: dict[str, int],
) -> deque[str]:
    available_episode_ids = [
        episode_id
        for episode_id in ordered_episode_ids
        if episode_id not in used_episode_ids and episode_id not in reserved_episode_ids
    ]
    if not available_episode_ids:
        available_episode_ids = [
            episode_id
            for episode_id in ordered_episode_ids
            if episode_id not in reserved_episode_ids
        ]
    if not available_episode_ids:
        raise ValueError("Could not build any Quick Mix episode order from the source materials.")
    shuffled_episode_ids = list(available_episode_ids)
    _shuffle_in_place(shuffled_episode_ids)
    shuffled_episode_ids.sort(key=lambda episode_id: episode_usage_counts.get(episode_id, 0))
    return deque(shuffled_episode_ids)


def _episode_take_cooldown_size(take_count: int, output_count: int) -> int:
    if take_count <= 1 or output_count <= 1:
        return 0
    return min(take_count - 1, max(1, min(output_count, 6)))


def _episode_asset_cycle_size(asset_count: int) -> int:
    if asset_count <= 1:
        return 0
    return asset_count - 1


def _load_existing_quick_mix_variants(work_dir: Path) -> list[dict[str, object]]:
    report_path = work_dir / "reports" / "quick_mix.json"
    if not report_path.exists():
        return []
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    variants = payload.get("variants", [])
    if not isinstance(variants, list):
        return []
    return [variant for variant in variants if isinstance(variant, dict)]


def _build_quick_mix_variant_signature(
    selected_takes: list[dict[str, object]],
    *,
    selected_music_path: Path | None,
    selected_music_start_ms: int,
    opening_asset: Asset | None,
    closing_asset: Asset | None,
    target_duration_ms: int,
    use_closing_duration: bool = False,
) -> str:
    source_groups = [
        str(take.get("normalized_source_group") or "")
        for take in selected_takes
        if str(take.get("normalized_source_group") or "")
    ]
    signature_payload = {
        "target_duration_ms": target_duration_ms,
        "music_path": str(selected_music_path.resolve()) if selected_music_path is not None else "",
        "music_start_ms": selected_music_start_ms,
        "opening_media_path": str(opening_asset.path.resolve()) if opening_asset is not None else "",
        "closing_media_path": str(closing_asset.path.resolve()) if closing_asset is not None else "",
        "use_closing_duration": use_closing_duration,
        "take_ids": [str(take.get("take_id", "")) for take in selected_takes],
    }
    if source_groups:
        signature_payload["source_groups"] = source_groups
    return json.dumps(signature_payload, ensure_ascii=False, sort_keys=True)


def _build_quick_mix_variant_legacy_signature(
    selected_takes: list[dict[str, object]],
    *,
    selected_music_path: Path | None,
    selected_music_start_ms: int,
    opening_asset: Asset | None,
    closing_asset: Asset | None,
    target_duration_ms: int,
    use_closing_duration: bool = False,
) -> str:
    signature_payload = {
        "target_duration_ms": target_duration_ms,
        "music_path": str(selected_music_path.resolve()) if selected_music_path is not None else "",
        "music_start_ms": selected_music_start_ms,
        "opening_media_path": str(opening_asset.path.resolve()) if opening_asset is not None else "",
        "closing_media_path": str(closing_asset.path.resolve()) if closing_asset is not None else "",
        "use_closing_duration": use_closing_duration,
        "take_ids": [str(take.get("take_id", "")) for take in selected_takes],
    }
    return json.dumps(signature_payload, ensure_ascii=False, sort_keys=True)


def _build_quick_mix_variant_signature_from_manifest(variant: dict[str, object]) -> str:
    selected_takes = variant.get("selected_takes", [])
    if not isinstance(selected_takes, list):
        selected_takes = []
    signature_payload: dict[str, object] = {
        "target_duration_ms": int(variant.get("target_duration_ms") or 0),
        "music_path": str(variant.get("music_path") or ""),
        "music_start_ms": int(variant.get("music_start_ms") or 0),
        "opening_media_path": str(variant.get("opening_media_path") or ""),
        "closing_media_path": str(variant.get("closing_media_path") or ""),
        "use_closing_duration": bool(variant.get("use_closing_duration") or False),
        "take_ids": [
            str(take.get("take_id", ""))
            for take in selected_takes
            if isinstance(take, dict)
        ],
    }
    source_groups = _extract_variant_source_groups(variant)
    if source_groups:
        signature_payload["source_groups"] = source_groups
    return json.dumps(signature_payload, ensure_ascii=False, sort_keys=True)


def _build_quick_mix_variant_legacy_signature_from_manifest(variant: dict[str, object]) -> str:
    selected_takes = variant.get("selected_takes", [])
    if not isinstance(selected_takes, list):
        selected_takes = []
    signature_payload = {
        "target_duration_ms": int(variant.get("target_duration_ms") or 0),
        "music_path": str(variant.get("music_path") or ""),
        "music_start_ms": int(variant.get("music_start_ms") or 0),
        "opening_media_path": str(variant.get("opening_media_path") or ""),
        "closing_media_path": str(variant.get("closing_media_path") or ""),
        "use_closing_duration": bool(variant.get("use_closing_duration") or False),
        "take_ids": [
            str(take.get("take_id", ""))
            for take in selected_takes
            if isinstance(take, dict)
        ],
    }
    return json.dumps(signature_payload, ensure_ascii=False, sort_keys=True)


def _extract_variant_take_ids(variant: dict[str, object]) -> list[str]:
    selected_takes = variant.get("selected_takes", [])
    if not isinstance(selected_takes, list):
        return []
    return [
        str(take.get("take_id", ""))
        for take in selected_takes
        if isinstance(take, dict)
    ]


def _extract_variant_episode_ids(variant: dict[str, object]) -> list[str]:
    selected_takes = variant.get("selected_takes", [])
    if isinstance(selected_takes, list):
        episode_ids = [
            str(take.get("episode_id", ""))
            for take in selected_takes
            if isinstance(take, dict)
        ]
        if any(episode_ids):
            return episode_ids
    episode_order = variant.get("episode_order", [])
    if not isinstance(episode_order, list):
        return []
    return [str(item) for item in episode_order]


def _extract_variant_source_paths(variant: dict[str, object]) -> list[str]:
    selected_takes = variant.get("selected_takes", [])
    if not isinstance(selected_takes, list):
        return []
    return [
        str(take.get("source_path", ""))
        for take in selected_takes
        if isinstance(take, dict)
    ]


def _extract_variant_source_groups(variant: dict[str, object]) -> list[str]:
    selected_takes = variant.get("selected_takes", [])
    if not isinstance(selected_takes, list):
        return []
    groups: list[str] = []
    for take in selected_takes:
        if not isinstance(take, dict):
            continue
        normalized_group = str(take.get("normalized_source_group") or "").strip()
        if normalized_group:
            groups.append(normalized_group)
            continue
        source_path = str(take.get("source_path") or "").strip()
        if source_path:
            groups.append(normalize_quick_mix_source_group(source_path))
    return groups


def _extract_variant_take_window_ids(variant: dict[str, object]) -> list[str]:
    selected_takes = variant.get("selected_takes", [])
    if not isinstance(selected_takes, list):
        return []
    take_window_ids: list[str] = []
    for take in selected_takes:
        if not isinstance(take, dict):
            continue
        take_id = str(take.get("take_id", ""))
        if not take_id:
            continue
        render_start_ms = int(take.get("render_start_ms") or 0)
        render_end_ms = int(take.get("render_end_ms") or 0)
        take_window_ids.append(f"{take_id}@{render_start_ms}:{render_end_ms}")
    return take_window_ids


def _extract_variant_episode_transitions(variant: dict[str, object]) -> list[str]:
    episode_ids = _extract_variant_episode_ids(variant)
    if len(episode_ids) < 2:
        return []
    return [
        f"{left_episode}->{right_episode}"
        for left_episode, right_episode in zip(episode_ids, episode_ids[1:], strict=False)
        if left_episode and right_episode
    ]


def _count_positional_matches(left: list[str], right: list[str]) -> int:
    return sum(1 for left_item, right_item in zip(left, right, strict=False) if left_item and left_item == right_item)


def _count_overlap(left: list[str], right: list[str]) -> int:
    if not left or not right:
        return 0
    right_remaining = list(right)
    matches = 0
    for left_item in left:
        if not left_item:
            continue
        try:
            index = right_remaining.index(left_item)
        except ValueError:
            continue
        matches += 1
        right_remaining.pop(index)
    return matches


def _variant_similarity_tuple(
    candidate_variant: dict[str, object],
    seen_variant: dict[str, object],
) -> tuple[int, int, int, int, int, int, int, int, int, int, int, int, int]:
    candidate_take_window_ids = _extract_variant_take_window_ids(candidate_variant)
    seen_take_window_ids = _extract_variant_take_window_ids(seen_variant)
    candidate_take_ids = _extract_variant_take_ids(candidate_variant)
    seen_take_ids = _extract_variant_take_ids(seen_variant)
    candidate_episode_ids = _extract_variant_episode_ids(candidate_variant)
    seen_episode_ids = _extract_variant_episode_ids(seen_variant)
    candidate_source_paths = _extract_variant_source_paths(candidate_variant)
    seen_source_paths = _extract_variant_source_paths(seen_variant)
    candidate_source_groups = _extract_variant_source_groups(candidate_variant)
    seen_source_groups = _extract_variant_source_groups(seen_variant)
    candidate_transitions = _extract_variant_episode_transitions(candidate_variant)
    seen_transitions = _extract_variant_episode_transitions(seen_variant)
    media_matches = sum(
        1
        for key in ("music_path", "opening_media_path", "closing_media_path", "music_start_ms")
        if str(candidate_variant.get(key) or "") == str(seen_variant.get(key) or "")
    )
    duration_match = int(int(candidate_variant.get("target_duration_ms") or 0) == int(seen_variant.get("target_duration_ms") or 0))
    return (
        _count_positional_matches(candidate_take_window_ids, seen_take_window_ids),
        _count_overlap(candidate_take_window_ids, seen_take_window_ids),
        _count_positional_matches(candidate_take_ids, seen_take_ids),
        _count_overlap(candidate_take_ids, seen_take_ids),
        _count_positional_matches(candidate_source_groups, seen_source_groups),
        _count_overlap(candidate_source_groups, seen_source_groups),
        _count_positional_matches(candidate_source_paths, seen_source_paths),
        _count_overlap(candidate_source_paths, seen_source_paths),
        _count_positional_matches(candidate_transitions, seen_transitions),
        _count_overlap(candidate_transitions, seen_transitions),
        _count_positional_matches(candidate_episode_ids, seen_episode_ids),
        _count_overlap(candidate_episode_ids, seen_episode_ids),
        media_matches + duration_match,
    )


def _build_variant_similarity_rank(candidate_variant: dict[str, object], seen_variants: list[dict[str, object]]) -> tuple[int, ...]:
    if not seen_variants:
        return (0,) * 26
    similarity_vectors = sorted(
        (_variant_similarity_tuple(candidate_variant, seen_variant) for seen_variant in seen_variants),
        reverse=True,
    )
    worst_vector = similarity_vectors[0]
    totals = tuple(sum(vector[index] for vector in similarity_vectors) for index in range(len(worst_vector)))
    return (*worst_vector, *totals)


def _build_quick_mix_plan_report(
    variants: list[dict[str, object]],
    *,
    requested_duration_ms: int,
    requested_output_count: int,
    warnings: list[dict[str, object]],
) -> dict[str, object]:
    outputs: list[dict[str, object]] = []
    for output_index, variant in enumerate(variants, start=1):
        selected_takes = variant.get("selected_takes", [])
        if not isinstance(selected_takes, list):
            selected_takes = []
        variant_warnings = variant.get("warnings", [])
        if not isinstance(variant_warnings, list):
            variant_warnings = []
        outputs.append(
            {
                "output_index": output_index,
                "target_duration_ms": int(variant.get("target_duration_ms") or requested_duration_ms),
                "planned_duration_ms": int(variant.get("generated_duration_ms") or 0),
                "warnings": variant_warnings,
                "segments": [
                    {
                        "output_index": output_index,
                        "step_index": step_index,
                        "source_id": str(take.get("take_id") or ""),
                        "base_source_id": str(take.get("asset_id") or ""),
                        "source_path": str(take.get("source_path") or ""),
                        "source_basename": Path(str(take.get("source_path") or "")).name,
                        "normalized_source_group": str(take.get("normalized_source_group") or ""),
                        "media_type": str(take.get("media_type") or ""),
                        "source_start_ms": int(take.get("render_start_ms") or 0),
                        "source_end_ms": int(take.get("render_end_ms") or 0),
                        "relative_source_start_ms": max(
                            0,
                            int(take.get("render_start_ms") or 0) - int(take.get("source_start_ms") or 0),
                        ),
                        "duration_ms": max(
                            0,
                            int(take.get("render_end_ms") or 0) - int(take.get("render_start_ms") or 0),
                        ),
                        "warnings": [],
                    }
                    for step_index, take in enumerate(
                        [take for take in selected_takes if isinstance(take, dict)],
                        start=1,
                    )
                ],
            }
        )
    return {
        "target_duration_ms": requested_duration_ms,
        "output_count": requested_output_count,
        "warning_count": len(warnings),
        "warnings": warnings,
        "outputs": outputs,
    }


def _build_video_segment_command(
    asset: Asset,
    output_path: Path,
    *,
    start_ms: int,
    duration_ms: int,
    ffmpeg_path: str,
) -> list[str]:
    start_seconds = max(0, start_ms) / 1000
    duration_seconds = max(0, duration_ms) / 1000
    return [
        ffmpeg_path,
        "-y",
        "-i",
        str(asset.path),
        "-vf",
        (
            f"trim=start={start_seconds:.3f}:duration={duration_seconds:.3f},"
            "setpts=PTS-STARTPTS,"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "fps=30"
        ),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]


def _build_photo_segment_command(
    asset: Asset,
    output_path: Path,
    *,
    duration_ms: int,
    ffmpeg_path: str,
) -> list[str]:
    return [
        ffmpeg_path,
        "-y",
        "-loop",
        "1",
        "-i",
        str(asset.path),
        "-t",
        f"{duration_ms / 1000:.3f}",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]


def _render_quick_mix_segment(
    asset: Asset,
    output_path: Path,
    *,
    start_ms: int,
    duration_ms: int,
    ffmpeg_path: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if asset.media_type == MediaType.PHOTO:
        command = _build_photo_segment_command(asset, output_path, duration_ms=duration_ms, ffmpeg_path=ffmpeg_path)
    else:
        command = _build_video_segment_command(
            asset,
            output_path,
            start_ms=start_ms,
            duration_ms=duration_ms,
            ffmpeg_path=ffmpeg_path,
        )
    subprocess.run(command, check=True)


def _build_quick_mix_concat_command(concat_path: Path, output_path: Path, ffmpeg_path: str) -> list[str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return [
        ffmpeg_path,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def _mux_quick_mix_audio(
    video_path: Path,
    output_path: Path,
    music_path: Path,
    ffmpeg_path: str,
    *,
    music_start_ms: int = 0,
) -> None:
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(video_path),
    ]
    if music_start_ms > 0:
        command.extend(["-ss", f"{music_start_ms / 1000:.3f}"])
    command.extend(
        [
            "-i",
            str(music_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-af",
            "apad",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    subprocess.run(command, check=True)


def _render_quick_mix_output(
    segment_paths: list[Path],
    output_path: Path,
    ffmpeg_path: str,
    *,
    music_path: Path | None = None,
    music_start_ms: int = 0,
) -> None:
    concat_dir = output_path.parent.parent / "quick_mix_concat"
    concat_dir.mkdir(parents=True, exist_ok=True)
    concat_path = concat_dir / f"{output_path.stem}.txt"
    concat_path.write_text(
        "".join(f"file '{segment_path.as_posix()}'\n" for segment_path in segment_paths),
        encoding="utf-8",
    )
    visual_output_path = output_path if music_path is None else concat_dir / f"{output_path.stem}__video_only.mp4"
    subprocess.run(_build_quick_mix_concat_command(concat_path, visual_output_path, ffmpeg_path), check=True)
    if music_path is not None:
        _mux_quick_mix_audio(
            visual_output_path,
            output_path,
            music_path,
            ffmpeg_path,
            music_start_ms=music_start_ms,
        )


def _prepare_quick_mix_workdir(
    work_dir: Path,
    *,
    project: Project,
    assets: list[Asset],
    output_paths: list[Path],
    duration_seconds: float,
    output_count: int,
    episode_duration_min_seconds: float = 1.5,
    episode_duration_max_seconds: float = 2.0,
    generation_elapsed_ms: int = 0,
    music_path: Path | None = None,
    music_paths: list[Path] | None = None,
    use_music_duration: bool = False,
    opening_media_path: Path | None = None,
    opening_media_paths: list[Path] | None = None,
    closing_media_path: Path | None = None,
    closing_media_paths: list[Path] | None = None,
    use_closing_duration: bool = False,
    variants: list[dict[str, object]] | None = None,
    episode_groups: list[dict[str, object]] | None = None,
    quick_mix_warning_count: int = 0,
    quick_mix_warnings: list[dict[str, object]] | None = None,
    quick_mix_plan_path: str = "",
) -> None:
    save_project(work_dir, project)
    save_assets(work_dir, assets)
    save_clips(work_dir, [])
    save_candidates(work_dir, [])
    save_summary(work_dir, build_summary(project, assets, [], []))
    write_json(
        work_dir / "reports" / "quick_mix.json",
        {
            "source_dir": str(project.root_path),
            "work_dir": str(work_dir),
            "duration_seconds": duration_seconds,
            "output_count": output_count,
            "episode_duration_min_seconds": episode_duration_min_seconds,
            "episode_duration_max_seconds": episode_duration_max_seconds,
            "generated_count": len(output_paths),
            "generation_elapsed_ms": generation_elapsed_ms,
            "music_path": str(music_path) if music_path else "",
            "music_paths": [str(path) for path in (music_paths or [])],
            "use_music_duration": use_music_duration,
            "duration_source": "music" if use_music_duration and music_path else "manual",
            "opening_media_path": str(opening_media_path) if opening_media_path else "",
            "opening_media_paths": [str(path) for path in (opening_media_paths or [])],
            "closing_media_path": str(closing_media_path) if closing_media_path else "",
            "closing_media_paths": [str(path) for path in (closing_media_paths or [])],
            "use_closing_duration": use_closing_duration,
            "episode_groups": episode_groups or [],
            "variants": variants or [],
            "quick_mix_warning_count": quick_mix_warning_count,
            "quick_mix_warnings": quick_mix_warnings or [],
            "quick_mix_plan_path": quick_mix_plan_path,
            "output_paths": [str(path.relative_to(work_dir)).replace("\\", "/") for path in output_paths],
        },
    )


def quick_mix_source_materials(
    raw_source_dir: str,
    *,
    duration_seconds: float,
    output_count: int,
    episode_duration_min_seconds: float = 1.5,
    episode_duration_max_seconds: float = 2.0,
    project_name: str | None = None,
    pack: str = "wedding",
    work_dir: str | None = None,
    ffmpeg_path: str = "ffmpeg",
    ffprobe_path: str = "ffprobe",
    music_path: str | None = None,
    music_paths: list[str] | None = None,
    use_music_duration: bool = False,
    opening_media_path: str | None = None,
    opening_media_paths: list[str] | None = None,
    closing_media_path: str | None = None,
    closing_media_paths: list[str] | None = None,
    use_closing_duration: bool = False,
) -> dict:
    generation_started_at = time.perf_counter()
    fallback_duration_ms, normalized_output_count = _validate_quick_mix_inputs(duration_seconds, output_count)
    minimum_body_ms, maximum_body_ms = _validate_episode_duration_range(
        episode_duration_min_seconds,
        episode_duration_max_seconds,
    )
    _ensure_ffmpeg_available(ffmpeg_path)

    source_dir = resolve_source_dir(raw_source_dir)
    source_input = Path(raw_source_dir).expanduser().resolve()
    project = Project(stable_id("project", str(source_input)), project_name or source_input.stem, source_dir, pack)
    resolved_work_dir = resolve_work_dir(source_dir, work_dir, source_hint=source_input)

    assets = score_assets(probe_assets(scan_project_assets(project), ffprobe_path=ffprobe_path))
    if not assets:
        raise ValueError("No supported media files were found in the selected source folder.")

    usable_assets = [asset for asset in assets if asset.media_type in {MediaType.VIDEO, MediaType.PHOTO}]
    if not usable_assets:
        raise ValueError("No usable video or photo files were found in the selected source folder.")

    assets_by_path = {asset.path.resolve(): asset for asset in assets}
    opening_assets = _resolve_optional_media_assets(
        opening_media_path,
        opening_media_paths,
        project=project,
        assets_by_path=assets_by_path,
        ffprobe_path=ffprobe_path,
        label="Opening media",
    )
    closing_assets = _resolve_optional_media_assets(
        closing_media_path,
        closing_media_paths,
        project=project,
        assets_by_path=assets_by_path,
        ffprobe_path=ffprobe_path,
        label="Closing media",
    )
    resolved_music_paths = _resolve_music_paths(music_path, music_paths)

    exports_dir = resolved_work_dir / "exports"
    segments_dir = resolved_work_dir / "quick_mix_segments"
    exports_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)

    episode_groups = _build_episode_groups(usable_assets, ffmpeg_path, source_dir)
    if not episode_groups:
        raise ValueError("No usable Quick Mix episode groups could be built from the selected source folder.")
    ordered_episode_ids = [str(group["episode_id"]) for group in episode_groups]
    episode_lookup = {str(group["episode_id"]): group for group in episode_groups}
    episode_take_pools: dict[str, list[dict[str, int | str | Asset | bool]]] = {
        episode_id: [] for episode_id in ordered_episode_ids
    }
    total_unique_asset_ids = {
        asset.asset_id
        for group in episode_groups
        for asset in list(group.get("assets", []))
    }
    episode_take_cooldowns = {
        episode_id: _episode_take_cooldown_size(int(group["take_count"]), normalized_output_count)
        for episode_id, group in episode_lookup.items()
    }
    episode_asset_cycles = {
        episode_id: _episode_asset_cycle_size(len(list(group.get("assets", []))))
        for episode_id, group in episode_lookup.items()
    }
    episode_usage_counts: dict[str, int] = {}
    take_usage_counts: dict[str, int] = {}
    asset_usage_counts: dict[str, int] = {}
    source_group_usage_counts: dict[str, int] = {}
    recent_take_ids_by_episode: dict[str, deque[str]] = {
        episode_id: deque(maxlen=max(1, cooldown_size))
        for episode_id, cooldown_size in episode_take_cooldowns.items()
        if cooldown_size > 0
    }
    exhausted_asset_ids_by_episode: dict[str, deque[str]] = {
        episode_id: deque(maxlen=max(1, cycle_size))
        for episode_id, cycle_size in episode_asset_cycles.items()
        if cycle_size > 0
    }
    globally_exhausted_asset_ids = deque(maxlen=max(1, len(total_unique_asset_ids) - 1)) if len(total_unique_asset_ids) > 1 else deque()
    output_paths: list[Path] = []
    selected_music_paths: list[Path] = []
    selected_music_start_ms_values: list[int] = []
    selected_duration_ms_values: list[int] = []
    selected_opening_paths: list[Path] = []
    selected_closing_paths: list[Path] = []
    variant_manifests: list[dict[str, object]] = []
    quick_mix_warnings: list[dict[str, object]] = []
    existing_variant_manifests = _load_existing_quick_mix_variants(resolved_work_dir)
    seen_variant_manifests = list(existing_variant_manifests)
    used_variant_signatures = {
        _build_quick_mix_variant_signature_from_manifest(variant)
        for variant in existing_variant_manifests
    }
    used_variant_signatures.update(
        _build_quick_mix_variant_legacy_signature_from_manifest(variant)
        for variant in existing_variant_manifests
    )
    music_variant_pool: list[Path] = []
    music_duration_cache: dict[Path, int] = {}
    opening_variant_pool: list[Asset] = []
    closing_variant_pool: list[Asset] = []
    marker_episode_ids = {
        asset.asset_id
        for asset in [*opening_assets, *closing_assets]
    }

    for output_index in range(normalized_output_count):
        accepted_plan: dict[str, object] | None = None
        accepted_rank: tuple[int, ...] | None = None
        duplicate_fallback_plan: dict[str, object] | None = None
        duplicate_fallback_rank: tuple[int, ...] | None = None
        for _attempt_index in range(QUICK_MIX_VARIANT_SEARCH_ATTEMPTS):
            attempt_music_variant_pool = list(music_variant_pool)
            attempt_opening_variant_pool = list(opening_variant_pool)
            attempt_closing_variant_pool = list(closing_variant_pool)
            attempt_episode_take_pools = {
                episode_id: list(pool)
                for episode_id, pool in episode_take_pools.items()
            }
            attempt_episode_usage_counts = dict(episode_usage_counts)
            attempt_take_usage_counts = dict(take_usage_counts)
            attempt_asset_usage_counts = dict(asset_usage_counts)
            attempt_source_group_usage_counts = dict(source_group_usage_counts)
            attempt_recent_take_ids_by_episode = {
                episode_id: deque(recent_take_ids, maxlen=recent_take_ids.maxlen)
                for episode_id, recent_take_ids in recent_take_ids_by_episode.items()
            }
            attempt_exhausted_asset_ids_by_episode = {
                episode_id: deque(exhausted_asset_ids, maxlen=exhausted_asset_ids.maxlen)
                for episode_id, exhausted_asset_ids in exhausted_asset_ids_by_episode.items()
            }
            attempt_globally_exhausted_asset_ids = deque(
                globally_exhausted_asset_ids,
                maxlen=globally_exhausted_asset_ids.maxlen,
            )

            selected_music_path = _take_next_variant(resolved_music_paths, attempt_music_variant_pool)
            opening_asset = _take_next_variant(opening_assets, attempt_opening_variant_pool)
            closing_asset = _take_next_variant(closing_assets, attempt_closing_variant_pool)
            if selected_music_path is not None and use_music_duration:
                target_duration_ms = _resolve_audio_track_duration_ms(selected_music_path, ffprobe_path)
            else:
                target_duration_ms = fallback_duration_ms
            selected_music_start_ms = _select_music_start_ms(
                selected_music_path,
                target_duration_ms=target_duration_ms,
                ffprobe_path=ffprobe_path,
                use_music_duration=use_music_duration,
                duration_cache=music_duration_cache,
            )

            remaining_ms = target_duration_ms
            step_index = 0
            selected_take_manifest: list[dict[str, object]] = []
            episode_order: list[str] = []
            segment_plans: list[dict[str, object]] = []
            output_warnings: list[dict[str, object]] = []
            used_episode_ids_in_output: set[str] = set()
            used_take_ids_in_output: set[str] = set()
            used_asset_ids_in_output: set[str] = set()
            used_source_groups_in_output: set[str] = set()
            allow_output_level_reuse = False
            reserved_episode_ids_in_output = set(marker_episode_ids)
            used_episode_ids_in_output.update(reserved_episode_ids_in_output)
            episode_order_queue = _build_episode_order_queue(
                ordered_episode_ids,
                used_episode_ids_in_output,
                reserved_episode_ids_in_output,
                attempt_episode_usage_counts,
            )
            cycle_progress = False

            if opening_asset is not None:
                intro_ms = _pinned_segment_ms(opening_asset, remaining_ms)
                if intro_ms > 0:
                    segment_plans.append(
                        {
                            "asset": opening_asset,
                            "start_ms": 0,
                            "duration_ms": intro_ms,
                            "step_index": step_index,
                        }
                    )
                    remaining_ms -= intro_ms
                    step_index += 1

            if closing_asset is not None:
                if use_closing_duration:
                    closing_remaining_ms = closing_asset.duration_ms or remaining_ms
                    closing_segment_ms = _pinned_segment_ms(
                        closing_asset,
                        closing_remaining_ms,
                        use_full_duration=True,
                    )
                else:
                    closing_segment_ms = _pinned_segment_ms(closing_asset, remaining_ms, use_full_duration=False)
            else:
                closing_segment_ms = 0

            reserved_closing_ms = 0 if use_closing_duration else closing_segment_ms

            while remaining_ms > reserved_closing_ms:
                if not episode_order_queue:
                    if not cycle_progress:
                        if allow_output_level_reuse:
                            break
                        allow_output_level_reuse = True
                    episode_order_queue = _build_episode_order_queue(
                        ordered_episode_ids,
                        used_episode_ids_in_output,
                        reserved_episode_ids_in_output,
                        attempt_episode_usage_counts,
                    )
                    if not episode_order_queue:
                        break
                    cycle_progress = False
                episode_id = episode_order_queue.popleft()
                episode_group = episode_lookup[episode_id]
                take_pool = attempt_episode_take_pools.setdefault(episode_id, [])
                recent_take_ids = set(attempt_recent_take_ids_by_episode.get(episode_id, ()))
                exhausted_asset_ids = set(attempt_exhausted_asset_ids_by_episode.get(episode_id, ()))
                selected_take, selection_warning = _select_balanced_take_variant(
                    episode_group["takes"],
                    take_pool,
                    attempt_take_usage_counts,
                    attempt_asset_usage_counts,
                    attempt_source_group_usage_counts,
                    avoid_take_ids=((set() if allow_output_level_reuse else used_take_ids_in_output) | recent_take_ids),
                    avoid_asset_ids=(
                        (set() if allow_output_level_reuse else used_asset_ids_in_output)
                        | exhausted_asset_ids
                        | set(attempt_globally_exhausted_asset_ids)
                    ),
                    avoid_source_groups=(set() if allow_output_level_reuse else used_source_groups_in_output),
                    output_index=output_index,
                    step_index=step_index,
                )
                if selected_take is None:
                    continue
                asset = selected_take["asset"]
                attempt_episode_usage_counts[episode_id] = attempt_episode_usage_counts.get(episode_id, 0) + 1
                selected_take_id = _take_identifier(selected_take)
                attempt_take_usage_counts[selected_take_id] = attempt_take_usage_counts.get(selected_take_id, 0) + 1
                selected_asset_id = _asset_identifier(selected_take)
                attempt_asset_usage_counts[selected_asset_id] = attempt_asset_usage_counts.get(selected_asset_id, 0) + 1
                selected_source_group = _source_group_identifier(selected_take)
                if selected_source_group:
                    attempt_source_group_usage_counts[selected_source_group] = (
                        attempt_source_group_usage_counts.get(selected_source_group, 0) + 1
                    )
                used_take_ids_in_output.add(selected_take_id)
                used_asset_ids_in_output.add(selected_asset_id)
                if selected_source_group:
                    used_source_groups_in_output.add(selected_source_group)
                recent_take_ids_queue = attempt_recent_take_ids_by_episode.get(episode_id)
                if recent_take_ids_queue is not None:
                    recent_take_ids_queue.append(selected_take_id)
                exhausted_asset_ids_queue = attempt_exhausted_asset_ids_by_episode.get(episode_id)
                if exhausted_asset_ids_queue is not None:
                    exhausted_asset_ids_queue.append(selected_asset_id)
                if attempt_globally_exhausted_asset_ids.maxlen:
                    attempt_globally_exhausted_asset_ids.append(selected_asset_id)
                if selection_warning is not None:
                    output_warnings.append(selection_warning)
                segment_budget_ms = remaining_ms - reserved_closing_ms
                preferred_ms = _choose_body_segment_ms(
                    asset,
                    segment_budget_ms,
                    minimum_body_ms=minimum_body_ms,
                    maximum_body_ms=maximum_body_ms,
                )
                if preferred_ms <= 0:
                    raise ValueError(f"Could not determine a usable segment duration for asset: {asset.path}")
                start_ms, segment_ms = _choose_take_render_window(selected_take, asset, preferred_ms)
                if segment_ms <= 0:
                    continue

                segment_plans.append(
                    {
                        "asset": asset,
                        "start_ms": start_ms,
                        "duration_ms": segment_ms,
                        "step_index": step_index,
                    }
                )
                remaining_ms -= segment_ms
                step_index += 1
                cycle_progress = True
                used_episode_ids_in_output.add(episode_id)
                episode_order.append(episode_id)
                selected_take_manifest.append(
                    {
                        "episode_id": episode_id,
                        "episode_label": episode_group["episode_label"],
                        "take_id": selected_take["take_id"],
                        "take_index": selected_take["take_index"],
                        "marker_split": bool(selected_take["marker_split"]),
                        "asset_id": asset.asset_id,
                        "media_type": asset.media_type.value,
                        "normalized_source_group": normalize_quick_mix_source_group(asset.path),
                        "source_path": str(asset.path.resolve()),
                        "source_start_ms": int(selected_take["start_ms"]),
                        "source_end_ms": int(selected_take["end_ms"]),
                        "render_start_ms": start_ms,
                        "render_end_ms": start_ms + segment_ms,
                    }
                )

            if closing_asset is not None and closing_segment_ms > 0:
                closing_start_ms = 0
                if closing_asset.media_type == MediaType.VIDEO and closing_asset.duration_ms:
                    closing_start_ms = max(0, closing_asset.duration_ms - closing_segment_ms)
                segment_plans.append(
                    {
                        "asset": closing_asset,
                        "start_ms": closing_start_ms,
                        "duration_ms": closing_segment_ms,
                        "step_index": step_index,
                    }
                )

            variant_signature = _build_quick_mix_variant_signature(
                selected_take_manifest,
                selected_music_path=selected_music_path,
                selected_music_start_ms=selected_music_start_ms,
                opening_asset=opening_asset,
                closing_asset=closing_asset,
                target_duration_ms=target_duration_ms,
                use_closing_duration=use_closing_duration,
            )
            variant_legacy_signature = _build_quick_mix_variant_legacy_signature(
                selected_take_manifest,
                selected_music_path=selected_music_path,
                selected_music_start_ms=selected_music_start_ms,
                opening_asset=opening_asset,
                closing_asset=closing_asset,
                target_duration_ms=target_duration_ms,
                use_closing_duration=use_closing_duration,
            )
            variant_manifest_preview = {
                "episode_order": episode_order,
                "selected_takes": selected_take_manifest,
                "music_path": str(selected_music_path) if selected_music_path else "",
                "music_start_ms": selected_music_start_ms,
                "opening_media_path": str(opening_asset.path.resolve()) if opening_asset is not None else "",
                "closing_media_path": str(closing_asset.path.resolve()) if closing_asset is not None else "",
                "use_closing_duration": use_closing_duration,
                "target_duration_ms": target_duration_ms,
            }
            variant_rank = _build_variant_similarity_rank(variant_manifest_preview, seen_variant_manifests)
            candidate_plan = {
                "selected_music_path": selected_music_path,
                "selected_music_start_ms": selected_music_start_ms,
                "opening_asset": opening_asset,
                "closing_asset": closing_asset,
                "target_duration_ms": target_duration_ms,
                "segment_plans": segment_plans,
                "selected_take_manifest": selected_take_manifest,
                "episode_order": episode_order,
                "variant_manifest_preview": variant_manifest_preview,
                "variant_signature": variant_signature,
                "variant_legacy_signature": variant_legacy_signature,
                "variant_rank": variant_rank,
                "output_warnings": output_warnings,
                "episode_take_pools": attempt_episode_take_pools,
                "episode_usage_counts": attempt_episode_usage_counts,
                "take_usage_counts": attempt_take_usage_counts,
                "asset_usage_counts": attempt_asset_usage_counts,
                "source_group_usage_counts": attempt_source_group_usage_counts,
                "recent_take_ids_by_episode": attempt_recent_take_ids_by_episode,
                "exhausted_asset_ids_by_episode": attempt_exhausted_asset_ids_by_episode,
                "globally_exhausted_asset_ids": attempt_globally_exhausted_asset_ids,
                "music_variant_pool": attempt_music_variant_pool,
                "opening_variant_pool": attempt_opening_variant_pool,
                "closing_variant_pool": attempt_closing_variant_pool,
            }
            if variant_signature in used_variant_signatures or variant_legacy_signature in used_variant_signatures:
                if duplicate_fallback_rank is None or variant_rank < duplicate_fallback_rank:
                    duplicate_fallback_plan = candidate_plan
                    duplicate_fallback_rank = variant_rank
                continue
            if accepted_rank is not None and variant_rank >= accepted_rank:
                continue

            accepted_plan = candidate_plan
            accepted_rank = variant_rank

        if accepted_plan is None:
            if duplicate_fallback_plan is None:
                raise ValueError(
                    "No new unique Quick Mix combinations remain for the selected source materials and current options."
                )
            fallback_take_ids = {
                str(take.get("take_id", ""))
                for take in duplicate_fallback_plan["selected_take_manifest"]
                if isinstance(take, dict)
            }
            if len(fallback_take_ids) <= 1:
                raise ValueError(
                    "No new unique Quick Mix combinations remain for the selected source materials and current options."
                )
            accepted_plan = duplicate_fallback_plan

        selected_music_path = accepted_plan["selected_music_path"]
        selected_music_start_ms = int(accepted_plan["selected_music_start_ms"])
        opening_asset = accepted_plan["opening_asset"]
        closing_asset = accepted_plan["closing_asset"]
        target_duration_ms = int(accepted_plan["target_duration_ms"])
        selected_take_manifest = list(accepted_plan["selected_take_manifest"])
        episode_order = list(accepted_plan["episode_order"])
        music_variant_pool = list(accepted_plan["music_variant_pool"])
        opening_variant_pool = list(accepted_plan["opening_variant_pool"])
        closing_variant_pool = list(accepted_plan["closing_variant_pool"])
        episode_take_pools = {
            episode_id: list(pool)
            for episode_id, pool in accepted_plan["episode_take_pools"].items()
        }
        episode_usage_counts = dict(accepted_plan["episode_usage_counts"])
        take_usage_counts = dict(accepted_plan["take_usage_counts"])
        asset_usage_counts = dict(accepted_plan["asset_usage_counts"])
        source_group_usage_counts = dict(accepted_plan["source_group_usage_counts"])
        recent_take_ids_by_episode = {
            episode_id: deque(recent_take_ids, maxlen=recent_take_ids.maxlen)
            for episode_id, recent_take_ids in accepted_plan["recent_take_ids_by_episode"].items()
        }
        exhausted_asset_ids_by_episode = {
            episode_id: deque(exhausted_asset_ids, maxlen=exhausted_asset_ids.maxlen)
            for episode_id, exhausted_asset_ids in accepted_plan["exhausted_asset_ids_by_episode"].items()
        }
        globally_exhausted_asset_ids = deque(
            accepted_plan["globally_exhausted_asset_ids"],
            maxlen=accepted_plan["globally_exhausted_asset_ids"].maxlen,
        )
        used_variant_signatures.add(str(accepted_plan["variant_signature"]))
        used_variant_signatures.add(str(accepted_plan["variant_legacy_signature"]))
        seen_variant_manifests.append(dict(accepted_plan["variant_manifest_preview"]))

        if selected_music_path is not None:
            selected_music_paths.append(selected_music_path)
            selected_music_start_ms_values.append(selected_music_start_ms)
        if opening_asset is not None:
            selected_opening_paths.append(opening_asset.path.resolve())
        if closing_asset is not None:
            selected_closing_paths.append(closing_asset.path.resolve())
        selected_duration_ms_values.append(
            sum(int(segment_plan["duration_ms"]) for segment_plan in accepted_plan["segment_plans"])
        )

        segment_paths: list[Path] = []
        for segment_plan in accepted_plan["segment_plans"]:
            step_number = int(segment_plan["step_index"]) + 1
            segment_path = segments_dir / f"quick_mix_{output_index + 1:03d}_seg_{step_number:02d}.mp4"
            _render_quick_mix_segment(
                segment_plan["asset"],
                segment_path,
                start_ms=int(segment_plan["start_ms"]),
                duration_ms=int(segment_plan["duration_ms"]),
                ffmpeg_path=ffmpeg_path,
            )
            segment_paths.append(segment_path)

        output_path = exports_dir / f"quick_mix_{output_index + 1:03d}.mp4"
        _render_quick_mix_output(
            segment_paths,
            output_path,
            ffmpeg_path,
            music_path=selected_music_path,
            music_start_ms=selected_music_start_ms,
        )
        output_paths.append(output_path)
        variant_manifests.append(
            {
                "variant_id": output_path.stem,
                "output_path": str(output_path.relative_to(resolved_work_dir)).replace("\\", "/"),
                "episode_order": episode_order,
                "selected_takes": selected_take_manifest,
                "music_path": str(selected_music_path) if selected_music_path else "",
                "music_start_ms": selected_music_start_ms,
                "opening_media_path": str(opening_asset.path.resolve()) if opening_asset is not None else "",
                "closing_media_path": str(closing_asset.path.resolve()) if closing_asset is not None else "",
                "use_closing_duration": use_closing_duration,
                "target_duration_ms": target_duration_ms,
                "generated_duration_ms": sum(int(segment_plan["duration_ms"]) for segment_plan in accepted_plan["segment_plans"]),
                "warnings": list(accepted_plan["output_warnings"]),
            }
        )
        quick_mix_warnings.extend(list(accepted_plan["output_warnings"]))

    generation_elapsed_ms = max(0, int((time.perf_counter() - generation_started_at) * 1000))
    reported_duration_seconds = (
        (sum(selected_duration_ms_values) / len(selected_duration_ms_values)) / 1000
        if selected_duration_ms_values
        else fallback_duration_ms / 1000
    )
    quick_mix_plan_path = "reports/quick_mix_plan.json"
    write_json(
        resolved_work_dir / quick_mix_plan_path,
        _build_quick_mix_plan_report(
            [*existing_variant_manifests, *variant_manifests],
            requested_duration_ms=fallback_duration_ms,
            requested_output_count=normalized_output_count,
            warnings=quick_mix_warnings,
        ),
    )

    _prepare_quick_mix_workdir(
        resolved_work_dir,
        project=project,
        assets=assets,
        output_paths=output_paths,
        duration_seconds=reported_duration_seconds,
        output_count=normalized_output_count,
        episode_duration_min_seconds=minimum_body_ms / 1000,
        episode_duration_max_seconds=maximum_body_ms / 1000,
        music_path=selected_music_paths[0] if selected_music_paths else None,
        music_paths=resolved_music_paths,
        use_music_duration=use_music_duration,
        opening_media_path=selected_opening_paths[0] if selected_opening_paths else None,
        opening_media_paths=[asset.path.resolve() for asset in opening_assets],
        closing_media_path=selected_closing_paths[0] if selected_closing_paths else None,
        closing_media_paths=[asset.path.resolve() for asset in closing_assets],
        use_closing_duration=use_closing_duration,
        generation_elapsed_ms=generation_elapsed_ms,
        variants=[*existing_variant_manifests, *variant_manifests],
        episode_groups=[_serialize_episode_group(group) for group in episode_groups],
        quick_mix_warning_count=len(quick_mix_warnings),
        quick_mix_warnings=quick_mix_warnings,
        quick_mix_plan_path=quick_mix_plan_path,
    )

    return {
        "source_dir": str(source_input),
        "resolved_source_dir": str(source_dir),
        "source_kind": "zip" if source_input.is_file() else "directory",
        "work_dir": str(resolved_work_dir),
        "project_name": project.name,
        "pack": project.industry_pack,
        "duration_seconds": reported_duration_seconds,
        "episode_duration_min_seconds": minimum_body_ms / 1000,
        "episode_duration_max_seconds": maximum_body_ms / 1000,
        "duration_source": "music" if resolved_music_paths and use_music_duration else "manual",
        "output_count": normalized_output_count,
        "generated_count": len(output_paths),
        "generation_elapsed_ms": generation_elapsed_ms,
        "video_count": sum(asset.media_type == MediaType.VIDEO for asset in usable_assets),
        "image_count": sum(asset.media_type == MediaType.PHOTO for asset in usable_assets),
        "photo_support": True,
        "music_path": str(selected_music_paths[0]) if selected_music_paths else "",
        "music_paths": [str(path) for path in resolved_music_paths],
        "used_music_paths": [str(path) for path in selected_music_paths],
        "use_music_duration": bool(resolved_music_paths and use_music_duration),
        "use_closing_duration": use_closing_duration,
        "opening_media_path": str(selected_opening_paths[0]) if selected_opening_paths else "",
        "opening_media_paths": [str(asset.path.resolve()) for asset in opening_assets],
        "used_opening_media_paths": [str(path) for path in selected_opening_paths],
        "closing_media_path": str(selected_closing_paths[0]) if selected_closing_paths else "",
        "closing_media_paths": [str(asset.path.resolve()) for asset in closing_assets],
        "used_closing_media_paths": [str(path) for path in selected_closing_paths],
        "episode_groups": [_serialize_episode_group(group) for group in episode_groups],
        "variants": variant_manifests,
        "quick_mix_warning_count": len(quick_mix_warnings),
        "quick_mix_warnings": quick_mix_warnings,
        "quick_mix_plan_path": quick_mix_plan_path,
        "output_paths": [str(path.relative_to(resolved_work_dir)).replace("\\", "/") for path in output_paths],
    }


def estimate_quick_mix_capacity(
    raw_source_dir: str,
    *,
    duration_seconds: float,
    episode_duration_min_seconds: float = 1.5,
    episode_duration_max_seconds: float = 2.0,
    ffmpeg_path: str = "ffmpeg",
    ffprobe_path: str = "ffprobe",
    music_path: str | None = None,
    music_paths: list[str] | None = None,
    use_music_duration: bool = False,
    opening_media_path: str | None = None,
    opening_media_paths: list[str] | None = None,
    closing_media_path: str | None = None,
    closing_media_paths: list[str] | None = None,
    use_closing_duration: bool = False,
) -> dict:
    fallback_duration_ms, _ = _validate_quick_mix_inputs(duration_seconds, 1)
    minimum_body_ms, maximum_body_ms = _validate_episode_duration_range(
        episode_duration_min_seconds,
        episode_duration_max_seconds,
    )

    source_dir = resolve_source_dir(raw_source_dir)
    source_input = Path(raw_source_dir).expanduser().resolve()
    project = Project(stable_id("project", str(source_input)), source_input.stem if source_input.is_file() else source_dir.name, source_dir, "wedding")

    assets = score_assets(probe_assets(scan_project_assets(project), ffprobe_path=ffprobe_path))
    usable_assets = [asset for asset in assets if asset.media_type in {MediaType.VIDEO, MediaType.PHOTO}]
    if not usable_assets:
        raise ValueError("No usable video or photo files were found in the selected source folder.")

    assets_by_path = {asset.path.resolve(): asset for asset in assets}
    opening_assets = _resolve_optional_media_assets(
        opening_media_path,
        opening_media_paths,
        project=project,
        assets_by_path=assets_by_path,
        ffprobe_path=ffprobe_path,
        label="Opening media",
    )
    closing_assets = _resolve_optional_media_assets(
        closing_media_path,
        closing_media_paths,
        project=project,
        assets_by_path=assets_by_path,
        ffprobe_path=ffprobe_path,
        label="Closing media",
    )
    resolved_music_paths = _resolve_music_paths(music_path, music_paths)
    if resolved_music_paths and use_music_duration:
        durations = [_resolve_audio_track_duration_ms(path, ffprobe_path) for path in resolved_music_paths]
        target_duration_ms = max(1000, int(sum(durations) / len(durations)))
        duration_source = "music"
    else:
        target_duration_ms = fallback_duration_ms
        duration_source = "manual"

    episode_groups = _build_episode_groups(usable_assets, ffmpeg_path, source_dir)
    if not episode_groups:
        raise ValueError("No usable Quick Mix episode groups could be built from the selected source folder.")
    total_segment_candidates = sum(int(group["take_count"]) for group in episode_groups)
    unique_asset_count = len(episode_groups)

    remaining_ms = target_duration_ms
    segments_per_output = 0

    opening_asset = opening_assets[0] if opening_assets else None
    closing_asset = closing_assets[0] if closing_assets else None

    if opening_asset is not None:
        opening_ms = _pinned_segment_ms(opening_asset, remaining_ms)
        if opening_ms > 0:
            segments_per_output += 1
            remaining_ms -= opening_ms

    if closing_asset is not None:
        if use_closing_duration:
            closing_remaining_ms = closing_asset.duration_ms or remaining_ms
            closing_segment_ms = _pinned_segment_ms(
                closing_asset,
                closing_remaining_ms,
                use_full_duration=True,
            )
        else:
            closing_segment_ms = _pinned_segment_ms(closing_asset, remaining_ms, use_full_duration=False)
    else:
        closing_segment_ms = 0
    body_remaining_ms = remaining_ms if use_closing_duration else max(0, remaining_ms - closing_segment_ms)
    average_body_segment_ms = max(100, int((minimum_body_ms + maximum_body_ms) / 2))
    body_segments_per_output = math.ceil(body_remaining_ms / average_body_segment_ms) if body_remaining_ms > 0 else 0
    selected_episode_count = min(unique_asset_count, body_segments_per_output)
    segments_per_output += selected_episode_count

    if closing_segment_ms > 0:
        segments_per_output += 1

    if segments_per_output <= 0:
        estimated_unique_outputs = 0
    else:
        estimated_unique_outputs = _count_episode_combinations(
            [int(group["take_count"]) for group in episode_groups],
            selected_episode_count,
        )

    return {
        "source_dir": str(source_input),
        "resolved_source_dir": str(source_dir),
        "duration_seconds": (target_duration_ms + (closing_segment_ms if use_closing_duration else 0)) / 1000,
        "episode_duration_min_seconds": minimum_body_ms / 1000,
        "episode_duration_max_seconds": maximum_body_ms / 1000,
        "duration_source": duration_source,
        "use_music_duration": bool(resolved_music_paths and use_music_duration),
        "use_closing_duration": use_closing_duration,
        "usable_asset_count": len(usable_assets),
        "unique_asset_count": unique_asset_count,
        "episode_group_count": unique_asset_count,
        "total_segment_candidates": total_segment_candidates,
        "segments_per_output": segments_per_output,
        "body_segments_per_output": body_segments_per_output,
        "selected_episode_count": selected_episode_count,
        "estimated_unique_outputs": estimated_unique_outputs,
        "opening_enabled": opening_asset is not None,
        "closing_enabled": closing_asset is not None,
        "music_paths": [str(path) for path in resolved_music_paths],
        "opening_media_paths": [str(asset.path.resolve()) for asset in opening_assets],
        "closing_media_paths": [str(asset.path.resolve()) for asset in closing_assets],
        "episode_groups": [_serialize_episode_group(group) for group in episode_groups],
    }


def plan_source_materials(
    raw_source_dir: str,
    *,
    project_name: str | None = None,
    pack: str = "wedding",
    work_dir: str | None = None,
    ffprobe_path: str = "ffprobe",
    ffmpeg_path: str = "ffmpeg",
    scenedetect_path: str = "scenedetect",
    prefer_pyscenedetect: bool = False,
    clip_ms: int = 3000,
    max_clips_per_asset: int = 12,
    max_candidates: int = 10,
) -> dict:
    source_dir = resolve_source_dir(raw_source_dir)
    source_input = Path(raw_source_dir).expanduser().resolve()
    project = Project(stable_id("project", str(source_input)), project_name or source_input.stem, source_dir, pack)
    resolved_work_dir = resolve_work_dir(source_dir, work_dir, source_hint=source_input)

    assets = score_assets(probe_assets(scan_project_assets(project), ffprobe_path=ffprobe_path))
    if not assets:
        raise ValueError("No supported media files were found in the selected source folder.")

    clips = plan_segments_for_assets(
        assets,
        resolved_work_dir / "clips",
        segmenters=_build_segmenters(
            clip_ms=clip_ms,
            max_clips_per_asset=max_clips_per_asset,
            prefer_pyscenedetect=prefer_pyscenedetect,
            scenedetect_path=scenedetect_path,
        ),
    )
    clips = apply_filename_tags(clips)
    clips = apply_duplicate_detection(clips)
    clips = score_clips(clips, assets)

    if project.industry_pack == "wedding":
        templates = get_wedding_templates()
    else:
        raise ValueError(f"Unsupported pack: {project.industry_pack}")

    candidates = build_candidates(project.project_id, project.industry_pack, templates, clips, max_candidates)

    save_project(resolved_work_dir, project)
    save_assets(resolved_work_dir, assets)
    save_clips(resolved_work_dir, clips)
    save_candidates(resolved_work_dir, candidates)
    save_summary(resolved_work_dir, build_summary(project, assets, clips, candidates))

    review_path, thumbnail_count, thumbnail_warnings = write_review_html(
        project,
        candidates,
        clips,
        assets,
        resolved_work_dir,
        ffmpeg_path=ffmpeg_path,
    )

    return {
        "source_dir": str(source_input),
        "resolved_source_dir": str(source_dir),
        "source_kind": "zip" if source_input.is_file() else "directory",
        "work_dir": str(resolved_work_dir),
        "project_name": project.name,
        "pack": project.industry_pack,
        "asset_count": len(assets),
        "clip_count": len(clips),
        "candidate_count": len(candidates),
        "review_path": str(review_path),
        "thumbnail_count": thumbnail_count,
        "thumbnail_warning_count": len(thumbnail_warnings),
    }
