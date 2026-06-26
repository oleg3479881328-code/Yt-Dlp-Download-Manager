from __future__ import annotations

import subprocess
from pathlib import Path

from .models import CandidateReel, Clip, ExportPlan
from .segmenters import extract_clip


def build_export_plan(project_name: str, pack_id: str, template_id: str, candidate: CandidateReel, export_dir: Path) -> ExportPlan:
    safe_project = project_name.lower().replace(" ", "_")
    filename = f"{safe_project}_{pack_id}_{template_id}_{candidate.candidate_id}.mp4"
    preset = candidate.platform_preset
    return ExportPlan(
        candidate_id=candidate.candidate_id,
        output_path=export_dir / filename,
        width=preset.width,
        height=preset.height,
        fps=preset.fps,
        format=preset.format,
        renderer="ffmpeg",
    )


def build_concat_file(candidate: CandidateReel, clip_lookup: dict[str, Clip], work_dir: Path) -> Path:
    concat_dir = work_dir / "concat"
    concat_dir.mkdir(parents=True, exist_ok=True)
    concat_path = concat_dir / f"{candidate.candidate_id}.txt"
    lines: list[str] = []
    for timeline_clip in candidate.video_clips:
        clip = clip_lookup[timeline_clip.clip_id]
        if clip.working_path is None:
            raise ValueError(f"Clip has no working_path: {clip.clip_id}")
        lines.append(f"file '{clip.working_path.as_posix()}'")
    concat_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return concat_path


def build_ffmpeg_export_command(concat_path: Path, export_plan: ExportPlan, ffmpeg_path: str = "ffmpeg") -> list[str]:
    export_plan.output_path.parent.mkdir(parents=True, exist_ok=True)
    return [
        ffmpeg_path,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-vf",
        f"scale={export_plan.width}:{export_plan.height}:force_original_aspect_ratio=increase,crop={export_plan.width}:{export_plan.height}",
        "-r",
        str(export_plan.fps),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-shortest",
        str(export_plan.output_path),
    ]


def export_candidate(project_name: str, pack_id: str, candidate: CandidateReel, clips: list[Clip], work_dir: Path, ffmpeg_path: str = "ffmpeg") -> ExportPlan:
    clip_lookup = {clip.clip_id: clip for clip in clips}
    for timeline_clip in candidate.video_clips:
        extract_clip(clip_lookup[timeline_clip.clip_id], ffmpeg_path=ffmpeg_path)

    export_plan = build_export_plan(project_name, pack_id, candidate.template_id, candidate, work_dir / "exports")
    concat_path = build_concat_file(candidate, clip_lookup, work_dir)
    command = build_ffmpeg_export_command(concat_path, export_plan, ffmpeg_path=ffmpeg_path)
    subprocess.run(command, check=True)
    return export_plan
