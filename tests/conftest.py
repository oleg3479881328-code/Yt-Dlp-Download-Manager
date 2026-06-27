from __future__ import annotations

import sys
import types

if "yt_dlp" not in sys.modules:
    yt_dlp_module = types.ModuleType("yt_dlp")
    utils_module = types.ModuleType("yt_dlp.utils")

    class YoutubeDL:  # noqa: D101
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __enter__(self) -> YoutubeDL:
            return self

        def __exit__(self, *_args) -> None:
            return None

        def extract_info(self, *_args, **_kwargs):  # noqa: ANN001, ANN002
            raise RuntimeError("yt_dlp test stub should not execute real downloads")

        def prepare_filename(self, info):  # noqa: ANN001
            return str(info.get("filepath", "stub-output.mp4"))

    class DownloadError(Exception):
        pass

    yt_dlp_module.YoutubeDL = YoutubeDL
    utils_module.DownloadError = DownloadError
    sys.modules["yt_dlp"] = yt_dlp_module
    sys.modules["yt_dlp.utils"] = utils_module
