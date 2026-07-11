"""Typed containers for decoded images and their metadata.

`DecodedImage` is a plain (non-Pydantic) container: it holds a numpy array
and a Pillow image, neither of which is JSON-serializable, and it is never
returned directly over the API — future pipeline stages (Phase 2B metrics,
OCR, UIClip) should receive a `DecodedImage` instead of raw bytes or
individual values.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image

from app.schemas.common import CamelModel

Orientation = Literal["landscape", "portrait", "square"]


class ImageMetadata(CamelModel):
    """Non-content metadata about a decoded image. Never includes pixel data."""

    width: int
    height: int
    format: str
    aspect_ratio: float
    orientation: Orientation
    file_size_bytes: int


@dataclass(frozen=True, eq=False)
class DecodedImage:
    """The same uploaded bytes, decoded into both representations pipeline
    stages need: OpenCV (numpy array, BGR) for computer-vision metrics, and
    Pillow for OCR/UIClip preprocessing. Held entirely in memory.
    """

    raw_bytes: bytes
    cv2_image: np.ndarray
    pil_image: Image.Image
    metadata: ImageMetadata
