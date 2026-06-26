"""Draft candidate builder for VIDEO MIX."""

from __future__ import annotations

import itertools
from collections import defaultdict

from .asset_scan import stable_id
from .models import CandidateClip, CandidateReel, CandidateStatus, Clip, ReelTemplate, TemplateSlot


def slot_matches(slot: TemplateSlot, clip: Clip) -> bool:
    if not clip.usable:
        return False
    if clip.duration_ms < slot.min_duration_ms:
        return False
    if slot.required_tags and not set(slot.required_tags).issubset(set(clip.tags)):
        return False
    if set(slot.forbidden_tags).intersection(clip.tags):
        return False
    return True


def slot_score(slot: TemplateSlot, clip: Clip) -> float:
    score = clip.quality_score
    preferred_hits = len(set(slot.preferred_tags).intersection(clip.tags))
    score += preferred_hits * 10
    if clip.duration_ms > slot.max_duration_ms:
        score -= 5
    return score


def choose_clip_for_slot(
    slot: TemplateSlot,
    clips: list[Clip],
    used_asset_ids: set[str],
) -> Clip | None:
    candidates = [clip for clip in clips if slot_matches(slot, clip)]
    candidates.sort(key=lambda clip: slot_score(slot, clip), reverse=True)

    for clip in candidates:
        if clip.asset_id not in used_asset_ids:
            return clip
    return candidates[0] if candidates else None


def build_candidate_from_template(
    project_id: str,
    pack_id: str,
    template: ReelTemplate,
    clips: list[Clip],
    index: int,
) -> CandidateReel | None:
    selected: list[CandidateClip] = []
    used_asset_ids: set[str] = set()
    cursor_ms = 0
    score_parts: list[float] = []
    warnings: list[str] = []

    for slot in template.slots:
        clip = choose_clip_for_slot(slot, clips, used_asset_ids)
        if clip is None:
            warnings.append(f"missing_slot:{slot.slot_id}")
            continue

        use_ms = min(clip.duration_ms, slot.max_duration_ms)
        selected.append(
            CandidateClip(
                clip_id=clip.clip_id,
                slot_id=slot.slot_id,
                start_in_reel_ms=cursor_ms,
                end_in_reel_ms=cursor_ms + use_ms,
            )
        )
        cursor_ms += use_ms
        used_asset_ids.add(clip.asset_id)
        score_parts.append(slot_score(slot, clip))

    if not selected:
        return None

    candidate_id = stable_id("cand", f"{project_id}:{template.template_id}:{index}:{cursor_ms}")
    score = sum(score_parts) / len(score_parts) if score_parts else 0.0

    return CandidateReel(
        candidate_id=candidate_id,
        project_id=project_id,
        pack_id=pack_id,
        template_id=template.template_id,
        status=CandidateStatus.GENERATED,
        score=score,
        duration_ms=cursor_ms,
        clips=selected,
        warnings=warnings,
    )


def build_candidates(
    project_id: str,
    pack_id: str,
    templates: list[ReelTemplate],
    clips: list[Clip],
    max_candidates: int = 20,
) -> list[CandidateReel]:
    usable_clips = [clip for clip in clips if clip.usable]
    usable_clips.sort(key=lambda clip: clip.quality_score, reverse=True)

    candidates: list[CandidateReel] = []
    for index, template in enumerate(itertools.cycle(templates), start=1):
        if len(candidates) >= max_candidates:
            break
        candidate = build_candidate_from_template(
            project_id=project_id,
            pack_id=pack_id,
            template=template,
            clips=usable_clips,
            index=index,
        )
        if candidate is not None:
            candidates.append(candidate)

    return candidates


def summarize_reuse(candidates: list[CandidateReel]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for candidate in candidates:
        for clip in candidate.clips:
            counts[clip.clip_id] += 1
    return dict(counts)
