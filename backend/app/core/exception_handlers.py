"""Global exception handlers that translate exceptions into the project-standard
JSON error envelope:

```json
{"error": {"code": "...", "message": "...", "details": null}}
```

Registered in `app.main.create_app`. No handler ever returns an HTML error page
or exposes a stack trace to the client.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import LucidUIError

logger = logging.getLogger("lucidui")


def _error_body(code: str, message: str, details: object | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


async def lucidui_error_handler(request: Request, exc: LucidUIError) -> JSONResponse:
    if exc.status_code >= 500:
        logger.exception("Unhandled domain error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_error_body(
            code="VALIDATION_ERROR",
            message="The request could not be validated.",
            details=exc.errors(),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=_error_body(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(LucidUIError, lucidui_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
