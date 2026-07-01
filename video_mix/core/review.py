from __future__ import annotations

import subprocess
from html import escape
from pathlib import Path

from .models import Asset, CandidateReel, Clip, Project


def _format_ms(value: int) -> str:
    total_seconds = max(0, value) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def build_thumbnail_command(clip: Clip, output_path: Path, ffmpeg_path: str = "ffmpeg") -> list[str]:
    midpoint_seconds = (clip.source_start_ms + max(500, clip.duration_ms // 2)) / 1000
    return [
        ffmpeg_path,
        "-y",
        "-ss",
        f"{midpoint_seconds:.3f}",
        "-i",
        str(clip.source_path),
        "-frames:v",
        "1",
        "-vf",
        "scale=320:-2",
        str(output_path),
    ]


def generate_thumbnails(clips: list[Clip], work_dir: Path, ffmpeg_path: str = "ffmpeg") -> tuple[dict[str, str], dict[str, str]]:
    thumbnails_dir = work_dir / "reports" / "thumbnails"
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_lookup: dict[str, str] = {}
    thumbnail_warnings: dict[str, str] = {}

    for clip in clips:
        output_path = thumbnails_dir / f"{clip.clip_id}.jpg"
        command = build_thumbnail_command(clip, output_path, ffmpeg_path=ffmpeg_path)
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            thumbnail_warnings[clip.clip_id] = f"ffmpeg not found: {ffmpeg_path}"
            continue
        if result.returncode == 0 and output_path.exists():
            thumbnail_lookup[clip.clip_id] = f"thumbnails/{output_path.name}"
        else:
            message = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "thumbnail generation failed"
            thumbnail_warnings[clip.clip_id] = message

    return thumbnail_lookup, thumbnail_warnings


def collect_existing_thumbnails(clips: list[Clip], work_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    thumbnails_dir = work_dir / "reports" / "thumbnails"
    thumbnail_lookup: dict[str, str] = {}
    thumbnail_warnings: dict[str, str] = {}

    for clip in clips:
        output_path = thumbnails_dir / f"{clip.clip_id}.jpg"
        if output_path.exists():
            thumbnail_lookup[clip.clip_id] = f"thumbnails/{output_path.name}"
        else:
            thumbnail_warnings[clip.clip_id] = "thumbnail unavailable"

    return thumbnail_lookup, thumbnail_warnings


def _candidate_block(
    candidate: CandidateReel,
    clip_lookup: dict[str, Clip],
    asset_lookup: dict[str, Asset],
    work_dir: Path,
    thumbnail_lookup: dict[str, str],
    thumbnail_warnings: dict[str, str],
) -> str:
    rows: list[str] = []
    warnings = "<br>".join(escape(item) for item in candidate.warnings) if candidate.warnings else "none"
    for timeline_clip in candidate.video_clips:
        clip = clip_lookup[timeline_clip.clip_id]
        asset = asset_lookup[clip.asset_id]
        tags = ", ".join(clip.tags) if clip.tags else "none"
        if clip.clip_id in thumbnail_lookup:
            thumbnail_html = f'<img class="thumb" src="{escape(thumbnail_lookup[clip.clip_id])}" alt="thumbnail">'
        else:
            warning = thumbnail_warnings.get(clip.clip_id, "thumbnail unavailable")
            thumbnail_html = f'<span class="thumb-missing">{escape(warning)}</span>'
        rows.append(
            "".join(
                [
                    "<tr>",
                    f"<td>{thumbnail_html}</td>",
                    f"<td><code>{escape(clip.clip_id)}</code></td>",
                    f"<td>{escape(asset.path.name)}</td>",
                    f"<td>{escape(_format_ms(timeline_clip.source_start_ms))} - {escape(_format_ms(timeline_clip.source_end_ms))}</td>",
                    f"<td>{escape(tags)}</td>",
                    f"<td>{clip.quality_score:.1f}</td>",
                    "</tr>",
                ]
            )
        )

    work_dir_text = str(work_dir)
    return f"""
    <section class="candidate-card">
      <h2><code>{escape(candidate.candidate_id)}</code></h2>
      <p class="template">template: <code>{escape(candidate.template_id)}</code></p>
      <p>status: <strong>{escape(candidate.status.value)}</strong> · score {candidate.score:.1f} · {escape(_format_ms(candidate.duration_ms))}</p>
      <p class="warnings"><strong>warnings:</strong> {warnings}</p>
      <p class="notes"><strong>review notes:</strong> {escape(candidate.review_notes or 'none')}</p>
      <p><strong>approve:</strong> <code>python -m video_mix.cli approve "{escape(work_dir_text)}" {escape(candidate.candidate_id)}</code></p>
      <p><strong>reject:</strong> <code>python -m video_mix.cli reject "{escape(work_dir_text)}" {escape(candidate.candidate_id)} --note "reason"</code></p>
      <table>
        <thead><tr><th>thumbnail</th><th>clip id</th><th>source file</th><th>source range</th><th>tags</th><th>clip score</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
    """


def build_review_html(
    project: Project,
    candidates: list[CandidateReel],
    clips: list[Clip],
    assets: list[Asset],
    work_dir: Path,
    thumbnail_lookup: dict[str, str] | None = None,
    thumbnail_warnings: dict[str, str] | None = None,
) -> str:
    clip_lookup = {clip.clip_id: clip for clip in clips}
    asset_lookup = {asset.asset_id: asset for asset in assets}
    thumbnails = thumbnail_lookup or {}
    thumb_warnings = thumbnail_warnings or {}
    candidate_sections = "".join(
        _candidate_block(candidate, clip_lookup, asset_lookup, work_dir, thumbnails, thumb_warnings)
        for candidate in candidates
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>VIDEO MIX Review</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 32px; background: #f5f1e8; color: #241b10; }}
    .candidate-card {{ background: #fffaf0; border: 1px solid #dacfb8; border-radius: 16px; padding: 20px; margin-bottom: 18px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #dacfb8; text-align: left; padding: 8px; vertical-align: middle; }}
    .thumb {{ width: 96px; max-height: 72px; object-fit: cover; }}
    .thumb-missing {{ color: #6f604d; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>VIDEO MIX Review</h1>
  <p>project: <strong>{escape(project.name)}</strong> · pack: <code>{escape(project.industry_pack)}</code> · root: <code>{escape(str(project.root_path))}</code></p>
  {candidate_sections}
</body>
</html>
"""


def write_review_html(
    project: Project,
    candidates: list[CandidateReel],
    clips: list[Clip],
    assets: list[Asset],
    work_dir: Path,
    *,
    ffmpeg_path: str = "ffmpeg",
) -> tuple[Path, int, dict[str, str]]:
    thumbnail_lookup, thumbnail_warnings = generate_thumbnails(clips, work_dir, ffmpeg_path=ffmpeg_path)
    html = build_review_html(project, candidates, clips, assets, work_dir, thumbnail_lookup, thumbnail_warnings)
    report_path = work_dir / "reports" / "review.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html, encoding="utf-8")
    return report_path, len(thumbnail_lookup), thumbnail_warnings
