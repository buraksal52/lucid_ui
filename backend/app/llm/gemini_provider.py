"""Real LLM provider backed by Google Gemini via the official `google-genai` SDK.

Selected via configuration (`Settings.llm_provider == "gemini"`) only when
`Settings.gemini_api_key` is set — see `app.dependencies.get_llm_provider`.
Requests structured JSON output directly from the model using
`LLMStructuredOutput` as the response schema, so the SDK constrains the
model's output shape before this provider ever tries to parse it. Only ever
receives the two prompt strings built by `app.llm.prompt` — never an image.
"""

import json
import logging
from typing import Any

from google import genai
from google.genai import types

from app.llm.exceptions import LLMInterpretationError, LLMProviderUnavailableError
from app.llm.models import LLMStructuredOutput

logger = logging.getLogger("lucidui.llm.gemini")


class GeminiLLMProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, max_output_tokens: int) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._max_output_tokens = max_output_tokens

    def complete(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=LLMStructuredOutput,
                    max_output_tokens=self._max_output_tokens,
                ),
            )
        except Exception as exc:
            raise LLMProviderUnavailableError("Could not reach or authenticate with the Gemini API.") from exc

        raw_text = getattr(response, "text", None)
        if not raw_text:
            raise LLMInterpretationError("The Gemini API returned an empty response.")

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise LLMInterpretationError("The Gemini API response was not valid JSON.") from exc
