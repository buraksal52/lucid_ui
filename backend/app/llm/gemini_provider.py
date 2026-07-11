"""Real LLM provider backed by Google Gemini via the official `google-genai` SDK.

Selected via configuration (`Settings.llm_provider == "gemini"`) only when
`Settings.gemini_api_key` is set — see `app.dependencies.get_llm_provider`.
Requests structured JSON output directly from the model by setting BOTH
`response_mime_type="application/json"` AND `response_schema=
LLMStructuredOutput` together in the same `GenerateContentConfig` — the SDK
only builds `response.parsed` when both are present. Only ever receives the
two prompt strings built by `app.llm.prompt` — never an image.

Parsing prefers `response.parsed` (the SDK's own already-validated result,
built internally via `LLMStructuredOutput.model_validate_json(...)`) over
re-parsing `response.text` with stdlib `json.loads()`. The two are built
from the same underlying text, but `response.parsed` uses pydantic-core's
JSON parser directly, which is the SDK's own recommended path for structured
output and does not need our own second, more brittle parse of the same
data. `response.text` is only used as a fallback when `.parsed` is absent —
never repaired with markdown-fence stripping or other text heuristics; if
Gemini didn't return valid JSON, that is treated as a genuine failure
(`LLMInterpretationError`), not something to patch around after the fact.

Thinking is disabled (`thinking_budget=0`): this task is bounded structured
extraction from an already-fixed JSON schema, not open-ended reasoning, and
gemini-2.5-flash's default "thinking" tokens were observed consuming nearly
the entire `max_output_tokens` budget on realistic prompts (~980 of 1024),
truncating the actual answer before any valid JSON could be produced
(`finish_reason=MAX_TOKENS`). Disabling thinking removes that failure mode
at the source rather than only enlarging the budget around it.
"""

import json
import logging
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.llm.exceptions import LLMInterpretationError, LLMProviderUnavailableError
from app.llm.models import LLMStructuredOutput

logger = logging.getLogger("lucidui.llm.gemini")


class GeminiLLMProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, max_output_tokens: int) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._max_output_tokens = max_output_tokens

    def _build_config(self, system_prompt: str) -> types.GenerateContentConfig:
        """Structured-output config for a request.

        `response_mime_type` and `response_schema` must both be set — the
        SDK only populates `response.parsed` when both are present together;
        setting only one silently disables structured-output parsing.
        `thinking_config` disables Gemini 2.5's internal "thinking" tokens,
        which otherwise compete with the actual JSON answer for the same
        `max_output_tokens` budget — see the module docstring.
        """
        return types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=LLMStructuredOutput,
            max_output_tokens=self._max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

    def complete(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=self._build_config(system_prompt),
            )
        except Exception as exc:
            raise LLMProviderUnavailableError("Could not reach or authenticate with the Gemini API.") from exc

        self._log_response_metadata(response)
        return self._extract_payload(response)

    @staticmethod
    def _log_response_metadata(response: Any) -> None:
        """Debug-only visibility into why a response did or didn't parse.

        `finish_reason` (e.g. `MAX_TOKENS`) and `usage_metadata` (token
        counts only, e.g. `thoughts_token_count`) contain no model-generated
        content, so logging them is safe — never log the API key or the full
        response text/parsed payload at any level.
        """
        candidates = getattr(response, "candidates", None) or []
        finish_reason = candidates[0].finish_reason if candidates else None
        logger.debug(
            "Gemini response finish_reason=%s usage_metadata=%s",
            finish_reason,
            getattr(response, "usage_metadata", None),
        )

    def _extract_payload(self, response: Any) -> dict[str, Any]:
        parsed = getattr(response, "parsed", None)
        logger.debug(
            "Gemini response.parsed present=%s type=%s",
            parsed is not None,
            type(parsed).__name__ if parsed is not None else None,
        )

        if isinstance(parsed, LLMStructuredOutput):
            return parsed.model_dump(by_alias=True)

        if isinstance(parsed, dict):
            return self._validate(parsed, source="response.parsed").model_dump(by_alias=True)

        # .parsed is unavailable (SDK could not build it) — fall back to text.
        logger.warning("Gemini response.parsed unavailable; falling back to response.text")
        raw_text = getattr(response, "text", None)
        logger.debug("Gemini response.text empty=%s", not raw_text)
        if not raw_text:
            raise LLMInterpretationError("The Gemini API returned an empty response.")

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("Gemini response.text was not valid JSON (%s)", type(exc).__name__)
            raise LLMInterpretationError("The Gemini API response was not valid JSON.") from exc

        return self._validate(payload, source="response.text").model_dump(by_alias=True)

    @staticmethod
    def _validate(payload: dict[str, Any], source: str) -> LLMStructuredOutput:
        try:
            return LLMStructuredOutput.model_validate(payload)
        except ValidationError as exc:
            logger.warning("Gemini %s failed LLMStructuredOutput validation (%s)", source, type(exc).__name__)
            raise LLMInterpretationError("The Gemini API response did not match the expected structure.") from exc
