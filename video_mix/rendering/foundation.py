from __future__ import annotations

from pathlib import Path
from typing import Any

from video_mix.core.storage import load_assets
from video_mix.service import _render_quick_mix_output, _render_quick_mix_segment


def render_foundation_outputs(
    *,
    work_dir: Path,
    generation_id: str,
    selected_plans: list[dict[str, Any]],
    ffmpeg_path: str = "ffmpeg",
    music_paths: list[str] | None = None,
    music_start_ms_values: list[int] | None = None,
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

    for index, plan in enumerate(selected_plans, start=1):
        part_paths: list[Path] = []
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
                "cover_source": "",
                "metadata": {
                    "generation_id": generation_id,
                    "plan_id": plan["plan_id"],
                },
                "plan": plan,
            }
        )
    return output_rows
