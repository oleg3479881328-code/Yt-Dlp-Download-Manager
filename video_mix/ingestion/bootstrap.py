from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from video_mix.core.events import append_event
from video_mix.core.storage import load_assets, load_project
from video_mix.core.store import VideoMixFoundationStore
from video_mix.proxy_pipeline import load_proxy_manifest


def bootstrap_foundation_state(work_dir: Path) -> dict[str, object]:
    work_dir = work_dir.expanduser().resolve()
    project = load_project(work_dir)
    assets = load_assets(work_dir)
    proxy_manifest = load_proxy_manifest(work_dir)
    entries = proxy_manifest.get("entries", {})
    store = VideoMixFoundationStore(work_dir)

    store.upsert_project(
        project_id=project.project_id,
        work_dir=str(work_dir),
        source_root=str(project.root_path.resolve()),
        name=project.name,
        industry_pack=project.industry_pack,
        created_at="",
        updated_at="",
    )

    imported_assets = 0
    imported_proxies = 0

    for asset in assets:
        store.upsert_asset(
            project_id=project.project_id,
            asset_id=asset.asset_id,
            original_path=str(asset.path.resolve()),
            media_type=asset.media_type.value,
            duration_ms=asset.duration_ms,
            width=asset.width,
            height=asset.height,
            fps=asset.fps,
            orientation=asset.orientation.value,
            has_audio=asset.has_audio,
            probe_status=asset.probe_status,
            quality_score=asset.quality_score,
            metadata_json=asset.metadata,
            created_at="",
            updated_at="",
        )
        imported_assets += 1
        append_event(
            store,
            project_id=project.project_id,
            entity_type="asset",
            entity_id=asset.asset_id,
            event_type="asset.registered",
            payload={"original_path": str(asset.path.resolve())},
        )
        proxy_entry = entries.get(asset.asset_id)
        if proxy_entry:
            store.upsert_proxy(
                project_id=project.project_id,
                asset_id=asset.asset_id,
                status=str(proxy_entry.get("status") or "missing"),
                proxy_path=str(proxy_entry.get("proxy_path") or ""),
                source_fingerprint=str(proxy_entry.get("source_fingerprint") or ""),
                profile_fingerprint=str(proxy_entry.get("profile_fingerprint") or ""),
                original_duration_ms=int(proxy_entry.get("original_duration_ms") or 0),
                proxy_duration_ms=int(proxy_entry.get("proxy_duration_ms") or 0),
                original_width=int(proxy_entry.get("original_width") or 0),
                original_height=int(proxy_entry.get("original_height") or 0),
                proxy_width=int(proxy_entry.get("proxy_width") or 0),
                proxy_height=int(proxy_entry.get("proxy_height") or 0),
                error=str(proxy_entry.get("error") or ""),
                has_audio=bool(proxy_entry.get("has_audio")),
                created_at=str(proxy_entry.get("created_at") or ""),
                updated_at=str(proxy_entry.get("updated_at") or ""),
            )
            imported_proxies += 1

    append_event(
        store,
        project_id=project.project_id,
        entity_type="project",
        entity_id=project.project_id,
        event_type="project.registered",
        payload={
            "work_dir": str(work_dir),
            "source_root": str(project.root_path.resolve()),
            "bootstrap_id": str(uuid4()),
            "imported_assets": imported_assets,
            "imported_proxies": imported_proxies,
        },
    )
    return {
        "project_id": project.project_id,
        "work_dir": str(work_dir),
        "db_path": str(store.db_path),
        "imported_assets": imported_assets,
        "imported_proxies": imported_proxies,
    }
