from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from science_assembly.sources.normalizer import normalize_pexels_video

JsonDict = Dict[str, Any]


class SourceAdapterError(RuntimeError):
    pass


class PexelsVideoSearchAdapter:
    endpoint = "https://api.pexels.com/v1/videos/search"

    def __init__(self, *, api_key: Optional[str] = None, timeout_seconds: int = 45) -> None:
        self.api_key = api_key or os.environ.get("PEXELS_API_KEY", "").strip()
        self.timeout_seconds = timeout_seconds
        if not self.api_key:
            raise SourceAdapterError("PEXELS_API_KEY is missing. Set it in the environment.")

    def search_for_beat(
        self,
        *,
        beat: JsonDict,
        beat_index: int,
        per_query: int = 3,
        orientation: Optional[str] = None,
    ) -> List[JsonDict]:
        candidates: List[JsonDict] = []
        queries = beat.get("search_queries") or []
        if not isinstance(queries, list):
            return candidates
        for query in queries[:3]:
            if not isinstance(query, str) or not query.strip():
                continue
            raw_results = self._search(query=query.strip(), per_page=per_query, orientation=orientation)
            for result_index, raw in enumerate(raw_results, start=1):
                candidates.append(
                    normalize_pexels_video(
                        raw=raw,
                        beat_id=str(beat.get("beat_id")),
                        beat_index=beat_index,
                        result_index=result_index,
                        query=query.strip(),
                    )
                )
        return candidates

    def _search(self, *, query: str, per_page: int, orientation: Optional[str]) -> List[JsonDict]:
        params: Dict[str, Any] = {"query": query, "per_page": per_page}
        if orientation in {"landscape", "portrait", "square"}:
            params["orientation"] = orientation
        url = f"{self.endpoint}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers={"Authorization": self.api_key})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SourceAdapterError(f"Pexels HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise SourceAdapterError(f"Pexels connection error: {exc}") from exc
        videos = payload.get("videos", [])
        if not isinstance(videos, list):
            return []
        return [item for item in videos if isinstance(item, dict)]
