from __future__ import annotations

import pytest

from native_host.ytdlp_host import (
    MAX_UPLOAD_CHUNK_BYTES,
    MAX_UPLOAD_TOTAL_BYTES,
    validate_upload_size,
)


def test_validate_upload_size_rejects_zero():
    with pytest.raises(ValueError, match="greater than zero"):
        validate_upload_size(0)


def test_validate_upload_size_rejects_oversized_payload():
    with pytest.raises(ValueError, match="max total size"):
        validate_upload_size(MAX_UPLOAD_TOTAL_BYTES + 1)


def test_upload_chunk_constant_matches_extension_contract():
    assert MAX_UPLOAD_CHUNK_BYTES == 256 * 1024
