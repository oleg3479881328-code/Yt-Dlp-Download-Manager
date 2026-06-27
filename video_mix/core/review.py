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


def _candidate_block(
    candidate: CandidateReel,
    clip_lookup: dict[str, Clip],
    asset_lookup: dict[str, Asset],
    work_dir: Path,
    thumbnail_lookup: dict[str, str],
    thumbnail_warnings: dict[str, str],
) -> str:
    warnings = "<br>".join(escape(item) for item in candidate.warnings) if candidate.warnings else "none"
    rows: list[str] = []
    for timeline_clip in candidate.video_clips:
        clip = clip_lookup[timeline_clip.clip_id]
        asset = asset_lookup[clip.asset_id]
        tags = ", ".join(clip.tags) if clip.tags else "none"
        thumbnail_html = (
            f'<img class="thumb" src="{escape(thumbnail_lookup[clip.clip_id])}" alt="{escape(asset.path.name)} thumbnail">'
            if clip.clip_id in thumbnail_lookup
            else f'<span class="thumb-missing">{escape(thumbnail_warnings.get(clip.clip_id, "thumbnail unavailable"))}</span>'
        )
        rows.append(
            "\n".join(
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
      <div class="candidate-head">
        <div>
          <h2><code>{escape(candidate.candidate_id)}</code></h2>
          <p class="template">template: <code>{escape(candidate.template_id)}</code></p>
        </div>
        <div class="status-block">
          <span class="status status-{escape(candidate.status.value)}">{escape(candidate.status.value)}</span>
          <span class="score">score {candidate.score:.1f}</span>
          <span class="duration">{escape(_format_ms(candidate.duration_ms))}</span>
        </div>
      </div>
      <p class="warnings"><strong>warnings:</strong> {warnings}</p>
      <p class="notes"><strong>review notes:</strong> {escape(candidate.review_notes or 'none')}</p>
      <div class="instructions">
        <strong>approve:</strong> <code>python -m video_mix.cli approve "{escape(work_dir_text)}" {escape(candidate.candidate_id)}</code><br>
        <strong>reject:</strong> <code>python -m video_mix.cli reject "{escape(work_dir_text)}" {escape(candidate.candidate_id)} --note "reason"</code>
      </div>
      <table>
        <thead>
          <tr>
            <th>thumbnail</th>
            <th>clip id</th>
            <th>source file</th>
            <th>source range</th>
            <th>tags</th>
            <th>clip score</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </section>
    """


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
        result = subprocess.run(command, capture_output=True, text=True, check=False)
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
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VIDEO MIX Review</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f1e8;
      --panel: #fffdf8;
      --ink: #1f1f1f;
      --muted: #5f5b52;
      --line: #d8cdb9;
      --accent: #8b5e3c;
      --good: #2f6b45;
      --bad: #8a3030;
      --warn: #8f6a16;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: radial-gradient(circle at top, #fffdf8 0%, var(--bg) 55%, #e7dcc7 100%);
      color: var(--ink);
      line-height: 1.45;
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }}
    .hero, .candidate-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: 0 12px 40px rgba(60, 46, 28, 0.08);
    }}
    .hero {{
      padding: 28px;
      margin-bottom: 24px;
    }}
    .hero h1 {{ margin: 0 0 12px; font-size: 2rem; }}
    .hero p {{ margin: 0 0 10px; color: var(--muted); }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-top: 20px;
    }}
    .summary-card {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: #fffaf1;
    }}
    .summary-card strong {{
      display: block;
      font-size: 1.3rem;
      margin-bottom: 4px;
    }}
    .candidate-card {{
      padding: 22px;
      margin-bottom: 20px;
    }}
    .candidate-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 12px;
    }}
    .candidate-head h2 {{ margin: 0 0 6px; font-size: 1.3rem; }}
    .template, .notes, .warnings {{ margin: 8px 0; color: var(--muted); }}
    .status-block {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .status, .score, .duration {{
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: #fff7ea;
      font-size: 0.95rem;
    }}
    .status-approved, .status-exported {{ color: var(--good); border-color: #b9d4c2; }}
    .status-rejected {{ color: var(--bad); border-color: #dfb5b5; }}
    .status-generated, .status-previewed {{ color: var(--warn); border-color: #dec98c; }}
    .instructions {{
      margin: 14px 0 18px;
      padding: 12px 14px;
      background: #f8f3e8;
      border-radius: 12px;
      border: 1px dashed var(--line);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    th, td {{
      border-top: 1px solid var(--line);
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }}
    .thumb {{
      width: 88px;
      height: 156px;
      object-fit: cover;
      border-radius: 10px;
      border: 1px solid var(--line);
      display: block;
      background: #efe5d5;
    }}
    .thumb-missing {{
      display: inline-block;
      max-width: 120px;
      color: var(--bad);
      font-size: 0.85rem;
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    code {{
      font-family: "Cascadia Code", Consolas, monospace;
      font-size: 0.92em;
      word-break: break-word;
    }}
    @media (max-width: 800px) {{
      .candidate-head {{ flex-direction: column; }}
      .status-block {{ justify-content: flex-start; }}
      table, thead, tbody, tr, th, td {{ display: block; }}
      thead {{ display: none; }}
      td {{
        border-top: none;
        padding: 6px 0;
      }}
      tbody tr {{
        padding: 10px 0;
        border-top: 1px solid var(--line);
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>VIDEO MIX Review</h1>
      <p><strong>project:</strong> {escape(project.name)}</p>
      <p><strong>pack:</strong> {escape(project.industry_pack)}</p>
      <p><strong>work dir:</strong> <code>{escape(str(work_dir))}</code></p>
      <p>Review candidates here, then run the shown <code>approve</code> or <code>reject</code> commands locally before export.</p>
      <div class="summary">
        <div class="summary-card"><strong>{len(candidates)}</strong><span>candidates</span></div>
        <div class="summary-card"><strong>{len(clips)}</strong><span>clips</span></div>
        <div class="summary-card"><strong>{len(assets)}</strong><span>assets</span></div>
      </div>
    </section>
    {candidate_sections}
  </main>
</body>
</html>
"""


def write_review_html(
    project: Project,
    candidates: list[CandidateReel],
    clips: list[Clip],
    assets: list[Asset],
    work_dir: Path,
    ffmpeg_path: str = "ffmpeg",
    regenerate_thumbnails: bool = True,
) -> tuple[Path, int, dict[str, str]]:
    review_path = work_dir / "reports" / "review.html"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    if regenerate_thumbnails:
        thumbnail_lookup, thumbnail_warnings = generate_thumbnails(clips, work_dir, ffmpeg_path=ffmpeg_path)
    else:
        thumbnail_lookup, thumbnail_warnings = collect_existing_thumbnails(clips, work_dir)
    review_path.write_text(
        build_review_html(project, candidates, clips, assets, work_dir, thumbnail_lookup, thumbnail_warnings),
        encoding="utf-8",
    )
    return review_path, len(thumbnail_lookup), thumbnail_warnings
