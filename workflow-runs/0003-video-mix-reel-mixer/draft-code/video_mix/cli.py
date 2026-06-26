"""Draft CLI for VIDEO MIX. Not wired into the app."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .core.asset_scan import scan_project_assets, stable_id
from .core.candidate_builder import build_candidates
from .core.duplicate_detection import apply_duplicate_detection
from .core.media_probe import probe_assets
from .core.models import Project
from .core.scoring import score_assets, score_clips
from .core.segmenters import FixedIntervalSegmenter, PySceneDetectSegmenter, plan_segments_for_assets
from .core.tagging import apply_filename_tags
from .packs.wedding import get_wedding_templates


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "value"):
        return value.value
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), indent=2, ensure_ascii=False), encoding="utf-8")


def build_segmenters(args: argparse.Namespace):
    fixed = FixedIntervalSegmenter(clip_ms=args.clip_ms, max_clips_per_asset=args.max_clips_per_asset)
    if args.prefer_pyscenedetect:
        return [PySceneDetectSegmenter(args.scenedetect), fixed]
    return [fixed]


def run_plan(args: argparse.Namespace) -> None:
    root = Path(args.project_folder).resolve()
    project = Project(stable_id("project", str(root)), args.project_name or root.name, root, args.pack)
    work_dir = Path(args.work_dir).resolve() if args.work_dir else root / "_video_mix_work"
    reports_dir = work_dir / "reports"

    assets = score_assets(probe_assets(scan_project_assets(project), ffprobe_path=args.ffprobe))
    clips = plan_segments_for_assets(assets, work_dir / "clips", segmenters=build_segmenters(args))
    clips = apply_filename_tags(clips)
    clips = apply_duplicate_detection(clips)
    clips = score_clips(clips, assets)

    templates = get_wedding_templates()
    candidates = build_candidates(project.project_id, args.pack, templates, clips, args.max_candidates)

    write_json(reports_dir / "project.json", project)
    write_json(reports_dir / "assets.json", assets)
    write_json(reports_dir / "clips.json", clips)
    write_json(reports_dir / "candidates.json", candidates)

    print(f"assets={len(assets)} clips={len(clips)} candidates={len(candidates)}")
    print(f"reports={reports_dir}")
    print("Draft planning only. No active app integration and no validated export.")


def main() -> None:
    parser = argparse.ArgumentParser(description="VIDEO MIX draft CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("project_folder")
    plan.add_argument("--project-name", default=None)
    plan.add_argument("--pack", default="wedding")
    plan.add_argument("--work-dir", default=None)
    plan.add_argument("--ffprobe", default="ffprobe")
    plan.add_argument("--scenedetect", default="scenedetect")
    plan.add_argument("--prefer-pyscenedetect", action="store_true")
    plan.add_argument("--clip-ms", type=int, default=3000)
    plan.add_argument("--max-clips-per-asset", type=int, default=12)
    plan.add_argument("--max-candidates", type=int, default=20)
    plan.set_defaults(func=run_plan)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
