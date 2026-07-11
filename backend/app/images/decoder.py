"""Decodes validated image bytes into OpenCV and Pillow representations.

Both representations are built from the same in-memory bytes and no
temporary file is ever written, per docs/architecture/privacy-model.md.
Uses `cv2.imdecode()` (never `cv2.imread()`, which requires a filesystem
path) so the raw bytes never touch disk.
"""

import io

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from app.images.exceptions import ImageDecodeError
from app.images.metadata import ImageMetadataExtractor
from app.images.models import DecodedImage


class ImageDecoder:
    def __init__(self, metadata_extractor: ImageMetadataExtractor | None = None) -> None:
        self._metadata_extractor = metadata_extractor or ImageMetadataExtractor()

    def decode(self, data: bytes, content_type: str) -> DecodedImage:
        cv2_image = self._decode_cv2(data)
        pil_image = self._decode_pillow(data)
        metadata = self._metadata_extractor.extract(pil_image=pil_image, data=data, content_type=content_type)
        return DecodedImage(raw_bytes=data, cv2_image=cv2_image, pil_image=pil_image, metadata=metadata)

    @staticmethod
    def _decode_cv2(data: bytes) -> np.ndarray:
        buffer = np.frombuffer(data, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise ImageDecodeError("OpenCV could not decode the image bytes")
        return image

    @staticmethod
    def _decode_pillow(data: bytes) -> Image.Image:
        try:
            image = Image.open(io.BytesIO(data))
            image.load()
        except (UnidentifiedImageError, OSError) as exc:
            raise ImageDecodeError("Pillow could not decode the image bytes") from exc
        return image
