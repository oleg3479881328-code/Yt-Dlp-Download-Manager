from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict

JsonDict = Dict[str, Any]


@dataclass(frozen=True)
class AIModelConfig:
    provider: str
    fast_model: str
    reasoning_model: str


class AIProviderError(RuntimeError):
    pass


class AIProvider(ABC):
    """Structured AI provider interface.

    Providers return JSON-like dictionaries only. The local application decides
    whether to search, cut, render, or save files.
    """

    @abstractmethod
    def extract_visual_beats(
        self,
        *,
        script_text: str,
        project_id: str,
        language: str,
        target_duration_seconds: int,
    ) -> JsonDict:
        pass

    @abstractmethod
    def rank_candidates(
        self,
        *,
        visual_beats: JsonDict,
        source_candidates: JsonDict,
        project_id: str,
    ) -> JsonDict:
        pass

    @abstractmethod
    def qa_review(self, *, timeline: JsonDict, source_ledger: JsonDict) -> JsonDict:
        pass
