from __future__ import annotations

from uuid import uuid4

from ..store.db import VideoMixFoundationStore


def append_event(
    store: VideoMixFoundationStore,
    *,
    project_id: str,
    entity_type: str,
    entity_id: str,
    event_type: str,
    payload: dict,
) -> str:
    event_id = str(uuid4())
    store.append_event(
        project_id=project_id,
        event_id=event_id,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        payload_json=payload,
    )
    return event_id
