from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from app.video_mix_dashboard import resolve_work_dir
from video_mix.core.storage import work_file

DEFAULT_WORK_DIR_CANDIDATES = (
    Path("video_mix_validation") / "work",
    Path("_video_mix_work"),
)


def _normalize_path(value: str | Path | None) -> Path | None:
    if value in {None, ""}:
        return None
    return Path(value).expanduser().resolve()


def detect_work_dir(project_root: Path, requested_work_dir: str | Path | None = None) -> Path | None:
    candidate = _normalize_path(requested_work_dir)
    if candidate is not None:
        return candidate

    for relative in DEFAULT_WORK_DIR_CANDIDATES:
        possible = (project_root / relative).resolve()
        try:
            resolve_work_dir(str(possible))
            return possible
        except Exception:  # noqa: BLE001
            continue
    return None


def _module_check(module_name: str) -> dict[str, Any]:
    try:
        importlib.import_module(module_name)
        return {"ok": True, "detail": f"{module_name} import ok"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": str(exc)}


def _tool_check(tool_name: str) -> dict[str, Any]:
    resolved = shutil.which(tool_name)
    return {
        "ok": resolved is not None,
        "detail": resolved or f"{tool_name} not found in PATH",
    }


def _work_dir_check(work_dir: Path | None) -> dict[str, Any]:
    if work_dir is None:
        return {
            "ok": False,
            "detail": "VIDEO MIX work_dir not found. Run `python -m video_mix.cli plan ... --work-dir ...` first or pass -WorkDir to the launcher.",
            "work_dir": None,
            "review_exists": False,
            "required_files": [],
        }

    try:
        resolved = resolve_work_dir(str(work_dir))
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "detail": str(exc),
            "work_dir": str(work_dir),
            "review_exists": False,
            "required_files": [],
        }

    required_files = [
        "project.json",
        "assets.json",
        "clips.json",
        "candidates.json",
    ]
    review_exists = work_file(resolved, "review.html").exists()
    return {
        "ok": True,
        "detail": "VIDEO MIX work_dir ready",
        "work_dir": str(resolved),
        "review_exists": review_exists,
        "required_files": required_files,
    }


def run_diagnostics(project_root: Path, requested_work_dir: str | Path | None = None) -> dict[str, Any]:
    resolved_project_root = project_root.resolve()
    work_dir = detect_work_dir(resolved_project_root, requested_work_dir)
    work_dir_result = _work_dir_check(work_dir)
    checks = {
        "python": {
            "ok": True,
            "detail": sys.executable,
        },
        "uvicorn": _module_check("uvicorn"),
        "app_import": _module_check("app.main"),
        "ffmpeg": _tool_check("ffmpeg"),
        "ffprobe": _tool_check("ffprobe"),
        "work_dir": work_dir_result,
    }
    ok = all(check["ok"] for check in checks.values() if isinstance(check, dict) and "ok" in check)
    return {
        "ok": ok,
        "project_root": str(resolved_project_root),
        "work_dir": work_dir_result["work_dir"],
        "checks": checks,
    }


def _print_human_readable(result: dict[str, Any]) -> None:
    print("VIDEO MIX dashboard diagnostics")
    print(f"project_root={result['project_root']}")
    print(f"work_dir={result['work_dir'] or 'missing'}")
    print(f"overall={'ok' if result['ok'] else 'failed'}")
    for name, check in result["checks"].items():
        status = "ok" if check["ok"] else "failed"
        print(f"{name}={status} :: {check['detail']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VIDEO MIX dashboard launcher diagnostics")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = run_diagnostics(Path(args.project_root), args.work_dir)
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False))
    else:
        _print_human_readable(result)
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
