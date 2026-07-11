"""Domain exceptions for the LLM interpretation layer.

Subclass the shared `LucidUIError` so they carry the same `code`/`status_code`
shape as every other domain exception, and map onto the already-documented
`LLM_UNAVAILABLE` code (docs/api/error-codes.md) rather than introducing a
new one. Unlike `MetricAnalysisError`, these must never reach the global
exception handler: `LLMInterpretationService` catches them internally and
degrades `llmInterpretation.status` instead of failing the whole request —
an LLM failure must never discard the deterministic analysis.
"""

from typing import Any

from app.core.exceptions import LucidUIError


class LLMProviderUnavailableError(LucidUIError):
    """The provider could not be reached, authenticated, or is not configured.

    Maps to `llmInterpretation.status = "unavailable"`.
    """

    code = "LLM_UNAVAILABLE"
    status_code = 502

    def __init__(
        self,
        message: str = "The LLM provider could not be reached or is not configured.",
        details: Any | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class LLMInterpretationError(LucidUIError):
    """The provider was reached but the interpretation attempt failed.

    Covers malformed/unparseable responses, schema validation failures, and
    missing metric evidence. Maps to `llmInterpretation.status = "failed"`.
    """

    code = "LLM_UNAVAILABLE"
    status_code = 502

    def __init__(
        self,
        message: str = "LLM interpretation failed.",
        details: Any | None = None,
    ) -> None:
        super().__init__(message=message, details=details)
