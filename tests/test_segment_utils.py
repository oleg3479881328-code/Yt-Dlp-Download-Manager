from __future__ import annotations

import pytest

from app.segment_utils import (
    SegmentValidationError,
    format_seconds_for_section,
    normalize_segment_payload,
    parse_time_value,
    sanitize_segment_label,
)


def test_parse_time_value_accepts_seconds() -> None:
    assert parse_time_value(65) == 65
    assert parse_time_value(65.25) == 65.25
    assert parse_time_value("65.5") == 65.5


def test_parse_time_value_accepts_mm_ss_and_hh_mm_ss() -> None:
    assert parse_time_value("01:05") == 65
    assert parse_time_value("00:01:05.250") == 65.25
    assert parse_time_value("1:02:03") == 3723


def test_parse_time_value_rejects_invalid_values() -> None:
    with pytest.raises(SegmentValidationError):
        parse_time_value(-1)
    with pytest.raises(SegmentValidationError):
        parse_time_value("01:99")
    with pytest.raises(SegmentValidationError):
        parse_time_value("abc")


def test_sanitize_segment_label() -> None:
    assert sanitize_segment_label("Main hook!") == "Main_hook"
    assert sanitize_segment_label("  ... ") == "clip"
    assert sanitize_segment_label("кириллица / emoji 🚀") == "emoji"


def test_normalize_segment_payload_with_end() -> None:
    segment = normalize_segment_payload({"start": "00:01:05", "end": "00:01:35", "label": "hook"})
    assert segment.start == 65
    assert segment.end == 95
    assert segment.duration == 30
    assert segment.label == "hook"
    assert segment.section_expression == "*65-95"


def test_normalize_segment_payload_with_duration() -> None:
    segment = normalize_segment_payload({"start": 65, "duration": 30, "label": "demo"})
    assert segment.start == 65
    assert segment.end == 95
    assert segment.section_expression == "*65-95"


def test_normalize_segment_payload_rejects_bad_ranges() -> None:
    with pytest.raises(SegmentValidationError):
        normalize_segment_payload({"start": 10, "end": 10})
    with pytest.raises(SegmentValidationError):
        normalize_segment_payload({"start": 10, "end": 9})
    with pytest.raises(SegmentValidationError):
        normalize_segment_payload({"start": 10})
    with pytest.raises(SegmentValidationError):
        normalize_segment_payload({"start": 10, "end": 20, "duration": 10})


def test_format_seconds_for_section() -> None:
    assert format_seconds_for_section(65.0) == "65"
    assert format_seconds_for_section(65.25) == "65.25"
    assert format_seconds_for_section(65.1234) == "65.123"
