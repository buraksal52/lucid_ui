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
    # Both LLM and UIClip mock providers complete by default, so the
    # top-level status is "completed" per report-schema.md's own semantics.
    assert body["status"] == "completed"
    assert body["imageMetadata"]["format"] == "png"
    assert body["imageMetadata"]["width"] == 64
    assert body["imageMetadata"]["height"] == 40


def test_valid_jpeg_upload_succeeds(client: TestClient, valid_jpeg_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.jpg", valid_jpeg_bytes, "image/jpeg")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["imageMetadata"]["format"] == "jpeg"


def test_valid_webp_upload_succeeds(client: TestClient, valid_webp_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.webp", valid_webp_bytes, "image/webp")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
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


def test_run_uiclip_false_disables_uiclip_evaluation(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(
        ENDPOINT,
        files={"image": ("shot.png", valid_png_bytes, "image/png")},
        data={"description": "A dashboard", "runUiclip": "false"},
    )
    assert response.status_code == 200
    body = response.json()
    uiclip = body["uiclip"]
    assert uiclip["enabled"] is False
    assert uiclip["status"] == "disabled"
    assert uiclip["modelVersion"] is None
    assert uiclip["description"] is None
    assert uiclip["descriptionSource"] is None
    assert uiclip["inferenceTimeMs"] == 0
    assert body["timings"]["uiclipMs"] == 0


def test_metric_engine_output_is_embedded_in_the_report(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    lucidui = body["lucidui"]
    assert lucidui["metricEngineVersion"] == "corrected-v3"
    assert lucidui["scoreName"] == "LucidUI Composite Signal Score"
    assert set(lucidui["raw"].keys()) == {
        "resolution",
        "contrast",
        "clutter",
        "elements",
        "groups",
        "textDensity",
        "whitespaceAlignment",
    }
    assert isinstance(lucidui["weightedScore"], float)


def test_uiclip_evaluation_completes_by_default_via_mock_provider(
    client: TestClient, valid_png_bytes: bytes
) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    uiclip = body["uiclip"]
    assert uiclip["enabled"] is True
    assert uiclip["status"] == "completed"
    assert uiclip["modelVersion"] == "mock-uiclip-v1"
    assert uiclip["descriptionSource"] == "generic"
    assert uiclip["description"] == "A software user interface screenshot."
    assert isinstance(uiclip["qualityScore"], float)
    # No verified official 0-100/0-1 normalization exists — must stay null.
    assert uiclip["normalizedQualityScore"] is None
    assert len(uiclip["observations"]) > 0
    assert body["timings"]["uiclipMs"] >= 0


def test_uiclip_uses_the_submitted_description(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(
        ENDPOINT,
        files={"image": ("shot.png", valid_png_bytes, "image/png")},
        data={"description": "A checkout flow with a payment form"},
    )
    body = response.json()
    uiclip = body["uiclip"]
    assert uiclip["descriptionSource"] == "user"
    assert uiclip["description"] == "A checkout flow with a payment form"


def test_comparison_section_remains_unavailable(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    comparison = body["comparison"]
    assert comparison["agreementLevel"] == "unavailable"
    assert comparison["absoluteScoreDifference"] is None
    assert comparison["sharedFindings"] == []
    assert comparison["luciduiOnlyFindings"] == []
    assert comparison["uiclipOnlyFindings"] == []
    assert comparison["luciduiWeightedScore"] == body["lucidui"]["weightedScore"]


def test_llm_interpretation_completes_by_default_via_mock_provider(
    client: TestClient, valid_png_bytes: bytes
) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    llm = body["llmInterpretation"]
    assert llm["status"] == "completed"
    assert llm["provider"] == "mock"
    assert llm["summary"] is not None
    assert len(llm["observations"]) > 0
    for observation in llm["observations"]:
        assert len(observation["metricEvidence"]) > 0


def test_run_llm_false_disables_llm_interpretation(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(
        ENDPOINT,
        files={"image": ("shot.png", valid_png_bytes, "image/png")},
        data={"runLlm": "false"},
    )
    assert response.status_code == 200
    body = response.json()
    llm = body["llmInterpretation"]
    assert llm["status"] == "disabled"
    assert llm["provider"] is None
    assert llm["summary"] is None
    assert llm["observations"] == []


def test_uiclip_provider_runs_exactly_once_per_upload_and_receives_image_and_description(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, valid_png_bytes: bytes
) -> None:
    from PIL.Image import Image as PILImage

    from app.uiclip.mock_provider import MockUIClipProvider

    calls: list[tuple] = []
    original_evaluate = MockUIClipProvider.evaluate

    def counting_evaluate(self, image, description):
        calls.append((image, description))
        return original_evaluate(self, image, description)

    monkeypatch.setattr(MockUIClipProvider, "evaluate", counting_evaluate)

    response = client.post(
        ENDPOINT,
        files={"image": ("shot.png", valid_png_bytes, "image/png")},
        data={"description": "A settings page"},
    )
    assert response.status_code == 200
    assert len(calls) == 1
    received_image, received_description = calls[0]
    assert isinstance(received_image, PILImage)
    assert received_description == "A settings page"


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


def test_ocr_failure_still_returns_analysis_with_empty_ocr_metrics(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, valid_png_bytes: bytes
) -> None:
    def failing_ocr(*args, **kwargs):
        raise RuntimeError("tesseract binary not found")

    monkeypatch.setattr(pytesseract, "image_to_data", failing_ocr)

    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    assert response.status_code == 200
    body = response.json()
    assert body["lucidui"]["raw"]["contrast"]["averageContrastRatio"] is None
    assert body["lucidui"]["raw"]["contrast"]["regionsAnalyzed"] == 0
    assert body["lucidui"]["raw"]["elements"]["ocrBasedCount"] == 0
    assert body["lucidui"]["raw"]["textDensity"]["wordsDetected"] == 0
