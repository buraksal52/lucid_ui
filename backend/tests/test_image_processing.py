"""Unit-level tests for app.images: validator, decoder, metadata extractor.

Exercises the image infrastructure directly (not through the API) so
failures point at the exact stage (validate vs. decode vs. metadata) that
broke.
"""

import os

import numpy as np
import pytest
from PIL import Image

from app.images.decoder import ImageDecoder
from app.images.exceptions import EmptyImage, ImageDecodeError, ImageTooLarge, UnsupportedMediaType
from app.images.validator import ImageValidator

MAX_SIZE = 20 * 1024 * 1024


@pytest.fixture
def validator() -> ImageValidator:
    return ImageValidator(max_size_bytes=MAX_SIZE)


@pytest.fixture
def decoder() -> ImageDecoder:
    return ImageDecoder()


def test_validator_accepts_valid_png(validator: ImageValidator, valid_png_bytes: bytes) -> None:
    validator.validate("image/png", valid_png_bytes)  # must not raise


def test_validator_accepts_valid_jpeg(validator: ImageValidator, valid_jpeg_bytes: bytes) -> None:
    validator.validate("image/jpeg", valid_jpeg_bytes)  # must not raise


def test_validator_accepts_valid_webp(validator: ImageValidator, valid_webp_bytes: bytes) -> None:
    validator.validate("image/webp", valid_webp_bytes)  # must not raise


def test_validator_rejects_unsupported_mime(validator: ImageValidator, valid_png_bytes: bytes) -> None:
    with pytest.raises(UnsupportedMediaType):
        validator.validate("image/gif", valid_png_bytes)


def test_validator_rejects_empty_upload(validator: ImageValidator) -> None:
    with pytest.raises(EmptyImage):
        validator.validate("image/png", b"")


def test_validator_rejects_oversized_upload(valid_png_bytes: bytes) -> None:
    tiny_validator = ImageValidator(max_size_bytes=10)
    with pytest.raises(ImageTooLarge):
        tiny_validator.validate("image/png", valid_png_bytes)


def test_validator_rejects_mismatched_signature(validator: ImageValidator, mismatched_signature_bytes: bytes) -> None:
    with pytest.raises(ImageDecodeError):
        validator.validate("image/png", mismatched_signature_bytes)


def test_decoder_produces_opencv_and_pillow_representations(decoder: ImageDecoder, valid_png_bytes: bytes) -> None:
    decoded = decoder.decode(valid_png_bytes, "image/png")
    assert isinstance(decoded.cv2_image, np.ndarray)
    assert isinstance(decoded.pil_image, Image.Image)
    assert decoded.cv2_image.shape[1] == decoded.pil_image.size[0]
    assert decoded.cv2_image.shape[0] == decoded.pil_image.size[1]
    assert decoded.raw_bytes == valid_png_bytes


def test_decoder_extracts_metadata(decoder: ImageDecoder, valid_png_bytes: bytes) -> None:
    decoded = decoder.decode(valid_png_bytes, "image/png")
    assert decoded.metadata.width == 64
    assert decoded.metadata.height == 40
    assert decoded.metadata.format == "png"
    assert decoded.metadata.aspect_ratio == pytest.approx(1.6)
    assert decoded.metadata.orientation == "landscape"
    assert decoded.metadata.file_size_bytes == len(valid_png_bytes)


def test_decoder_raises_on_corrupted_bytes(decoder: ImageDecoder, corrupted_png_bytes: bytes) -> None:
    with pytest.raises(ImageDecodeError):
        decoder.decode(corrupted_png_bytes, "image/png")


def test_decode_never_writes_temporary_files(
    decoder: ImageDecoder, valid_png_bytes: bytes, tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    before = set(os.listdir(tmp_path))

    decoder.decode(valid_png_bytes, "image/png")

    after = set(os.listdir(tmp_path))
    assert after == before
