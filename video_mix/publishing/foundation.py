from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from video_mix.core.schemas import validate_schema_document

PACKAGE_SCHEMA_VERSION = "publishing-package/v1"
MINIMAL_VALID_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb0043000201010101010201010102020202020403020202020504040304060506060605060606070908060709070606080b08090a0a0a0a0a06080b0c0b0a0c090a0a0affc00011080001000103012200021101031101ffc4001b0000010501010101010100000000000000000102030405060708090affc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffc4001f0100030101010101010101010000000000000102030405060708090affc400b51100020102040403040705040400010277000102031104052131061241510761711322328108144291a1b1c109233352f0156272d10a162434e125f11718191a262728292a35363738393a434445464748494a535455565758595a636465666768696a737475767778797a82838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9faffda000c03010002110311003f00f7fa28a2803fffd9"
)


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
                cover_path.write_bytes(MINIMAL_VALID_JPEG)
        else:
            cover_path.write_bytes(MINIMAL_VALID_JPEG)

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
