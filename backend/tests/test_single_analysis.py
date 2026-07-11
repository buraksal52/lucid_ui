import uuid

import pytest
import pytesseract
from fastapi.testclient import TestClient

ENDPOINT = "/api/v1/analyses/single"

pytestmark = pytest.mark.usefixtures("mock_ocr")


def test_valid_png_upload_succeeds(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial_success"
    assert body["imageMetadata"]["format"] == "png"
    assert body["imageMetadata"]["width"] == 64
    assert body["imageMetadata"]["height"] == 40


def test_valid_jpeg_upload_succeeds(client: TestClient, valid_jpeg_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.jpg", valid_jpeg_bytes, "image/jpeg")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial_success"
    assert body["imageMetadata"]["format"] == "jpeg"


def test_valid_webp_upload_succeeds(client: TestClient, valid_webp_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.webp", valid_webp_bytes, "image/webp")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial_success"
    assert body["imageMetadata"]["format"] == "webp"


def test_response_uses_camel_case_fields(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    assert "analysisId" in body
    assert "schemaVersion" in body
    assert "imageMetadata" in body
    assert "aspectRatio" in body["imageMetadata"]
    assert "fileSizeBytes" in body["imageMetadata"]
    assert "llmInterpretation" in body
    assert "weightedScore" in body["lucidui"]
    assert "metricEngineVersion" in body["lucidui"]
    # snake_case must not leak into the public contract
    assert "analysis_id" not in body
    assert "image_metadata" not in body


def test_analysis_id_is_a_valid_uuid(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    uuid.UUID(response.json()["analysisId"])  # raises ValueError if not a valid UUID


def test_image_metadata_reports_aspect_ratio_and_orientation(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    metadata = response.json()["imageMetadata"]
    assert metadata["aspectRatio"] == 1.6  # 64 / 40
    assert metadata["orientation"] == "landscape"
    assert metadata["fileSizeBytes"] == len(valid_png_bytes)


def test_default_context_is_general(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    assert response.status_code == 200
    assert response.json()["context"] == "general"


def test_explicit_expert_context_succeeds(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(
        ENDPOINT,
        files={"image": ("shot.png", valid_png_bytes, "image/png")},
        data={"context": "expert"},
    )
    assert response.status_code == 200
    assert response.json()["context"] == "expert"


def test_description_and_flags_are_accepted_and_do_not_break_the_request(
    client: TestClient, valid_png_bytes: bytes
) -> None:
    response = client.post(
        ENDPOINT,
        files={"image": ("shot.png", valid_png_bytes, "image/png")},
        data={"description": "A dashboard", "runLlm": "false", "runUiclip": "false"},
    )
    assert response.status_code == 200


def test_metric_engine_output_is_embedded_in_the_report(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    lucidui = body["lucidui"]
    assert lucidui["metricEngineVersion"] == "legacy-v1"
    assert lucidui["scoreName"] == "LucidUI Composite Signal Score"
    assert set(lucidui["raw"].keys()) == {
        "contrast",
        "clutter",
        "elements",
        "groups",
        "textDensity",
        "whitespaceAlignment",
    }
    assert isinstance(lucidui["weightedScore"], float)


def test_llm_and_uiclip_sections_are_disabled_placeholders(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    assert body["llmInterpretation"]["status"] == "disabled"
    assert body["llmInterpretation"]["observations"] == []
    assert body["uiclip"]["enabled"] is False
    assert body["uiclip"]["status"] == "disabled"
    assert body["comparison"]["agreementLevel"] == "unavailable"
    assert body["comparison"]["luciduiWeightedScore"] == body["lucidui"]["weightedScore"]


def test_metric_engine_runs_exactly_once_per_upload(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, valid_png_bytes: bytes
) -> None:
    calls = {"count": 0}

    def counting_ocr(*args, **kwargs):
        calls["count"] += 1
        return {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}

    monkeypatch.setattr(pytesseract, "image_to_data", counting_ocr)

    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    assert response.status_code == 200
    assert calls["count"] == 1


def test_ocr_failure_propagates_as_structured_analysis_failed_error(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, valid_png_bytes: bytes
) -> None:
    def failing_ocr(*args, **kwargs):
        raise RuntimeError("tesseract binary not found")

    monkeypatch.setattr(pytesseract, "image_to_data", failing_ocr)

    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "ANALYSIS_FAILED"
