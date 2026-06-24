from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from science_assembly.sources.normalizer import normalize_pixabay_video

JsonDict = Dict[str, Any]


class SourceAdapterError(RuntimeError):
    pass


class SecondStockVideoSearchAdapter:
    """Second stock video provider adapter.

    This implements the second provider described in the handoff docs while
    keeping the neutral filename that was already added to the draft scaffold.
    """

    endpoint = "https://pixabay.com/api/videos/"

    def __init__(self, *, api_key: Optional[str] = None, timeout_seconds: int = 45) -> None:
        self.api_key = api_key or os.environ.get("PIXABAY_API_KEY", "").strip()
        self.timeout_seconds = timeout_seconds
        if not self.api_key:
            raise SourceAdapterError("PIXABAY_API_KEY is missing. Set it in the environment.")

    def search_for_beat(self, *, beat: JsonDict, beat_index: int, per_query: int = 3) -> List[JsonDict]:
        candidates: List[JsonDict] = []
        queries = beat.get("search_queries") or []
        if not isinstance(queries, list):
            return candidates
        candidate_counter = 0
        for query in queries[:3]:
            if not isinstance(query, str) or not query.strip():
                continue
            for raw in self._search(query=query.strip(), per_page=per_query):
                candidate_counter += 1
                candidates.append(
                    normalize_pixabay_video(
                        raw=raw,
                        beat_id=str(beat.get("beat_id")),
                        beat_index=beat_index,
                        result_index=candidate_counter,
                        query=query.strip(),
                    )
                )
        return candidates

    def _search(self, *, query: str, per_page: int) -> List[JsonDict]:
        params: Dict[str, Any] = {
            "key": self.api_key,
            "q": query,
            "per_page": per_page,
            "safesearch": "true",
        }
        url = f"{self.endpoint}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SourceAdapterError(f"Second stock provider HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise SourceAdapterError(f"Second stock provider connection error: {exc}") from exc
        hits = payload.get("hits", [])
        if not isinstance(hits, list):
            return []
        return [item for item in hits if isinstance(item, dict)]
