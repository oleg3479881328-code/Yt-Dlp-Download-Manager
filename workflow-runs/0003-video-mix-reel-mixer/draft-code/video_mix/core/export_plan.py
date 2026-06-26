"""Draft export planning for VIDEO MIX.

Creates export plans and ffmpeg concat commands from timeline-like manifests.
Still draft only. Codex must validate locally before claiming export works.
"""

from __future__ import annotations

from pathlib import Path

from .models import CandidateReel, Clip, ExportPlan


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
    """Create an ffmpeg concat list for a candidate.

    Draft assumes micro-clips already exist at clip.working_path.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    concat_path = work_dir / f"{candidate.candidate_id}_concat.txt"

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
