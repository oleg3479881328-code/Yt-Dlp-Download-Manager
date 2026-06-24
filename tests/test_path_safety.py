from __future__ import annotations

import pytest

from app.path_safety import MissingPathError, UnsafePathError, resolve_existing_output_path, resolve_output_root


def test_resolve_output_root_uses_base_dir_for_relative_paths(tmp_path):
    root = resolve_output_root("downloads", tmp_path)

    assert root == (tmp_path / "downloads").resolve()


def test_resolve_existing_output_path_allows_file_inside_output_directory(tmp_path):
    output_dir = tmp_path / "downloads"
    output_dir.mkdir()
    media = output_dir / "video.mp4"
    media.write_text("demo", encoding="utf-8")

    resolved = resolve_existing_output_path(media, output_dir, tmp_path)

    assert resolved == media.resolve()


def test_resolve_existing_output_path_rejects_file_outside_output_directory(tmp_path):
    output_dir = tmp_path / "downloads"
    output_dir.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("do not open", encoding="utf-8")

    with pytest.raises(UnsafePathError):
        resolve_existing_output_path(secret, output_dir, tmp_path)


def test_resolve_existing_output_path_rejects_missing_path(tmp_path):
    output_dir = tmp_path / "downloads"
    output_dir.mkdir()

    with pytest.raises(MissingPathError):
        resolve_existing_output_path(output_dir / "missing.mp4", output_dir, tmp_path)


def test_resolve_existing_output_path_rejects_empty_path(tmp_path):
    output_dir = tmp_path / "downloads"
    output_dir.mkdir()

    with pytest.raises(MissingPathError):
        resolve_existing_output_path(None, output_dir, tmp_path)
