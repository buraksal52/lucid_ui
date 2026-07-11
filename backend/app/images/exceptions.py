"""Domain exceptions for image validation and decoding.

Each exception already carries the stable `code`/`status_code` documented in
docs/api/error-codes.md by subclassing the shared `LucidUIError`, so it maps
onto the project-standard JSON error envelope automatically via the global
exception handlers — no per-route translation needed.
"""

from app.core.exceptions import LucidUIError


class UnsupportedMediaType(LucidUIError):
    """Raised when the uploaded file's MIME type is not JPEG, PNG, or WebP."""

    code = "UNSUPPORTED_MEDIA_TYPE"
    status_code = 415

    def __init__(self, content_type: str | None, allowed: list[str]) -> None:
        super().__init__(
            message=(
                f"Unsupported image type '{content_type or 'unknown'}'. "
                f"Allowed types: {', '.join(allowed)}."
            ),
            details={"contentType": content_type, "allowed": allowed},
        )


class ImageTooLarge(LucidUIError):
    """Raised when the uploaded file exceeds the configured size limit."""

    code = "FILE_TOO_LARGE"
    status_code = 413

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            message=f"Uploaded image ({size_bytes} bytes) exceeds the {max_bytes}-byte limit.",
            details={"sizeBytes": size_bytes, "maxBytes": max_bytes},
        )


class EmptyImage(LucidUIError):
    """Raised when the uploaded file has no bytes."""

    code = "INVALID_IMAGE"
    status_code = 422

    def __init__(self) -> None:
        super().__init__(message="The uploaded image is empty.")


class ImageDecodeError(LucidUIError):
    """Raised when the uploaded bytes cannot be decoded as an image."""

    code = "INVALID_IMAGE"
    status_code = 422

    def __init__(self, reason: str | None = None) -> None:
        suffix = f": {reason}" if reason else "."
        super().__init__(message=f"The uploaded file could not be decoded as an image{suffix}")


class InvalidImage(LucidUIError):
    """Raised for image problems not covered by a more specific exception."""

    code = "INVALID_IMAGE"
    status_code = 422

    def __init__(self, message: str = "The uploaded file is not a valid image.") -> None:
        super().__init__(message=message)
