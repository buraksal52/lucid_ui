"""Domain exceptions for the deterministic metric engine.

Subclass the shared `LucidUIError` so they map onto the project-standard
JSON error envelope via the existing global exception handlers, and onto the
`ANALYSIS_FAILED` code already documented in docs/api/error-codes.md — no
new error code is introduced in this phase.
"""

from typing import Any

from app.core.exceptions import LucidUIError


class MetricAnalysisError(LucidUIError):
    """Raised when the deterministic metric engine cannot produce a result.

    Covers invalid/missing decoded-image data and unexpected failures inside
    the legacy metric functions — never exposes raw internal stack traces to
    API clients, only a safe summary message.
    """

    code = "ANALYSIS_FAILED"
    status_code = 500

    def __init__(
        self,
        message: str = "The deterministic metric engine failed to produce a result.",
        details: Any | None = None,
    ) -> None:
        super().__init__(message=message, details=details)
