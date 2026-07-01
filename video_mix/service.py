from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .core.asset_scan import SKIP_DIR_NAMES, detect_media_type, scan_project_assets, stable_id
from .core.candidate_builder import build_candidates
from .core.duplicate_detection import apply_duplicate_detection
from .core.media_probe import probe_assets
from .core.models import Asset, MediaType, Project
from .core.review import write_review_html
from .core.scoring import score_assets, score_clips
from .core.segmenters import (
    FixedIntervalSegmenter,
    PySceneDetectSegmenter,
    TakeMarkerSegmenter,
    plan_segments_for_assets,
)
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


QUICK_MIX_SOURCE_START_MS = "quick_mix_source_start_ms"
QUICK_MIX_SOURCE_ASSET_ID = "quick_mix_source_asset_id"
QUICK_MIX_TAKE_INDEX = "quick_mix_take_index"
QUICK_MIX_TAKE_MARKER = "quick_mix_take_marker"


def resolve_source_dir(raw_source_dir: str) -> Path:
    source_dir = Path(raw_source_dir).expanduser().resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"Source folder does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source folder is not a directory: {source_dir}")
    return source_dir


def resolve_work_dir(source_dir: Path, work_dir: str | None = None, *, cwd: Path | None = None) -> Path:
    if not work_dir:
        return source_dir / "_video_mix_work"
    raw = Path(work_dir).expanduser()
    if raw.is_absolute():
        return raw.resolve()
    base_dir = cwd.resolve() if cwd is not None else Path.cwd().resolve()
    return (base_dir / raw).resolve()


def scan_source_materials(raw_source_dir: str, preview_limit: int = 8) -> dict:
    source_dir = resolve_source_dir(raw_source_dir)
    project = Project(
        project_id=stable_id("project", str(source_dir)),
        name=source_dir.name,
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
        if any(part in SKIP_DIR_NAMES for part in path.parts):
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
        "source_dir": str(source_dir),
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
        "suggested_work_dir": str(resolve_work_dir(source_dir)),
    }


def _build_segmenters(
    *,
    clip_ms: int = 3000,
    max_clips_per_asset: int = 12,
    prefer_pyscenedetect: bool = False,
    scenedetect_path: str = "scenedetect",
    ffmpeg_path: str = "ffmpeg",
):
    take_marker = TakeMarkerSegmenter(ffmpeg_path=ffmpeg_path)
    fixed = FixedIntervalSegmenter(clip_ms=clip_ms, max_clips_per_asset=max_clips_per_asset)
    if prefer_pyscenedetect:
        return [take_marker, PySceneDetectSegmenter(scenedetect_path), fixed]
    return [take_marker, fixed]


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


def _preferred_segment_ms(asset: Asset, remaining_ms: int) -> int:
    if asset.media_type == MediaType.PHOTO:
        return min(remaining_ms, 2000 if remaining_ms > 2000 else remaining_ms)
    if not asset.duration_ms:
        return min(remaining_ms, 2000)
    return min(remaining_ms, min(3000, asset.duration_ms))


def _quick_mix_source_start_ms(asset: Asset) -> int:
    raw_value = asset.metadata.get(QUICK_MIX_SOURCE_START_MS, 0)
    return int(raw_value) if raw_value is not None else 0


def _clone_asset_for_quick_mix_take(asset: Asset, take_clip) -> Asset:
    metadata = dict(asset.metadata)
    metadata.update(
        {
            QUICK_MIX_SOURCE_ASSET_ID: asset.asset_id,
            QUICK_MIX_SOURCE_START_MS: take_clip.source_start_ms,
            QUICK_MIX_TAKE_INDEX: take_clip.metadata.get("take_index"),
            QUICK_MIX_TAKE_MARKER: take_clip.metadata.get("take_marker"),
        }
    )
    return Asset(
        asset_id=f"{asset.asset_id}_{take_clip.clip_id}",
        project_id=asset.project_id,
        path=asset.path,
        media_type=asset.media_type,
        duration_ms=take_clip.duration_ms,
        width=asset.width,
        height=asset.height,
        fps=asset.fps,
        orientation=asset.orientation,
        has_audio=asset.has_audio,
        probe_status=asset.probe_status,
        quality_score=asset.quality_score,
        metadata=metadata,
    )


def _build_quick_mix_usable_assets(assets: list[Asset], work_dir: Path, *, ffmpeg_path: str) -> tuple[list[Asset], int]:
    usable_assets: list[Asset] = []
    detected_take_count = 0
    take_segmenter = TakeMarkerSegmenter(ffmpeg_path=ffmpeg_path)

    for asset in assets:
        if asset.media_type == MediaType.VIDEO and asset.duration_ms:
            take_clips = take_segmenter.plan(asset, work_dir / "quick_mix_takes")
            if take_clips:
                detected_take_count += len(take_clips)
                usable_assets.extend(_clone_asset_for_quick_mix_take(asset, take_clip) for take_clip in take_clips)
                continue
        if asset.media_type in {MediaType.VIDEO, MediaType.PHOTO}:
            usable_assets.append(asset)

    return usable_assets, detected_take_count


def _build_video_segment_command(
    asset: Asset,
    output_path: Path,
    *,
    start_ms: int,
    duration_ms: int,
    ffmpeg_path: str,
) -> list[str]:
    return [
        ffmpeg_path,
        "-y",
        "-ss",
        f"{start_ms / 1000:.3f}",
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


def _render_quick_mix_output(segment_paths: list[Path], output_path: Path, ffmpeg_path: str) -> None:
    concat_dir = output_path.parent.parent / "quick_mix_concat"
    concat_dir.mkdir(parents=True, exist_ok=True)
    concat_path = concat_dir / f"{output_path.stem}.txt"
    concat_path.write_text(
        "".join(f"file '{segment_path.as_posix()}'\n" for segment_path in segment_paths),
        encoding="utf-8",
    )
    subprocess.run(_build_quick_mix_concat_command(concat_path, output_path, ffmpeg_path), check=True)


def _prepare_quick_mix_workdir(
    work_dir: Path,
    *,
    project: Project,
    assets: list[Asset],
    output_paths: list[Path],
    duration_seconds: float,
    output_count: int,
    quick_mix_source_count: int,
    detected_take_count: int,
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
            "generated_count": len(output_paths),
            "quick_mix_source_count": quick_mix_source_count,
            "detected_take_count": detected_take_count,
            "output_paths": [str(path.relative_to(work_dir)).replace("\\", "/") for path in output_paths],
        },
    )


def quick_mix_source_materials(
    raw_source_dir: str,
    *,
    duration_seconds: float,
    output_count: int,
    project_name: str | None = None,
    pack: str = "wedding",
    work_dir: str | None = None,
    ffmpeg_path: str = "ffmpeg",
    ffprobe_path: str = "ffprobe",
) -> dict:
    target_duration_ms, normalized_output_count = _validate_quick_mix_inputs(duration_seconds, output_count)
    _ensure_ffmpeg_available(ffmpeg_path)

    source_dir = resolve_source_dir(raw_source_dir)
    project = Project(stable_id("project", str(source_dir)), project_name or source_dir.name, source_dir, pack)
    resolved_work_dir = resolve_work_dir(source_dir, work_dir)

    assets = score_assets(probe_assets(scan_project_assets(project), ffprobe_path=ffprobe_path))
    if not assets:
        raise ValueError("No supported media files were found in the selected source folder.")

    source_assets = [asset for asset in assets if asset.media_type in {MediaType.VIDEO, MediaType.PHOTO}]
    usable_assets, detected_take_count = _build_quick_mix_usable_assets(
        source_assets,
        resolved_work_dir,
        ffmpeg_path=ffmpeg_path,
    )
    if not usable_assets:
        raise ValueError("No usable video or photo files were found in the selected source folder.")

    exports_dir = resolved_work_dir / "exports"
    segments_dir = resolved_work_dir / "quick_mix_segments"
    exports_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)

    video_offsets: dict[str, int] = {}
    asset_cursor = 0
    output_paths: list[Path] = []

    for output_index in range(normalized_output_count):
        remaining_ms = target_duration_ms
        segment_paths: list[Path] = []
        step_index = 0

        while remaining_ms > 0:
            asset = usable_assets[asset_cursor % len(usable_assets)]
            asset_cursor += 1
            preferred_ms = _preferred_segment_ms(asset, remaining_ms)
            if preferred_ms <= 0:
                raise ValueError(f"Could not determine a usable segment duration for asset: {asset.path}")

            if asset.media_type == MediaType.VIDEO and asset.duration_ms:
                segment_ms = min(preferred_ms, asset.duration_ms)
                max_start = max(0, asset.duration_ms - segment_ms)
                cursor = video_offsets.get(asset.asset_id, 0)
                relative_start_ms = min(cursor, max_start)
                start_ms = _quick_mix_source_start_ms(asset) + relative_start_ms
                next_cursor = cursor + segment_ms
                video_offsets[asset.asset_id] = 0 if next_cursor >= max_start and max_start > 0 else next_cursor
            else:
                segment_ms = preferred_ms
                start_ms = 0

            segment_path = segments_dir / f"quick_mix_{output_index + 1:03d}_seg_{step_index + 1:02d}.mp4"
            _render_quick_mix_segment(
                asset,
                segment_path,
                start_ms=start_ms,
                duration_ms=segment_ms,
                ffmpeg_path=ffmpeg_path,
            )
            segment_paths.append(segment_path)
            remaining_ms -= segment_ms
            step_index += 1

        output_path = exports_dir / f"quick_mix_{output_index + 1:03d}.mp4"
        _render_quick_mix_output(segment_paths, output_path, ffmpeg_path)
        output_paths.append(output_path)

    _prepare_quick_mix_workdir(
        resolved_work_dir,
        project=project,
        assets=assets,
        output_paths=output_paths,
        duration_seconds=duration_seconds,
        output_count=normalized_output_count,
        quick_mix_source_count=len(usable_assets),
        detected_take_count=detected_take_count,
    )

    return {
        "source_dir": str(source_dir),
        "work_dir": str(resolved_work_dir),
        "project_name": project.name,
        "pack": project.industry_pack,
        "duration_seconds": duration_seconds,
        "output_count": normalized_output_count,
        "generated_count": len(output_paths),
        "video_count": sum(asset.media_type == MediaType.VIDEO for asset in source_assets),
        "image_count": sum(asset.media_type == MediaType.PHOTO for asset in source_assets),
        "quick_mix_source_count": len(usable_assets),
        "detected_take_count": detected_take_count,
        "photo_support": True,
        "output_paths": [str(path.relative_to(resolved_work_dir)).replace("\\", "/") for path in output_paths],
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
    project = Project(stable_id("project", str(source_dir)), project_name or source_dir.name, source_dir, pack)
    resolved_work_dir = resolve_work_dir(source_dir, work_dir)

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
            ffmpeg_path=ffmpeg_path,
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
        "source_dir": str(source_dir),
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
