"""Domain exceptions for the UIClip evaluation layer.

Subclass the shared `LucidUIError` and map onto the already-documented
`UICLIP_UNAVAILABLE` code (docs/api/error-codes.md) — no new error code is
introduced. Like the LLM layer's exceptions, these must never reach the
global exception handler: `UIClipEvaluationService` catches them internally
and degrades `uiclip.status` instead of failing the whole request — a
UIClip failure must never discard the deterministic analysis or the LLM
interpretation.
"""

from typing import Any

from app.core.exceptions import LucidUIError


class UIClipProviderUnavailableError(LucidUIError):
    """The provider could not be reached, loaded, or is not configured.

    Maps to `uiclip.status = "unavailable"`.
    """

    code = "UICLIP_UNAVAILABLE"
    status_code = 502

    def __init__(
        self,
        message: str = "The UIClip provider could not be reached or is not configured.",
        details: Any | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class UIClipEvaluationError(LucidUIError):
    """The provider was reached but the evaluation attempt failed.

    Covers malformed/unusable provider output and validation failures.
    Maps to `uiclip.status = "failed"`.
    """

    code = "UICLIP_UNAVAILABLE"
    status_code = 502

    def __init__(
        self,
        message: str = "UIClip evaluation failed.",
        details: Any | None = None,
    ) -> None:
        super().__init__(message=message, details=details)
