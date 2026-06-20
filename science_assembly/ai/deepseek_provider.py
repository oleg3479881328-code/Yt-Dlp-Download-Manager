from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from science_assembly.ai.provider import AIProvider, AIProviderError
from science_assembly.ai.prompts import qa_review_prompt, rank_candidates_prompt, visual_beats_prompt

JsonDict = Dict[str, Any]


class DeepSeekProvider(AIProvider):
    """Minimal DeepSeek provider using Python stdlib HTTP.

    This draft avoids adding dependencies. An executor may replace it with the
    official OpenAI-compatible SDK later if the project accepts that dependency.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        fast_model: str = "deepseek-v4-flash",
        reasoning_model: str = "deepseek-v4-pro",
        timeout_seconds: int = 90,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "").strip()
        self.base_url = base_url.rstrip("/")
        self.fast_model = fast_model
        self.reasoning_model = reasoning_model
        self.timeout_seconds = timeout_seconds
        if not self.api_key:
            raise AIProviderError("DEEPSEEK_API_KEY is missing. Set it in the environment.")

    @classmethod
    def from_env(cls) -> "DeepSeekProvider":
        return cls(
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            fast_model=os.environ.get("AI_MODEL_FAST", "deepseek-v4-flash"),
            reasoning_model=os.environ.get("AI_MODEL_REASONING", "deepseek-v4-pro"),
        )

    def extract_visual_beats(
        self,
        *,
        script_text: str,
        project_id: str,
        language: str,
        target_duration_seconds: int,
    ) -> JsonDict:
        prompt = visual_beats_prompt(
            script_text=script_text,
            project_id=project_id,
            language=language,
            target_duration_seconds=target_duration_seconds,
        )
        return self._chat_json(model=self.fast_model, prompt=prompt)

    def rank_candidates(
        self,
        *,
        visual_beats: JsonDict,
        source_candidates: JsonDict,
        project_id: str,
    ) -> JsonDict:
        prompt = rank_candidates_prompt(
            visual_beats=visual_beats,
            source_candidates=source_candidates,
            project_id=project_id,
        )
        return self._chat_json(model=self.fast_model, prompt=prompt)

    def qa_review(self, *, timeline: JsonDict, source_ledger: JsonDict) -> JsonDict:
        prompt = qa_review_prompt(timeline=timeline, source_ledger=source_ledger)
        return self._chat_json(model=self.reasoning_model, prompt=prompt)

    def _chat_json(self, *, model: str, prompt: str) -> JsonDict:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return valid json only. Do not include markdown or extra commentary.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise AIProviderError(f"DeepSeek HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise AIProviderError(f"DeepSeek connection error: {exc}") from exc

        try:
            parsed = json.loads(raw)
            content = parsed["choices"][0]["message"]["content"]
            data = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError(f"DeepSeek returned invalid JSON response: {raw[:1000]}") from exc

        if not isinstance(data, dict):
            raise AIProviderError("DeepSeek JSON response was not an object.")
        return data
