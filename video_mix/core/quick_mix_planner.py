from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

QUICK_MIX_UNIQUE_MATERIAL_EXHAUSTED = "quick_mix_unique_material_exhausted"
QUICK_MIX_SOURCE_GROUP_RELAXED = "quick_mix_source_group_relaxed"
QUICK_MIX_ASSET_REPEAT_RELAXED = "quick_mix_asset_repeat_relaxed"
QUICK_MIX_ATOMIC_TAKE_EXHAUSTED = "quick_mix_atomic_take_exhausted"
WHATSAPP_DUPLICATE_SUFFIX_RE = re.compile(r"\s+\(\d+\)$")


@dataclass(frozen=True, slots=True)
class QuickMixSource:
    source_id: str
    path: Path
    media_type: str
    duration_ms: int | None = None
    source_start_ms: int = 0
    base_source_id: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def source_group(self) -> str:
        return normalize_quick_mix_source_group(self.path)

    @property
    def unique_base_id(self) -> str:
        return self.base_source_id or self.source_id

    @property
    def material_identity(self) -> str:
        content_identity = str(
            self.metadata.get("content_identity")
            or self.metadata.get("composite_signature")
            or ""
        ).strip()
        return content_identity or self.unique_base_id


@dataclass(frozen=True, slots=True)
class QuickMixSegmentPlan:
    output_index: int
    step_index: int
    source_id: str
    base_source_id: str
    source_path: str
    source_basename: str
    normalized_source_group: str
    media_type: str
    source_start_ms: int
    source_end_ms: int
    relative_source_start_ms: int
    duration_ms: int
    warnings: list[dict] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class QuickMixOutputPlan:
    output_index: int
    target_duration_ms: int
    planned_duration_ms: int
    segments: list[QuickMixSegmentPlan]
    warnings: list[dict] = field(default_factory=list)


def normalize_quick_mix_source_group(path: Path | str) -> str:
    """Collapse common duplicate-export filename variants into one source group.

    A typical WhatsApp export can produce siblings like:
    `WhatsApp Video ... PM.mp4`, `WhatsApp Video ... PM (1).mp4`,
    `WhatsApp Video ... PM (2).mp4`.

    The Quick Mix planner treats these as the same source group so a single
    output does not silently include multiple copies of the same visual scene.
    """

    normalized_path = Path(path)
    stem = WHATSAPP_DUPLICATE_SUFFIX_RE.sub("", normalized_path.stem).strip().casefold()
    return f"{stem}{normalized_path.suffix.lower()}"


def preferred_quick_mix_segment_ms(source: QuickMixSource, remaining_ms: int) -> int:
    if bool(source.metadata.get("atomic_take")):
        atomic_duration_ms = int(source.metadata.get("atomic_duration_ms") or source.duration_ms or 0)
        if atomic_duration_ms <= 0 or remaining_ms < atomic_duration_ms:
            return 0
        return atomic_duration_ms
    if source.media_type == "photo":
        return min(remaining_ms, 2000 if remaining_ms > 2000 else remaining_ms)
    if not source.duration_ms:
        return min(remaining_ms, 2000)
    return min(remaining_ms, min(3000, source.duration_ms))


def build_quick_mix_plan(
    sources: list[QuickMixSource],
    *,
    target_duration_ms: int,
    output_count: int,
) -> tuple[list[QuickMixOutputPlan], list[dict]]:
    if target_duration_ms <= 0:
        raise ValueError("target_duration_ms must be greater than zero")
    if output_count <= 0:
        raise ValueError("output_count must be greater than zero")
    if not sources:
        raise ValueError("At least one Quick Mix source is required")

    source_cursor = 0
    source_offsets: dict[str, int] = {}
    output_plans: list[QuickMixOutputPlan] = []
    all_warnings: list[dict] = []

    for output_index in range(1, output_count + 1):
        remaining_ms = target_duration_ms
        step_index = 1
        segments: list[QuickMixSegmentPlan] = []
        output_warnings: list[dict] = []
        used_material_ids: set[str] = set()
        used_source_groups: set[str] = set()

        while remaining_ms > 0:
            source, source_cursor, selection_warning = choose_quick_mix_source(
                sources,
                source_cursor,
                used_material_ids=used_material_ids,
                used_source_groups=used_source_groups,
                output_index=output_index,
                step_index=step_index,
                remaining_ms=remaining_ms,
            )
            if source is None:
                if selection_warning:
                    output_warnings.append(selection_warning)
                    all_warnings.append(selection_warning)
                break
            segment = plan_quick_mix_segment(
                source,
                output_index=output_index,
                step_index=step_index,
                remaining_ms=remaining_ms,
                source_offsets=source_offsets,
                selection_warning=selection_warning,
            )
            segments.append(segment)
            used_material_ids.add(source.material_identity)
            used_source_groups.add(segment.normalized_source_group)
            output_warnings.extend(segment.warnings)
            all_warnings.extend(segment.warnings)
            remaining_ms -= segment.duration_ms
            step_index += 1

        output_plans.append(
            QuickMixOutputPlan(
                output_index=output_index,
                target_duration_ms=target_duration_ms,
                planned_duration_ms=sum(segment.duration_ms for segment in segments),
                segments=segments,
                warnings=output_warnings,
            )
        )

    return output_plans, all_warnings


def choose_quick_mix_source(
    sources: list[QuickMixSource],
    source_cursor: int,
    *,
    used_material_ids: set[str],
    used_source_groups: set[str],
    output_index: int,
    step_index: int,
    remaining_ms: int,
) -> tuple[QuickMixSource | None, int, dict | None]:
    def iter_sources():
        for offset in range(len(sources)):
            absolute_index = source_cursor + offset
            yield absolute_index, sources[absolute_index % len(sources)]

    for absolute_index, source in iter_sources():
        if preferred_quick_mix_segment_ms(source, remaining_ms) <= 0:
            continue
        is_new_source = source.material_identity not in used_material_ids
        is_new_group = source.source_group not in used_source_groups
        if is_new_source and is_new_group:
            return source, absolute_index + 1, None

    for absolute_index, source in iter_sources():
        if preferred_quick_mix_segment_ms(source, remaining_ms) <= 0:
            continue
        if source.material_identity not in used_material_ids:
            return (
                source,
                absolute_index + 1,
                build_quick_mix_warning(
                    QUICK_MIX_SOURCE_GROUP_RELAXED,
                    output_index=output_index,
                    step_index=step_index,
                    source=source,
                ),
            )

    for absolute_index, source in iter_sources():
        if preferred_quick_mix_segment_ms(source, remaining_ms) <= 0:
            continue
        if source.source_group not in used_source_groups:
            return (
                source,
                absolute_index + 1,
                build_quick_mix_warning(
                    QUICK_MIX_ASSET_REPEAT_RELAXED,
                    output_index=output_index,
                    step_index=step_index,
                    source=source,
                ),
            )

    fallback_source = next(
        (source for source in sources if bool(source.metadata.get("atomic_take"))),
        sources[source_cursor % len(sources)] if sources else None,
    )
    if fallback_source is not None and preferred_quick_mix_segment_ms(fallback_source, remaining_ms) > 0:
        return (
            fallback_source,
            source_cursor + 1,
            build_quick_mix_warning(
                QUICK_MIX_UNIQUE_MATERIAL_EXHAUSTED,
                output_index=output_index,
                step_index=step_index,
                source=fallback_source,
            ),
        )
    return (
        None,
        source_cursor,
        {
            "code": QUICK_MIX_ATOMIC_TAKE_EXHAUSTED,
            "output_index": output_index,
            "step_index": step_index,
            "remaining_ms": remaining_ms,
            "source_id": fallback_source.source_id if fallback_source is not None else "",
            "base_source_id": fallback_source.material_identity if fallback_source is not None else "",
            "source_path": str(fallback_source.path) if fallback_source is not None else "",
            "normalized_source_group": fallback_source.source_group if fallback_source is not None else "",
        },
    )


def plan_quick_mix_segment(
    source: QuickMixSource,
    *,
    output_index: int,
    step_index: int,
    remaining_ms: int,
    source_offsets: dict[str, int],
    selection_warning: dict | None = None,
) -> QuickMixSegmentPlan:
    segment_ms = preferred_quick_mix_segment_ms(source, remaining_ms)
    if segment_ms <= 0:
        raise ValueError(f"Could not determine a usable segment duration for source: {source.path}")

    if bool(source.metadata.get("atomic_take")):
        relative_start_ms = 0
        start_ms = source.source_start_ms
    elif source.media_type == "video" and source.duration_ms:
        max_start = max(0, source.duration_ms - segment_ms)
        cursor = source_offsets.get(source.source_id, 0)
        relative_start_ms = min(cursor, max_start)
        start_ms = source.source_start_ms + relative_start_ms
        next_cursor = cursor + segment_ms
        source_offsets[source.source_id] = 0 if next_cursor >= max_start and max_start > 0 else next_cursor
    else:
        relative_start_ms = 0
        start_ms = source.source_start_ms

    return QuickMixSegmentPlan(
        output_index=output_index,
        step_index=step_index,
        source_id=source.source_id,
        base_source_id=source.unique_base_id,
        source_path=str(source.path),
        source_basename=source.path.name,
        normalized_source_group=source.source_group,
        media_type=source.media_type,
        source_start_ms=start_ms,
        source_end_ms=start_ms + segment_ms,
        relative_source_start_ms=relative_start_ms,
        duration_ms=segment_ms,
        warnings=[selection_warning] if selection_warning else [],
    )


def build_quick_mix_warning(
    warning_code: str,
    *,
    output_index: int,
    step_index: int,
    source: QuickMixSource,
) -> dict:
    return {
        "code": warning_code,
        "output_index": output_index,
        "step_index": step_index,
        "source_id": source.source_id,
        "base_source_id": source.unique_base_id,
        "source_path": str(source.path),
        "normalized_source_group": source.source_group,
    }
