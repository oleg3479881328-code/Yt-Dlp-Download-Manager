"""Draft wedding templates for VIDEO MIX.

Kept in Python for zero dependencies. Codex can later convert this to YAML
or database-backed config if that becomes useful.
"""

from __future__ import annotations

from ...core.models import ReelTemplate, TemplateSlot


PACK_ID = "wedding"


def get_wedding_templates() -> list[ReelTemplate]:
    return [
        ReelTemplate(
            template_id="romantic_story",
            pack_id=PACK_ID,
            name="Romantic Story",
            target_duration_ms=28_000,
            pacing="medium",
            slots=[
                TemplateSlot("opening_detail", 1200, 3000, preferred_tags=["details", "venue"]),
                TemplateSlot("preparation", 1500, 3500, preferred_tags=["bride", "groom", "preparation"]),
                TemplateSlot("couple", 2500, 5000, preferred_tags=["couple", "emotion"]),
                TemplateSlot("closing", 2000, 4500, preferred_tags=["kiss", "dance", "couple"]),
            ],
        ),
        ReelTemplate(
            template_id="fast_highlight",
            pack_id=PACK_ID,
            name="Fast Highlight",
            target_duration_ms=20_000,
            pacing="fast",
            slots=[
                TemplateSlot("detail_1", 800, 1800, preferred_tags=["details"]),
                TemplateSlot("person_1", 800, 1800, preferred_tags=["bride", "groom"]),
                TemplateSlot("couple_1", 800, 2200, preferred_tags=["couple"]),
                TemplateSlot("party_1", 800, 2200, preferred_tags=["dance", "guests"]),
                TemplateSlot("final", 1200, 2500, preferred_tags=["kiss", "emotion"]),
            ],
        ),
        ReelTemplate(
            template_id="behind_the_scenes",
            pack_id=PACK_ID,
            name="Behind The Scenes",
            target_duration_ms=24_000,
            pacing="medium",
            slots=[
                TemplateSlot("bts_open", 1500, 3500, preferred_tags=["backstage", "photographer"]),
                TemplateSlot("posing", 1500, 3500, preferred_tags=["couple", "posing"]),
                TemplateSlot("detail", 1200, 3000, preferred_tags=["details"]),
                TemplateSlot("result_feel", 2000, 4500, preferred_tags=["emotion", "couple"]),
            ],
        ),
        ReelTemplate(
            template_id="details_to_couple",
            pack_id=PACK_ID,
            name="Details To Couple",
            target_duration_ms=25_000,
            pacing="slow",
            slots=[
                TemplateSlot("rings", 1500, 3500, preferred_tags=["rings", "details"]),
                TemplateSlot("dress", 1500, 3500, preferred_tags=["dress", "bride"]),
                TemplateSlot("venue", 1500, 3500, preferred_tags=["venue"]),
                TemplateSlot("couple", 2500, 5000, preferred_tags=["couple", "emotion"]),
            ],
        ),
        ReelTemplate(
            template_id="party_energy",
            pack_id=PACK_ID,
            name="Party Energy",
            target_duration_ms=22_000,
            pacing="fast",
            slots=[
                TemplateSlot("guests", 800, 2200, preferred_tags=["guests"]),
                TemplateSlot("dance", 800, 2200, preferred_tags=["dance"]),
                TemplateSlot("couple", 1000, 2500, preferred_tags=["couple"]),
                TemplateSlot("energy", 800, 2200, preferred_tags=["party", "dance"]),
            ],
        ),
    ]
