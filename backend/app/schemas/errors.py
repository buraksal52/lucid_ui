"""Typed representation of the project-standard JSON error envelope.

Used for OpenAPI documentation of error responses. The actual error responses
are constructed directly as JSON in app.core.exception_handlers, but sharing
this shape keeps the documented contract and the runtime behavior in sync.
See docs/api/error-codes.md.
"""

from typing import Any

from app.schemas.common import CamelModel


class ErrorPayload(CamelModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(CamelModel):
    error: ErrorPayload
