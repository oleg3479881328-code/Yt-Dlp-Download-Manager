from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from video_mix.core.schemas import validate_schema_document

PACKAGE_SCHEMA_VERSION = "publishing-package/v1"


def _default_caption(index: int) -> str:
    return f"Reel {index:02d}\nСвадебный вертикальный монтаж. Отредактируйте текст перед публикацией."


def _default_hashtags() -> str:
    return "#wedding #reels #videomix #highlight"


def build_publishing_package(
    *,
    work_dir: Path,
    generation_id: str,
    outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    resolved_work_dir = work_dir.expanduser().resolve()
    package_dir = resolved_work_dir / "publishing" / f"five_reels_{generation_id}"
    package_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []

    for index, output in enumerate(outputs, start=1):
        source_output = (resolved_work_dir / str(output["output_path"])).resolve()
        if not source_output.exists():
            continue
        mp4_name = f"reel_{index:02d}.mp4"
        cover_name = f"cover_{index:02d}.jpg"
        caption_name = f"caption_{index:02d}.txt"
        hashtags_name = f"hashtags_{index:02d}.txt"
        metadata_name = f"metadata_{index:02d}.json"
        plan_name = f"render_plan_{index:02d}.json"
        quality_name = f"quality_report_{index:02d}.json"

        target_mp4 = package_dir / mp4_name
        shutil.copy2(source_output, target_mp4)

        cover_path = package_dir / cover_name
        source_cover = output.get("cover_source")
        if source_cover:
            source_cover_path = (resolved_work_dir / str(source_cover)).resolve()
            if source_cover_path.exists():
                shutil.copy2(source_cover_path, cover_path)
            else:
                cover_path.write_bytes(b"")
        else:
            cover_path.write_bytes(b"")

        (package_dir / caption_name).write_text(_default_caption(index), encoding="utf-8")
        (package_dir / hashtags_name).write_text(_default_hashtags(), encoding="utf-8")
        (package_dir / metadata_name).write_text(json.dumps(output.get("metadata", {}), ensure_ascii=False, indent=2), encoding="utf-8")
        (package_dir / plan_name).write_text(json.dumps(output.get("plan", {}), ensure_ascii=False, indent=2), encoding="utf-8")
        (package_dir / quality_name).write_text(json.dumps(output.get("quality_report", {}), ensure_ascii=False, indent=2), encoding="utf-8")

        items.append(
            {
                "index": index,
                "mp4": mp4_name,
                "cover": cover_name,
                "caption": caption_name,
                "hashtags": hashtags_name,
                "metadata": metadata_name,
                "render_plan": plan_name,
                "quality_report": quality_name,
            }
        )

    package_payload = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "generation_id": generation_id,
        "items": items,
    }
    validate_schema_document("publishing_package", package_payload)
    (package_dir / "publishing_package.json").write_text(json.dumps(package_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (package_dir / "README.txt").write_text(
        "Локальный publishing package для пяти роликов.\n"
        "Внутри лежат MP4, cover, caption, hashtags, metadata, render plan и quality report.\n",
        encoding="utf-8",
    )
    return {
        "package_dir": str(package_dir),
        "relative_package_dir": str(package_dir.relative_to(resolved_work_dir)).replace("\\", "/"),
        "items": items,
        "package_manifest_path": str((package_dir / "publishing_package.json").relative_to(resolved_work_dir)).replace("\\", "/"),
    }
