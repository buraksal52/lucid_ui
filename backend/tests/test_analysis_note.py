"""Tests for `AnalysisReport.note` (app.services.analysis_service).

The note must describe what actually happened during the UIClip stage for
that specific analysis, not a hardcoded assumption baked in at import time —
see CLAUDE.md UIClip Rules ("never fabricate", "independent evaluator").
Every scenario here uses a fake/mocked UIClip provider — none downloads or
runs a real model, per CLAUDE.md ("Tests must not require ... UIClip ...
GPU").
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL.Image import Image as PILImage

from app.dependencies import (
    get_analysis_service,
    get_image_decoder,
    get_image_validator,
    get_metric_engine,
    get_repository,
)
from app.llm.mock_provider import MockLLMProvider
from app.llm.service import LLMInterpretationService
from app.main import app
from app.schemas.uiclip import UIClipResult
from app.services.analysis_service import AnalysisService
from app.uiclip.exceptions import UIClipEvaluationError, UIClipProviderUnavailableError
from app.uiclip.mock_provider import MockUIClipProvider
from app.uiclip.service import UIClipEvaluationService

ENDPOINT = "/api/v1/analyses/single"


class _FakeRealProvider:
    """Stands in for a real (non-mock) completed UIClip provider."""

    name = "huggingface"

    def evaluate(self, image: PILImage, description: str) -> dict[str, Any]:
        return {
            "model_version": "biglab/uiclip_jitteredwebsites-2-224-paraphrased",
            "raw_score": 12.3,
            "observations": [],
        }


class _FakeUnavailableProvider:
    name = "huggingface"

    def evaluate(self, image: PILImage, description: str) -> dict[str, Any]:
        raise UIClipProviderUnavailableError("test: provider unreachable")


class _FakeFailedProvider:
    name = "huggingface"

    def evaluate(self, image: PILImage, description: str) -> dict[str, Any]:
        raise UIClipEvaluationError("test: evaluation failed")


def _override_with_uiclip_provider(provider) -> None:
    def _build() -> AnalysisService:
        return AnalysisService(
            repository=get_repository(),
            image_validator=get_image_validator(),
            image_decoder=get_image_decoder(),
            metric_engine=get_metric_engine(),
            llm_service=LLMInterpretationService(provider=MockLLMProvider(), provider_name="mock"),
            uiclip_service=UIClipEvaluationService(provider=provider, provider_name=provider.name if provider else "mock"),
        )

    app.dependency_overrides[get_analysis_service] = _build


@pytest.fixture(autouse=True)
def _clear_repository_cache():
    get_repository.cache_clear()
    yield
    app.dependency_overrides.pop(get_analysis_service, None)


@pytest.mark.usefixtures("mock_ocr")
def test_note_says_mock_when_mock_provider_completes(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(MockUIClipProvider())
    with TestClient(app) as client:
        response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    assert response.status_code == 200
    note = response.json()["note"]
    assert "mock evaluator" in note
    assert "not the real UIClip model" in note
    assert "not been computed" in note


@pytest.mark.usefixtures("mock_ocr")
def test_note_does_not_mention_mock_when_real_provider_completes(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(_FakeRealProvider())
    with TestClient(app) as client:
        response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    assert response.status_code == 200
    body = response.json()
    assert body["uiclip"]["status"] == "completed"
    note = body["note"]
    assert "mock" not in note.lower()
    assert "real UIClip model" in note


@pytest.mark.usefixtures("mock_ocr")
def test_note_is_honest_when_uiclip_provider_unavailable(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(_FakeUnavailableProvider())
    with TestClient(app) as client:
        response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    assert response.status_code == 200
    body = response.json()
    assert body["uiclip"]["status"] == "unavailable"
    note = body["note"]
    assert "mock" not in note.lower()
    assert "unavailable" in note.lower()


@pytest.mark.usefixtures("mock_ocr")
def test_note_is_honest_when_uiclip_evaluation_fails(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(_FakeFailedProvider())
    with TestClient(app) as client:
        response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    assert response.status_code == 200
    body = response.json()
    assert body["uiclip"]["status"] == "failed"
    note = body["note"]
    assert "mock" not in note.lower()
    assert "failed" in note.lower()


@pytest.mark.usefixtures("mock_ocr")
def test_note_reflects_disabled_uiclip_for_this_request(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(MockUIClipProvider())
    with TestClient(app) as client:
        response = client.post(
            ENDPOINT,
            files={"image": ("shot.png", valid_png_bytes, "image/png")},
            data={"runUiclip": "false"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["uiclip"]["status"] == "disabled"
    note = body["note"]
    assert "mock" not in note.lower()
    assert "not requested" in note.lower()


def test_build_note_unit_covers_every_uiclip_status() -> None:
    """Direct unit coverage of `AnalysisService._build_note` for each
    documented `UIClipStatus`, independent of the HTTP layer."""

    def _result(**overrides: Any) -> UIClipResult:
        defaults = dict(
            enabled=True,
            status="completed",
            model_version=None,
            description=None,
            description_source=None,
            quality_score=None,
            normalized_quality_score=None,
            observations=[],
            inference_time_ms=0,
        )
        defaults.update(overrides)
        return UIClipResult(**defaults)

    disabled_note = AnalysisService._build_note(_result(status="disabled", enabled=False))
    assert "not requested" in disabled_note

    unavailable_note = AnalysisService._build_note(_result(status="unavailable"))
    assert "unavailable" in unavailable_note.lower()

    failed_note = AnalysisService._build_note(_result(status="failed"))
    assert "failed" in failed_note.lower()

    mock_note = AnalysisService._build_note(_result(status="completed", model_version="mock-uiclip-v1"))
    assert "mock evaluator" in mock_note

    real_note = AnalysisService._build_note(_result(status="completed", model_version="biglab/uiclip-real"))
    assert "mock" not in real_note.lower()
    assert "real UIClip model" in real_note

    for note in (disabled_note, unavailable_note, failed_note, mock_note, real_note):
        assert "not been computed" in note
