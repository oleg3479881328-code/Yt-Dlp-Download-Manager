from datetime import UTC, datetime

from video_mix.core.quick_mix_generation import (
    allocate_generation_paths,
    load_generation_index,
    load_prior_diversity_plans,
    record_generation,
    write_generation_json,
)


def test_generation_paths_do_not_overwrite_existing_generation(tmp_path) -> None:
    first = allocate_generation_paths(
        tmp_path,
        generation_id="quick_mix_test",
    )
    second = allocate_generation_paths(
        tmp_path,
        generation_id="quick_mix_test",
    )
    assert first.generation_id == "quick_mix_test"
    assert second.generation_id == "quick_mix_test_002"
    assert first.root_dir != second.root_dir
    assert first.exports_dir.exists()
    assert second.exports_dir.exists()


def test_generation_index_is_append_only(tmp_path) -> None:
    created_at = datetime(2026, 7, 11, tzinfo=UTC)
    first = allocate_generation_paths(tmp_path, generation_id="generation_a")
    first_output = first.exports_dir / "quick_mix_001.mp4"
    first_output.write_bytes(b"a")
    record_generation(
        tmp_path,
        first,
        requested_output_count=1,
        achieved_output_count=1,
        output_paths=[first_output],
        created_at=created_at,
    )

    second = allocate_generation_paths(tmp_path, generation_id="generation_b")
    second_output = second.exports_dir / "quick_mix_001.mp4"
    second_output.write_bytes(b"b")
    record_generation(
        tmp_path,
        second,
        requested_output_count=1,
        achieved_output_count=1,
        output_paths=[second_output],
        created_at=created_at,
    )

    index = load_generation_index(tmp_path)
    assert [entry["generation_id"] for entry in index["generations"]] == [
        "generation_a",
        "generation_b",
    ]
    assert index["generations"][0]["output_paths"] != index["generations"][1][
        "output_paths"
    ]


def test_prior_diversity_plans_load_from_generation_manifests(tmp_path) -> None:
    paths = allocate_generation_paths(tmp_path, generation_id="generation_history")
    write_generation_json(
        paths.plan_path,
        {
            "outputs": [
                {
                    "output_index": 1,
                    "target_duration_ms": 4000,
                    "segments": [
                        {
                            "segment_kind": "body",
                            "source_id": "take_a",
                            "base_source_id": "asset_a",
                            "content_identity": "composite:demo",
                            "source_group": "a.mp4",
                            "folder_id": "folder_a",
                            "source_path": "folder_a/a.mp4",
                            "media_type": "video",
                            "source_start_ms": 1000,
                            "duration_ms": 2000,
                        },
                        {
                            "segment_kind": "opening",
                            "source_id": "opening",
                            "folder_id": "opening",
                            "duration_ms": 1000,
                        },
                    ],
                }
            ]
        },
    )
    record_generation(
        tmp_path,
        paths,
        requested_output_count=1,
        achieved_output_count=1,
        output_paths=[],
    )
    plans = load_prior_diversity_plans(tmp_path)
    assert len(plans) == 1
    assert plans[0].body_signature == ("composite:demo",)
    assert plans[0].asset_signature == ("composite:demo",)
