"""API-level tests for `AnalysisReport.presentation` (app.presentation).

Exercises the presentation layer through the real HTTP pipeline (upload ->
metrics -> LLM -> UIClip -> presentation -> persist -> retrieve), using the
same fake/mock UIClip providers pattern as test_analysis_note.py — every
scenario here is offline, per CLAUDE.md ("Tests must not require ...
external APIs ... GPU ... UIClip").
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
from app.services.analysis_service import AnalysisService
from app.uiclip.exceptions import UIClipEvaluationError, UIClipProviderUnavailableError
from app.uiclip.mock_provider import MockUIClipProvider
from app.uiclip.service import UIClipEvaluationService

ENDPOINT = "/api/v1/analyses/single"

_EXPECTED_SECTION_IDS = [
    "contrast",
    "elements",
    "grouping",
    "text-density",
    "colorfulness",
    "fitts-law",
    "visual-balance",
]


class _FakeRealProvider:
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
            uiclip_service=UIClipEvaluationService(
                provider=provider, provider_name=provider.name if provider else "mock"
            ),
        )

    app.dependency_overrides[get_analysis_service] = _build


@pytest.fixture(autouse=True)
def _clear_repository_cache():
    get_repository.cache_clear()
    yield
    app.dependency_overrides.pop(get_analysis_service, None)


@pytest.mark.usefixtures("mock_ocr")
def test_presentation_is_present_with_fixed_metric_section_order(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(MockUIClipProvider())
    with TestClient(app) as client:
        response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    assert response.status_code == 200
    body = response.json()
    presentation = body["presentation"]
    assert [section["id"] for section in presentation["metricSections"]] == _EXPECTED_SECTION_IDS
    assert presentation["context"] == body["context"]
    assert presentation["title"]
    assert presentation["closingNote"] == body["note"]


@pytest.mark.usefixtures("mock_ocr")
def test_original_lucidui_and_llm_fields_are_unchanged_by_presentation(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(MockUIClipProvider())
    with TestClient(app) as client:
        response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    assert set(body["lucidui"].keys()) == {
        "raw",
        "normalized",
        "additionalSignals",
        "weightedScore",
        "scoreName",
        "metricEngineVersion",
    }
    assert body["presentation"]["composite"]["value"] == body["lucidui"]["weightedScore"]
    assert body["llmInterpretation"]["summary"] is not None
    assert body["presentation"]["summary"] == body["llmInterpretation"]["summary"]


@pytest.mark.usefixtures("mock_ocr")
def test_presentation_composite_score_display(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(MockUIClipProvider())
    with TestClient(app) as client:
        response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    composite = body["presentation"]["composite"]
    weighted_score = body["lucidui"]["weightedScore"]
    assert composite["rawDisplay"] == f"{weighted_score:.1f} / 100"
    assert "not a quality" in composite["explanation"].lower()


@pytest.mark.usefixtures("mock_ocr")
def test_presentation_uiclip_summary_for_mock_provider(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(MockUIClipProvider())
    with TestClient(app) as client:
        response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    card = body["presentation"]["uiclipSummary"]
    assert card["status"] == "completed"
    assert card["modelId"] == "mock-uiclip-v1"
    assert card["rawScoreDisplay"] is not None
    assert card["scoreType"] == "Learned raw model score"
    assert card["comparableToLucidui"] is False
    assert "not directly comparable" in card["comparabilityNote"]


@pytest.mark.usefixtures("mock_ocr")
def test_presentation_uiclip_summary_for_real_provider_with_user_description(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(_FakeRealProvider())
    with TestClient(app) as client:
        response = client.post(
            ENDPOINT,
            files={"image": ("shot.png", valid_png_bytes, "image/png")},
            data={"description": "A settings page"},
        )
    body = response.json()
    card = body["presentation"]["uiclipSummary"]
    assert card["status"] == "completed"
    assert card["modelId"] == "biglab/uiclip_jitteredwebsites-2-224-paraphrased"
    assert card["userDescription"] == "A settings page"
    assert card["rawScoreDisplay"] == "12.30"
    assert card["scoreType"] == "Learned raw model score"


@pytest.mark.usefixtures("mock_ocr")
def test_presentation_uiclip_summary_for_unavailable_provider(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(_FakeUnavailableProvider())
    with TestClient(app) as client:
        response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    card = body["presentation"]["uiclipSummary"]
    assert card["status"] == "unavailable"
    assert card["modelId"] is None
    assert card["rawScoreDisplay"] is None
    assert card["scoreType"] is None


@pytest.mark.usefixtures("mock_ocr")
def test_presentation_uiclip_summary_for_failed_provider(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(_FakeFailedProvider())
    with TestClient(app) as client:
        response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    card = body["presentation"]["uiclipSummary"]
    assert card["status"] == "failed"
    assert card["rawScoreDisplay"] is None


@pytest.mark.usefixtures("mock_ocr")
def test_presentation_uiclip_summary_for_disabled_request(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(MockUIClipProvider())
    with TestClient(app) as client:
        response = client.post(
            ENDPOINT,
            files={"image": ("shot.png", valid_png_bytes, "image/png")},
            data={"runUiclip": "false"},
        )
    body = response.json()
    card = body["presentation"]["uiclipSummary"]
    assert card["status"] == "disabled"
    assert card["modelId"] is None
    assert card["rawScoreDisplay"] is None


@pytest.mark.usefixtures("mock_ocr")
def test_presentation_round_trips_through_repository_get_and_raw(valid_png_bytes: bytes) -> None:
    _override_with_uiclip_provider(MockUIClipProvider())
    with TestClient(app) as client:
        created = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")}).json()
        analysis_id = created["analysisId"]

        fetched = client.get(f"/api/v1/analyses/{analysis_id}").json()
        raw = client.get(f"/api/v1/analyses/{analysis_id}/raw").json()

    assert fetched["presentation"] == created["presentation"]
    assert raw["presentation"] == created["presentation"]


def test_presentation_report_schema_is_visible_in_openapi() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
    components = schema["components"]["schemas"]
    assert "PresentationReport" in components
    assert "presentation" in components["AnalysisReport"]["properties"]
    assert "metricSections" in components["PresentationReport"]["properties"]
    assert "uiclipSummary" in components["PresentationReport"]["properties"]
