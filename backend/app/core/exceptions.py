"""Domain exceptions for the LucidUI backend.

Every domain exception carries a stable `code` (matching docs/api/error-codes.md),
a human-readable `message`, an HTTP `status_code`, and optional structured `details`.
Route and service code should raise these instead of generic exceptions so the
global exception handlers can translate them into the project-standard JSON
error envelope.
"""

from typing import Any


class LucidUIError(Exception):
    """Base class for all domain exceptions with a structured error payload."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(self, message: str, details: Any | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class AnalysisNotFoundError(LucidUIError):
    """Raised when a requested analysis ID does not exist in the repository."""

    code = "ANALYSIS_NOT_FOUND"
    status_code = 404

    def __init__(self, analysis_id: str) -> None:
        super().__init__(
            message=f"No analysis was found with ID '{analysis_id}'.",
            details={"analysisId": analysis_id},
        )


class InvalidContextError(LucidUIError):
    """Raised when the requested analysis `context` is not an allowed value."""

    code = "INVALID_CONTEXT"
    status_code = 422

    def __init__(self, context: str, allowed: list[str]) -> None:
        super().__init__(
            message=f"'{context}' is not a valid analysis context.",
            details={"context": context, "allowed": allowed},
        )


class InvalidRequestError(LucidUIError):
    """Raised for use-case-level request problems not covered by a more specific error."""

    code = "VALIDATION_ERROR"
    status_code = 422


class AnalysisFailedError(LucidUIError):
    """Raised when the (mock) deterministic metric engine fails to produce a report."""

    code = "ANALYSIS_FAILED"
    status_code = 500


class InternalError(LucidUIError):
    """Raised for unexpected internal failures not covered by a domain-specific error."""

    code = "INTERNAL_ERROR"
    status_code = 500
