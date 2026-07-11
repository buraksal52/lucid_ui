"""Shared pytest fixtures.

Clears the cached in-memory repository between tests so analyses created in
one test don't leak into another, since `get_repository` is process-cached
via `lru_cache` for reuse across real requests. Also provides small
in-memory-generated image byte fixtures (PNG/JPEG/WEBP) so image-upload
tests need no external sample files and no network access.
"""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.dependencies import get_repository
from app.main import app


@pytest.fixture
def client() -> TestClient:
    get_repository.cache_clear()
    return TestClient(app)


def _encode(width: int, height: int, format: str) -> bytes:
    image = Image.new("RGB", (width, height), color=(120, 200, 40))
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return buffer.getvalue()


@pytest.fixture
def valid_png_bytes() -> bytes:
    return _encode(64, 40, "PNG")


@pytest.fixture
def valid_jpeg_bytes() -> bytes:
    return _encode(64, 40, "JPEG")


@pytest.fixture
def valid_webp_bytes() -> bytes:
    return _encode(64, 40, "WEBP")


@pytest.fixture
def corrupted_png_bytes(valid_png_bytes: bytes) -> bytes:
    """A correct PNG signature followed by truncated/garbled body bytes."""
    return valid_png_bytes[:8] + b"\x00" * 40


@pytest.fixture
def mismatched_signature_bytes() -> bytes:
    """Bytes with no recognizable image file signature at all."""
    return b"not-an-image-" + b"\x00" * 32
