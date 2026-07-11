"""Pre-decode validation of uploaded image bytes.

Checks MIME type, size limit, emptiness, and file-signature ("magic bytes")
consistency — cheap checks that reject obviously invalid or corrupted
uploads before the more expensive cv2/Pillow decode step. Deliberately does
not decode pixels itself; deeper corruption that only surfaces mid-decode is
caught by ImageDecoder.
"""

from app.images.exceptions import EmptyImage, ImageDecodeError, ImageTooLarge, UnsupportedMediaType
from app.images.formats import MIME_TO_FORMAT, SUPPORTED_MIME_TYPES, sniff_format


class ImageValidator:
    def __init__(self, max_size_bytes: int) -> None:
        self._max_size_bytes = max_size_bytes

    def validate(self, content_type: str | None, data: bytes) -> None:
        if not data:
            raise EmptyImage()

        if content_type not in SUPPORTED_MIME_TYPES:
            raise UnsupportedMediaType(content_type, sorted(SUPPORTED_MIME_TYPES))

        if len(data) > self._max_size_bytes:
            raise ImageTooLarge(len(data), self._max_size_bytes)

        sniffed = sniff_format(data)
        if sniffed is None or sniffed != MIME_TO_FORMAT[content_type]:
            raise ImageDecodeError("the file signature does not match a supported image format")
