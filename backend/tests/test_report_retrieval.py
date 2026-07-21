"""Retrieval tests for GET /analyses/{id} and /analyses/{id}/raw.

`POST /analyses/single` runs the deterministic metric engine, LLM
interpretation, and UIClip evaluation, and persists a full `AnalysisReport`,
so these endpoints have real data to retrieve — see
AnalysisService.create_single_analysis.
"""

import pytest
from fastapi.testclient import TestClient

CREATE_ENDPOINT = "/api/v1/analyses/single"

pytestmark = pytest.mark.usefixtures("mock_ocr")


def test_created_analysis_can_be_retrieved(client: TestClient, valid_png_bytes: bytes) -> None:
    created = client.post(CREATE_ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")}).json()
    analysis_id = created["analysisId"]

    response = client.get(f"/api/v1/analyses/{analysis_id}")
    assert response.status_code == 200
    assert response.json() == created


def test_raw_returns_same_report(client: TestClient, valid_png_bytes: bytes) -> None:
    created = client.post(CREATE_ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")}).json()
    analysis_id = created["analysisId"]

    response = client.get(f"/api/v1/analyses/{analysis_id}/raw")
    assert response.status_code == 200
    assert response.json() == created


def test_retrieved_report_contains_real_metric_output(client: TestClient, valid_png_bytes: bytes) -> None:
    created = client.post(CREATE_ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")}).json()
    analysis_id = created["analysisId"]

    response = client.get(f"/api/v1/analyses/{analysis_id}")
    body = response.json()
    assert body["lucidui"]["metricEngineVersion"] == "corrected-v3"
    assert isinstance(body["lucidui"]["weightedScore"], float)
    # LLM and UIClip mock providers both complete by default.
    assert body["status"] == "completed"


def test_llm_interpretation_is_persisted_and_retrievable(client: TestClient, valid_png_bytes: bytes) -> None:
    created = client.post(CREATE_ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")}).json()
    analysis_id = created["analysisId"]
    assert created["llmInterpretation"]["status"] == "completed"

    response = client.get(f"/api/v1/analyses/{analysis_id}")
    body = response.json()
    assert body["llmInterpretation"] == created["llmInterpretation"]
    assert body["llmInterpretation"]["status"] == "completed"
    assert body["llmInterpretation"]["provider"] == "mock"

    raw_response = client.get(f"/api/v1/analyses/{analysis_id}/raw")
    assert raw_response.json()["llmInterpretation"] == created["llmInterpretation"]


def test_uiclip_evaluation_is_persisted_and_retrievable(client: TestClient, valid_png_bytes: bytes) -> None:
    created = client.post(
        CREATE_ENDPOINT,
        files={"image": ("shot.png", valid_png_bytes, "image/png")},
        data={"description": "A profile settings page"},
    ).json()
    analysis_id = created["analysisId"]
    assert created["uiclip"]["status"] == "completed"
    assert created["uiclip"]["description"] == "A profile settings page"

    response = client.get(f"/api/v1/analyses/{analysis_id}")
    body = response.json()
    assert body["uiclip"] == created["uiclip"]
    assert body["uiclip"]["status"] == "completed"
    assert body["uiclip"]["modelVersion"] == "mock-uiclip-v1"

    raw_response = client.get(f"/api/v1/analyses/{analysis_id}/raw")
    assert raw_response.json()["uiclip"] == created["uiclip"]


def test_unknown_analysis_id_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_unknown_analysis_raw_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000/raw")
    assert response.status_code == 404


def test_unknown_analysis_error_follows_documented_format(client: TestClient) -> None:
    response = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000")
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "ANALYSIS_NOT_FOUND"
    assert isinstance(body["error"]["message"], str)
