from __future__ import annotations

from pathlib import Path

from .core.asset_scan import SKIP_DIR_NAMES, detect_media_type, scan_project_assets, stable_id
from .core.candidate_builder import build_candidates
from .core.duplicate_detection import apply_duplicate_detection
from .core.media_probe import probe_assets
from .core.models import MediaType, Project
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
)
from .core.tagging import apply_filename_tags
from .packs.wedding import get_wedding_templates


def resolve_source_dir(raw_source_dir: str) -> Path:
    source_dir = Path(raw_source_dir).expanduser().resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"Source folder does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source folder is not a directory: {source_dir}")
    return source_dir


def resolve_work_dir(source_dir: Path, work_dir: str | None = None) -> Path:
    if not work_dir:
        return source_dir / "_video_mix_work"
    raw = Path(work_dir).expanduser()
    return (source_dir / raw).resolve() if not raw.is_absolute() else raw.resolve()


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
):
    fixed = FixedIntervalSegmenter(clip_ms=clip_ms, max_clips_per_asset=max_clips_per_asset)
    if prefer_pyscenedetect:
        return [PySceneDetectSegmenter(scenedetect_path), fixed]
    return [fixed]


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
