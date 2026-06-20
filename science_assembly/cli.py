from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from science_assembly.ai.deepseek_provider import DeepSeekProvider
from science_assembly.ai.json_validation import (
    JsonValidationError,
    load_json,
    validate_manual_approvals,
    validate_ranked_candidates,
    validate_source_candidates,
    validate_visual_beats,
    write_json,
)
from science_assembly.ai.offline_demo_provider import OfflineDemoProvider
from science_assembly.ai.provider import AIProvider, AIProviderError
from science_assembly.pipeline.approvals import build_manual_approval_template
from science_assembly.pipeline.source_ledger import build_source_ledger
from science_assembly.pipeline.timeline_builder import build_timeline
from science_assembly.sources.normalizer import flatten_candidates
from science_assembly.sources.pexels import PexelsVideoSearchAdapter, SourceAdapterError as PexelsError

JsonDict = Dict[str, Any]


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except (AIProviderError, JsonValidationError, PexelsError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Science Video Assembly MVP draft CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    beats = sub.add_parser("beats", help="Extract visual beats from a script")
    beats.add_argument("--script", required=True)
    beats.add_argument("--out", required=True)
    beats.add_argument("--project-id", default="science_video_demo_001")
    beats.add_argument("--language", default="ru")
    beats.add_argument("--target-duration-seconds", type=int, default=90)
    beats.add_argument("--offline-demo", action="store_true")
    beats.set_defaults(func=cmd_beats)

    search = sub.add_parser("search", help="Search stock video candidates for visual beats")
    search.add_argument("--beats", required=True)
    search.add_argument("--out", required=True)
    search.add_argument("--per-query", type=int, default=3)
    search.add_argument("--provider", choices=["pexels"], default="pexels")
    search.set_defaults(func=cmd_search)

    rank = sub.add_parser("rank", help="Rank source candidates against visual beats")
    rank.add_argument("--beats", required=True)
    rank.add_argument("--candidates", required=True)
    rank.add_argument("--out", required=True)
    rank.add_argument("--offline-demo", action="store_true")
    rank.set_defaults(func=cmd_rank)

    approve = sub.add_parser("make-approval-template", help="Create manual approval template")
    approve.add_argument("--ranked", required=True)
    approve.add_argument("--out", required=True)
    approve.add_argument("--max-per-beat", type=int, default=3)
    approve.set_defaults(func=cmd_make_approval_template)

    timeline = sub.add_parser("timeline", help="Create timeline and source ledger from approvals")
    timeline.add_argument("--beats", required=True)
    timeline.add_argument("--candidates", required=True)
    timeline.add_argument("--approvals", required=True)
    timeline.add_argument("--out", required=True)
    timeline.add_argument("--title", default="Science video assembly preview")
    timeline.add_argument("--language", default="ru")
    timeline.set_defaults(func=cmd_timeline)

    qa = sub.add_parser("qa", help="Run AI QA review on timeline and source ledger")
    qa.add_argument("--timeline", required=True)
    qa.add_argument("--ledger", required=True)
    qa.add_argument("--out", required=True)
    qa.add_argument("--offline-demo", action="store_true")
    qa.set_defaults(func=cmd_qa)

    return parser


def provider_from_args(args: argparse.Namespace) -> AIProvider:
    if getattr(args, "offline_demo", False):
        return OfflineDemoProvider()
    return DeepSeekProvider.from_env()


def cmd_beats(args: argparse.Namespace) -> None:
    script_text = Path(args.script).read_text(encoding="utf-8")
    provider = provider_from_args(args)
    data = provider.extract_visual_beats(
        script_text=script_text,
        project_id=args.project_id,
        language=args.language,
        target_duration_seconds=args.target_duration_seconds,
    )
    validate_visual_beats(data)
    out_dir = Path(args.out)
    write_json(out_dir / "visual_beats.json", data)
    print(f"Wrote {out_dir / 'visual_beats.json'}")


def cmd_search(args: argparse.Namespace) -> None:
    beats = load_json(args.beats)
    validate_visual_beats(beats)
    project_id = str(beats.get("project_id"))
    adapter = PexelsVideoSearchAdapter()
    groups: List[List[JsonDict]] = []
    for beat_index, beat in enumerate(beats.get("beats", []), start=1):
        groups.append(adapter.search_for_beat(beat=beat, beat_index=beat_index, per_query=args.per_query))
    candidates = flatten_candidates(project_id, groups)
    validate_source_candidates(candidates)
    out_dir = Path(args.out)
    write_json(out_dir / "source_candidates.json", candidates)
    print(f"Wrote {out_dir / 'source_candidates.json'}")


def cmd_rank(args: argparse.Namespace) -> None:
    beats = load_json(args.beats)
    candidates = load_json(args.candidates)
    validate_visual_beats(beats)
    validate_source_candidates(candidates)
    provider = provider_from_args(args)
    ranked = provider.rank_candidates(
        visual_beats=beats,
        source_candidates=candidates,
        project_id=str(beats.get("project_id")),
    )
    validate_ranked_candidates(ranked)
    out_dir = Path(args.out)
    write_json(out_dir / "ranked_candidates.json", ranked)
    print(f"Wrote {out_dir / 'ranked_candidates.json'}")


def cmd_make_approval_template(args: argparse.Namespace) -> None:
    ranked = load_json(args.ranked)
    validate_ranked_candidates(ranked)
    approvals = build_manual_approval_template(ranked, max_per_beat=args.max_per_beat)
    write_json(args.out, approvals)
    print(f"Wrote {args.out}")


def cmd_timeline(args: argparse.Namespace) -> None:
    beats = load_json(args.beats)
    candidates = load_json(args.candidates)
    approvals = load_json(args.approvals)
    validate_visual_beats(beats)
    validate_source_candidates(candidates)
    validate_manual_approvals(approvals)
    timeline = build_timeline(
        visual_beats=beats,
        source_candidates=candidates,
        manual_approvals=approvals,
        title=args.title,
        language=args.language,
    )
    ledger = build_source_ledger(timeline=timeline, source_candidates=candidates)
    out_dir = Path(args.out)
    write_json(out_dir / "timeline.json", timeline)
    write_json(out_dir / "source_ledger.json", ledger)
    print(f"Wrote {out_dir / 'timeline.json'}")
    print(f"Wrote {out_dir / 'source_ledger.json'}")


def cmd_qa(args: argparse.Namespace) -> None:
    timeline = load_json(args.timeline)
    ledger = load_json(args.ledger)
    provider = provider_from_args(args)
    review = provider.qa_review(timeline=timeline, source_ledger=ledger)
    write_json(args.out, review)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    raise SystemExit(main())
