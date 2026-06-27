from __future__ import annotations

import argparse
from pathlib import Path

from .core.export_plan import export_candidate
from .core.models import CandidateStatus
from .core.review import write_review_html
from .core.storage import (
    build_summary,
    load_assets,
    load_candidates,
    load_clips,
    load_project,
    save_candidates,
    save_summary,
)
from .service import plan_source_materials


def run_plan(args: argparse.Namespace) -> None:
    result = plan_source_materials(
        args.project_folder,
        project_name=args.project_name,
        pack=args.pack,
        work_dir=args.work_dir,
        ffprobe_path=args.ffprobe,
        scenedetect_path=args.scenedetect,
        prefer_pyscenedetect=args.prefer_pyscenedetect,
        clip_ms=args.clip_ms,
        max_clips_per_asset=args.max_clips_per_asset,
        max_candidates=args.max_candidates,
    )
    print(f"project={result['project_name']}")
    print(f"assets={result['asset_count']}")
    print(f"clips={result['clip_count']}")
    print(f"candidates={result['candidate_count']}")
    print(f"work_dir={result['work_dir']}")


def update_candidate_status(work_dir: Path, candidate_id: str, status: CandidateStatus, note: str = "") -> None:
    candidates = load_candidates(work_dir)
    target = next((candidate for candidate in candidates if candidate.candidate_id == candidate_id), None)
    if target is None:
        raise ValueError(f"Candidate not found: {candidate_id}")
    target.status = status
    target.review_notes = note
    save_candidates(work_dir, candidates)
    project = load_project(work_dir)
    save_summary(work_dir, build_summary(project, load_assets(work_dir), load_clips(work_dir), candidates))
    print(f"{status.value}={candidate_id}")


def run_approve(args: argparse.Namespace) -> None:
    update_candidate_status(Path(args.work_dir).resolve(), args.candidate_id, CandidateStatus.APPROVED, args.note)


def run_reject(args: argparse.Namespace) -> None:
    update_candidate_status(Path(args.work_dir).resolve(), args.candidate_id, CandidateStatus.REJECTED, args.note)


def run_export(args: argparse.Namespace) -> None:
    work_dir = Path(args.work_dir).resolve()
    project = load_project(work_dir)
    clips = load_clips(work_dir)
    candidates = load_candidates(work_dir)

    approved = [candidate for candidate in candidates if candidate.status == CandidateStatus.APPROVED]
    if not approved:
        raise ValueError("No approved candidates found. Run approve first.")

    exported = 0
    for candidate in approved:
        plan = export_candidate(
            project_name=project.name,
            pack_id=project.industry_pack,
            candidate=candidate,
            clips=clips,
            work_dir=work_dir,
            ffmpeg_path=args.ffmpeg,
        )
        candidate.status = CandidateStatus.EXPORTED
        candidate.review_notes = f"{candidate.review_notes}\nexported:{plan.output_path.name}".strip()
        print(f"exported={plan.output_path}")
        exported += 1

    save_candidates(work_dir, candidates)
    save_summary(work_dir, build_summary(project, load_assets(work_dir), clips, candidates))
    print(f"exported_count={exported}")


def run_review(args: argparse.Namespace) -> None:
    work_dir = Path(args.work_dir).resolve()
    project = load_project(work_dir)
    assets = load_assets(work_dir)
    clips = load_clips(work_dir)
    candidates = load_candidates(work_dir)
    review_path, thumbnail_count, thumbnail_warnings = write_review_html(
        project,
        candidates,
        clips,
        assets,
        work_dir,
        ffmpeg_path=args.ffmpeg,
    )
    print(f"review={review_path}")
    print(f"candidates={len(candidates)}")
    print(f"thumbnails={thumbnail_count}")
    if thumbnail_warnings:
        print(f"thumbnail_warnings={len(thumbnail_warnings)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VIDEO MIX Stage 1 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="Scan, probe, segment and build candidate manifests")
    plan.add_argument("project_folder")
    plan.add_argument("--project-name", default=None)
    plan.add_argument("--pack", default="wedding")
    plan.add_argument("--work-dir", default=None)
    plan.add_argument("--ffprobe", default="ffprobe")
    plan.add_argument("--scenedetect", default="scenedetect")
    plan.add_argument("--prefer-pyscenedetect", action="store_true")
    plan.add_argument("--clip-ms", type=int, default=3000)
    plan.add_argument("--max-clips-per-asset", type=int, default=12)
    plan.add_argument("--max-candidates", type=int, default=10)
    plan.set_defaults(func=run_plan)

    approve = sub.add_parser("approve", help="Approve a generated candidate")
    approve.add_argument("work_dir")
    approve.add_argument("candidate_id")
    approve.add_argument("--note", default="")
    approve.set_defaults(func=run_approve)

    reject = sub.add_parser("reject", help="Reject a generated candidate")
    reject.add_argument("work_dir")
    reject.add_argument("candidate_id")
    reject.add_argument("--note", default="")
    reject.set_defaults(func=run_reject)

    review = sub.add_parser("review", help="Generate a local static review artifact")
    review.add_argument("work_dir")
    review.add_argument("--ffmpeg", default="ffmpeg")
    review.set_defaults(func=run_review)

    export = sub.add_parser("export", help="Export approved candidates to MP4")
    export.add_argument("work_dir")
    export.add_argument("--ffmpeg", default="ffmpeg")
    export.set_defaults(func=run_export)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
