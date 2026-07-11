"""Extracts non-content metadata from a decoded image.

Reads only dimensions/format/size — never pixel content — so this stays safe
to log and to include in an API response.
"""

from app.images.models import ImageMetadata, Orientation
from PIL import Image


class ImageMetadataExtractor:
    def extract(self, pil_image: Image.Image, data: bytes, content_type: str) -> ImageMetadata:
        width, height = pil_image.size
        aspect_ratio = round(width / height, 4) if height else 0.0
        image_format = (pil_image.format or "").lower() or self._format_from_content_type(content_type)
        return ImageMetadata(
            width=width,
            height=height,
            format=image_format,
            aspect_ratio=aspect_ratio,
            orientation=self._orientation(width, height),
            file_size_bytes=len(data),
        )

    @staticmethod
    def _orientation(width: int, height: int) -> Orientation:
        if width > height:
            return "landscape"
        if height > width:
            return "portrait"
        return "square"

    @staticmethod
    def _format_from_content_type(content_type: str) -> str:
        return content_type.split("/")[-1]
