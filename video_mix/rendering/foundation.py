from __future__ import annotations

from pathlib import Path
from typing import Any

from video_mix.core.asset_scan import stable_id
from video_mix.core.media_probe import probe_assets
from video_mix.core.models import Asset, MediaType, Orientation
from video_mix.core.storage import load_assets
from video_mix.service import _pinned_segment_ms, _render_quick_mix_output, _render_quick_mix_segment


def _build_optional_media_asset(path: Path, ffprobe_path: str) -> Asset:
    suffix = path.suffix.lower()
    media_type = MediaType.PHOTO if suffix in {".jpg", ".jpeg", ".png", ".webp"} else MediaType.VIDEO
    asset = Asset(
        asset_id=stable_id("optional_media", str(path.resolve())),
        project_id="foundation_optional_media",
        path=path.resolve(),
        media_type=media_type,
        orientation=Orientation.UNKNOWN,
    )
    return probe_assets([asset], ffprobe_path=ffprobe_path)[0]


def render_foundation_outputs(
    *,
    work_dir: Path,
    generation_id: str,
    selected_plans: list[dict[str, Any]],
    ffmpeg_path: str = "ffmpeg",
    ffprobe_path: str = "ffprobe",
    music_paths: list[str] | None = None,
    music_start_ms_values: list[int] | None = None,
    opening_media_paths: list[str] | None = None,
    closing_media_paths: list[str] | None = None,
    use_closing_duration: bool = False,
) -> list[dict[str, Any]]:
    resolved_work_dir = work_dir.expanduser().resolve()
    assets = load_assets(resolved_work_dir)
    asset_lookup = {asset.asset_id: asset for asset in assets}
    generation_dir = resolved_work_dir / "foundation_generations" / generation_id
    exports_dir = generation_dir / "exports"
    segments_dir = generation_dir / "segments"
    exports_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)
    output_rows: list[dict[str, Any]] = []
    opening_assets = [_build_optional_media_asset(Path(path), ffprobe_path) for path in (opening_media_paths or []) if Path(path).exists()]
    closing_assets = [_build_optional_media_asset(Path(path), ffprobe_path) for path in (closing_media_paths or []) if Path(path).exists()]

    for index, plan in enumerate(selected_plans, start=1):
        part_paths: list[Path] = []
        cover_source = ""
        requested_duration_ms = int(plan.get("requested_duration_ms") or 0)
        if opening_assets:
            opening_asset = opening_assets[(index - 1) % len(opening_assets)]
            opening_duration_ms = _pinned_segment_ms(opening_asset, requested_duration_ms or 2000)
            if opening_duration_ms > 0:
                opening_path = segments_dir / f"{plan['plan_id']}_opening.mp4"
                _render_quick_mix_segment(
                    opening_asset,
                    opening_path,
                    start_ms=0,
                    duration_ms=opening_duration_ms,
                    ffmpeg_path=ffmpeg_path,
                )
                part_paths.append(opening_path)
        for item_index, item in enumerate(plan.get("items", []), start=1):
            asset = asset_lookup.get(str(item.get("asset_id") or ""))
            if asset is None:
                continue
            segment_path = segments_dir / f"{plan['plan_id']}_seg_{item_index:02d}.mp4"
            source_start_ms = int(item["source_start_ms"])
            source_end_ms = int(item["source_end_ms"])
            _render_quick_mix_segment(
                asset,
                segment_path,
                start_ms=source_start_ms,
                duration_ms=max(source_end_ms - source_start_ms, 0),
                ffmpeg_path=ffmpeg_path,
            )
            part_paths.append(segment_path)
            if not cover_source:
                cover_source = str((item.get("metadata_json") or {}).get("keyframe_path") or "")
        if closing_assets:
            closing_asset = closing_assets[(index - 1) % len(closing_assets)]
            if use_closing_duration:
                closing_duration_ms = _pinned_segment_ms(closing_asset, closing_asset.duration_ms or requested_duration_ms or 2000, use_full_duration=True)
            else:
                closing_duration_ms = _pinned_segment_ms(closing_asset, requested_duration_ms or 2000)
            if closing_duration_ms > 0:
                closing_path = segments_dir / f"{plan['plan_id']}_closing.mp4"
                closing_start_ms = 0
                if closing_asset.media_type == MediaType.VIDEO and closing_asset.duration_ms and use_closing_duration:
                    closing_start_ms = max(0, closing_asset.duration_ms - closing_duration_ms)
                _render_quick_mix_segment(
                    closing_asset,
                    closing_path,
                    start_ms=closing_start_ms,
                    duration_ms=closing_duration_ms,
                    ffmpeg_path=ffmpeg_path,
                )
                part_paths.append(closing_path)
        output_path = exports_dir / f"reel_{index:02d}.mp4"
        music_path = None
        music_start_ms = 0
        if music_paths:
            music_path = Path(music_paths[(index - 1) % len(music_paths)])
            music_start_ms = int((music_start_ms_values or [0])[(index - 1) % len(music_paths)])
        _render_quick_mix_output(
            part_paths,
            output_path,
            ffmpeg_path,
            music_path=music_path,
            music_start_ms=music_start_ms,
        )
        output_rows.append(
            {
                "plan_id": plan["plan_id"],
                "output_index": index,
                "output_path": str(output_path.relative_to(resolved_work_dir)).replace("\\", "/"),
                "absolute_output_path": str(output_path),
                "cover_source": cover_source,
                "metadata": {
                    "generation_id": generation_id,
                    "plan_id": plan["plan_id"],
                },
                "plan": plan,
            }
        )
    return output_rows
