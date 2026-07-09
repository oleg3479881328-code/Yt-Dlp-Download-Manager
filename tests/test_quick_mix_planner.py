from pathlib import Path

import pytest

from video_mix.core.quick_mix_planner import (
    QUICK_MIX_UNIQUE_MATERIAL_EXHAUSTED,
    QuickMixSource,
    build_quick_mix_plan,
    normalize_quick_mix_source_group,
)


def test_normalize_quick_mix_source_group_collapses_whatsapp_variants() -> None:
    assert normalize_quick_mix_source_group(Path("WhatsApp Video 2026-07-03 at 10.21.53 PM.mp4")) == (
        normalize_quick_mix_source_group(Path("WhatsApp Video 2026-07-03 at 10.21.53 PM (3).MP4"))
    )
    assert normalize_quick_mix_source_group(Path("ceremony.mp4")) != normalize_quick_mix_source_group(
        Path("ceremony alternate.mp4")
    )


def test_quick_mix_plan_avoids_same_source_and_whatsapp_group_per_output() -> None:
    sources = [
        QuickMixSource(
            source_id="asset_whatsapp_1",
            path=Path("WhatsApp Video 2026-07-03 at 10.21.53 PM.jpg"),
            media_type="photo",
        ),
        QuickMixSource(
            source_id="asset_whatsapp_2",
            path=Path("WhatsApp Video 2026-07-03 at 10.21.53 PM (1).jpg"),
            media_type="photo",
        ),
        QuickMixSource(
            source_id="asset_cake",
            path=Path("cake_detail.jpg"),
            media_type="photo",
        ),
    ]

    plans, warnings = build_quick_mix_plan(sources, target_duration_ms=4000, output_count=1)
    groups = [segment.normalized_source_group for segment in plans[0].segments]
    source_ids = [segment.source_id for segment in plans[0].segments]

    assert warnings == []
    assert len(groups) == len(set(groups))
    assert len(source_ids) == len(set(source_ids))
    assert "whatsapp video 2026-07-03 at 10.21.53 pm.jpg" in groups
    assert "cake_detail.jpg" in groups


def test_quick_mix_plan_reports_warning_when_unique_material_is_exhausted() -> None:
    plans, warnings = build_quick_mix_plan(
        [QuickMixSource(source_id="only_photo", path=Path("only_photo.jpg"), media_type="photo")],
        target_duration_ms=4000,
        output_count=1,
    )

    assert len(plans[0].segments) == 2
    assert len(warnings) == 1
    assert warnings[0]["code"] == QUICK_MIX_UNIQUE_MATERIAL_EXHAUSTED
    assert plans[0].warnings[0]["code"] == QUICK_MIX_UNIQUE_MATERIAL_EXHAUSTED


def test_quick_mix_plan_preserves_video_offsets_without_reusing_within_output_when_possible() -> None:
    sources = [
        QuickMixSource(source_id="video_a", path=Path("a.mp4"), media_type="video", duration_ms=9000),
        QuickMixSource(source_id="video_b", path=Path("b.mp4"), media_type="video", duration_ms=9000),
    ]

    plans, warnings = build_quick_mix_plan(sources, target_duration_ms=6000, output_count=2)

    assert warnings == []
    assert [segment.source_id for segment in plans[0].segments] == ["video_a", "video_b"]
    assert [segment.source_id for segment in plans[1].segments] == ["video_a", "video_b"]
    assert [segment.relative_source_start_ms for segment in plans[0].segments] == [0, 0]
    assert [segment.relative_source_start_ms for segment in plans[1].segments] == [3000, 3000]


def test_quick_mix_plan_rejects_empty_sources() -> None:
    with pytest.raises(ValueError, match="At least one Quick Mix source"):
        build_quick_mix_plan([], target_duration_ms=4000, output_count=1)
