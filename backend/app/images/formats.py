"""Supported image format registry and lightweight magic-byte sniffing.

Sniffing lets ImageValidator flag obviously corrupted or mislabeled uploads
(a missing/mismatched file signature) without decoding pixels — deeper
corruption that only surfaces mid-decode is still caught by ImageDecoder.
"""

from enum import Enum


class SupportedImageFormat(str, Enum):
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"


MIME_TO_FORMAT: dict[str, SupportedImageFormat] = {
    "image/jpeg": SupportedImageFormat.JPEG,
    "image/png": SupportedImageFormat.PNG,
    "image/webp": SupportedImageFormat.WEBP,
}

SUPPORTED_MIME_TYPES: frozenset[str] = frozenset(MIME_TO_FORMAT)

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"


def sniff_format(data: bytes) -> SupportedImageFormat | None:
    """Best-effort file-signature sniff. Returns None if unrecognized."""
    if data.startswith(_PNG_SIGNATURE):
        return SupportedImageFormat.PNG
    if data.startswith(_JPEG_SIGNATURE):
        return SupportedImageFormat.JPEG
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return SupportedImageFormat.WEBP
    return None
