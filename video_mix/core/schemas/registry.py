from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SchemaDescriptor:
    name: str
    version: str


schema_registry: dict[str, SchemaDescriptor] = {
    "proxy_manifest": SchemaDescriptor(name="proxy_manifest", version="video-proxy-v1"),
    "scene_manifest": SchemaDescriptor(name="scene_manifest", version="scene-manifest/v1"),
    "edit_plan": SchemaDescriptor(name="edit_plan", version="edit-plan/v1"),
    "quality_report": SchemaDescriptor(name="quality_report", version="quality-report/v1"),
    "publishing_package": SchemaDescriptor(name="publishing_package", version="publishing-package/v1"),
}


def validate_schema_document(schema_name: str, payload: dict[str, Any]) -> None:
    descriptor = schema_registry.get(schema_name)
    if descriptor is None:
        raise ValueError(f"Unsupported schema name: {schema_name}")
    schema_version = str(payload.get("schema_version") or "")
    if schema_version != descriptor.version:
        raise ValueError(
            f"Unsupported {schema_name} schema version: {schema_version or '<missing>'}; expected {descriptor.version}"
        )
