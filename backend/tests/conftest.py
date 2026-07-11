"""Shared pytest fixtures.

Clears the cached in-memory repository between tests so analyses created in
one test don't leak into another, since `get_repository` is process-cached
via `lru_cache` for reuse across real requests. Also provides small
in-memory-generated image byte fixtures (PNG/JPEG/WEBP) so image-upload
tests need no external sample files and no network access, plus a
deterministic decoded image + mocked OCR dictionary for
app/metrics/ tests (no external Tesseract binary required).

The `client` fixture also overrides `get_analysis_service` (the actual
`Depends()`-injected callable in the routes — `get_llm_provider` itself is
only ever called as a plain nested function, not a FastAPI sub-dependency,
so overriding it directly via `app.dependency_overrides` would have no
effect) so its `LLMInterpretationService`/`UIClipEvaluationService` always
use `MockLLMProvider`/`MockUIClipProvider`, regardless of what a developer's
local `backend/.env` configures. Without this override, a real
`GEMINI_API_KEY` in `.env` would make API-level tests silently place real,
billed, non-deterministic network calls — CLAUDE.md ("Tests must not
require ... LLM providers") must hold no matter what a developer's local
environment happens to contain. (No real UIClip provider exists yet, so this
is defense-in-depth for Phase 5, not a live risk today.) The repository,
image validator/decoder, and metric engine are still the real, shared
instances so the rest of the pipeline is exercised normally.
"""

import io

import numpy as np
import pytest
import pytesseract
from fastapi.testclient import TestClient
from PIL import Image

from app.dependencies import (
    get_analysis_service,
    get_image_decoder,
    get_image_validator,
    get_metric_engine,
    get_repository,
)
from app.images.models import DecodedImage, ImageMetadata
from app.llm.mock_provider import MockLLMProvider
from app.llm.service import LLMInterpretationService
from app.main import app
from app.services.analysis_service import AnalysisService
from app.uiclip.mock_provider import MockUIClipProvider
from app.uiclip.service import UIClipEvaluationService


def _analysis_service_with_mock_providers() -> AnalysisService:
    return AnalysisService(
        repository=get_repository(),
        image_validator=get_image_validator(),
        image_decoder=get_image_decoder(),
        metric_engine=get_metric_engine(),
        llm_service=LLMInterpretationService(provider=MockLLMProvider(), provider_name="mock"),
        uiclip_service=UIClipEvaluationService(provider=MockUIClipProvider(), provider_name="mock"),
    )


@pytest.fixture
def client() -> TestClient:
    get_repository.cache_clear()
    app.dependency_overrides[get_analysis_service] = _analysis_service_with_mock_providers
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_analysis_service, None)


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


@pytest.fixture
def deterministic_cv_image() -> np.ndarray:
    """A fixed, uniformly light-gray 800x600 BGR canvas.

    A solid light background (>200 gray) means `analyze_elements`'s contour
    pass (threshold at 200, THRESH_BINARY_INV) finds zero contours, so every
    detected "element" comes solely from the mocked OCR fixture below —
    keeping metric-engine tests fully deterministic and independent of any
    image-content heuristics.
    """
    return np.full((600, 800, 3), 245, dtype=np.uint8)


@pytest.fixture
def mock_ocr_data() -> dict:
    """Deterministic pytesseract.image_to_data()-shaped OCR fixture.

    Covers: valid boxes above confidence 60 (indices 0, 1, 4, 5), one box
    below confidence 60 (index 2), one empty text value (index 3), multiple
    positions/sizes, and every valid box is smaller than 44px tall (small
    touch-target case). Four valid, well-separated elements are enough to
    exercise both grouping and Fitts's Law pairwise-distance calculations.
    """
    return {
        "text": ["Dashboard", "Settings", "ok", "", "Profile", "Save"],
        "conf": [95, 92, 40, 88, 85, 90],
        "left": [10, 200, 400, 20, 10, 600],
        "top": [10, 10, 10, 100, 300, 300],
        "width": [90, 70, 30, 40, 60, 40],
        "height": [20, 20, 20, 20, 20, 20],
    }


@pytest.fixture
def mock_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patches `pytesseract.image_to_data` with an empty OCR result.

    For API-level tests (via `TestClient`) that upload a real image and so
    reach `MetricEngine` through the live request path — keeps them hermetic
    per CLAUDE.md ("Tests must not require ... OCR"). Metric-value-accurate
    OCR fixtures belong in test_metric_engine.py; these tests only care that
    the request completes without needing the real Tesseract binary.
    """
    empty_ocr_data = {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}
    monkeypatch.setattr(pytesseract, "image_to_data", lambda *args, **kwargs: empty_ocr_data)


@pytest.fixture
def decoded_image(deterministic_cv_image: np.ndarray) -> DecodedImage:
    pil_image = Image.fromarray(deterministic_cv_image[:, :, ::-1])  # BGR -> RGB
    metadata = ImageMetadata(
        width=800,
        height=600,
        format="png",
        aspect_ratio=800 / 600,
        orientation="landscape",
        file_size_bytes=0,
    )
    return DecodedImage(
        raw_bytes=b"",
        cv2_image=deterministic_cv_image,
        pil_image=pil_image,
        metadata=metadata,
    )
