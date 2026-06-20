from __future__ import annotations

from typing import Any, Dict, List

JsonDict = Dict[str, Any]


class SourceAdapterError(RuntimeError):
    pass


class SecondStockVideoSearchAdapter:
    """Placeholder for a second stock video provider.

    The executor should wire this to the provider selected in the handoff docs.
    Keep returned items normalized through sources.normalizer.
    """

    def search_for_beat(self, *, beat: JsonDict, beat_index: int, per_query: int = 3) -> List[JsonDict]:
        raise SourceAdapterError("Second stock video adapter is not implemented in this draft.")
