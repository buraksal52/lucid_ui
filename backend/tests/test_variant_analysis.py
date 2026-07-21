import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import Response

ENDPOINT = "/api/v1/analyses/variants"

pytestmark = pytest.mark.usefixtures("mock_ocr")


def _post_variants(
    client: TestClient,
    image_a: bytes,
    image_b: bytes,
    content_type_a: str = "image/png",
    content_type_b: str = "image/png",
    **data,
) -> Response:
    return client.post(
        ENDPOINT,
        files={
            "imageA": ("variant-a.png", image_a, content_type_a),
            "imageB": ("variant-b.png", image_b, content_type_b),
        },
        data=data,
    )


def test_valid_two_image_upload_succeeds(
    client: TestClient, valid_png_bytes: bytes, valid_jpeg_bytes: bytes
) -> None:
    response = _post_variants(client, valid_png_bytes, valid_jpeg_bytes, content_type_b="image/jpeg")
    assert response.status_code == 200
    body = response.json()

    assert body["mode"] == "variants"
    assert body["variantA"]["status"] == "completed"
    assert body["variantB"]["status"] == "completed"
    assert body["status"] == "completed"
    assert len(body["deltas"]["metricDeltas"]) == 10


def test_response_uses_camel_case_fields(
    client: TestClient, valid_png_bytes: bytes, valid_jpeg_bytes: bytes
) -> None:
    response = _post_variants(client, valid_png_bytes, valid_jpeg_bytes, content_type_b="image/jpeg")
    body = response.json()

    assert "analysisId" in body
    assert "variantA" in body
    assert "variantB" in body
    assert "deltas" in body
    assert "compositeScoreDelta" in body["deltas"]
    assert "metricDeltas" in body["deltas"]
    assert "normalizedScoreDelta" in body["deltas"]["metricDeltas"][0]
    # snake_case must not leak into the public contract
    assert "variant_a" not in body
    assert "composite_score_delta" not in body["deltas"]


def test_analysis_ids_are_distinct_valid_uuids(
    client: TestClient, valid_png_bytes: bytes, valid_jpeg_bytes: bytes
) -> None:
    response = _post_variants(client, valid_png_bytes, valid_jpeg_bytes, content_type_b="image/jpeg")
    body = response.json()

    envelope_id = uuid.UUID(body["analysisId"])
    variant_a_id = uuid.UUID(body["variantA"]["analysisId"])
    variant_b_id = uuid.UUID(body["variantB"]["analysisId"])
    assert len({envelope_id, variant_a_id, variant_b_id}) == 3


def test_identical_images_produce_zero_composite_delta(
    client: TestClient, valid_png_bytes: bytes
) -> None:
    response = _post_variants(client, valid_png_bytes, valid_png_bytes)
    body = response.json()

    assert body["deltas"]["compositeScoreDelta"] == 0.0
    for metric_delta in body["deltas"]["metricDeltas"]:
        if metric_delta["normalizedScoreDelta"] is not None:
            assert metric_delta["normalizedScoreDelta"] == 0.0
            assert metric_delta["direction"] == "equal"


def test_variants_are_independently_retrievable(
    client: TestClient, valid_png_bytes: bytes, valid_jpeg_bytes: bytes
) -> None:
    response = _post_variants(client, valid_png_bytes, valid_jpeg_bytes, content_type_b="image/jpeg")
    body = response.json()

    get_a = client.get(f"/api/v1/analyses/{body['variantA']['analysisId']}")
    get_b = client.get(f"/api/v1/analyses/{body['variantB']['analysisId']}")
    assert get_a.status_code == 200
    assert get_b.status_code == 200
    assert get_a.json()["analysisId"] == body["variantA"]["analysisId"]
    assert get_b.json()["analysisId"] == body["variantB"]["analysisId"]


def test_missing_image_b_returns_structured_422(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"imageA": ("a.png", valid_png_bytes, "image/png")})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_context_returns_structured_422(
    client: TestClient, valid_png_bytes: bytes, valid_jpeg_bytes: bytes
) -> None:
    response = _post_variants(client, valid_png_bytes, valid_jpeg_bytes, content_type_b="image/jpeg", context="nonexistent")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_CONTEXT"


def test_unsupported_mime_type_on_one_image_returns_structured_415(
    client: TestClient, valid_png_bytes: bytes
) -> None:
    response = client.post(
        ENDPOINT,
        files={
            "imageA": ("a.png", valid_png_bytes, "image/png"),
            "imageB": ("b.gif", b"GIF89a" + b"\x00" * 20, "image/gif"),
        },
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_run_uiclip_false_disables_uiclip_for_both_variants(
    client: TestClient, valid_png_bytes: bytes, valid_jpeg_bytes: bytes
) -> None:
    response = _post_variants(client, valid_png_bytes, valid_jpeg_bytes, content_type_b="image/jpeg", runUiclip="false")
    body = response.json()

    assert body["variantA"]["uiclip"]["status"] == "disabled"
    assert body["variantB"]["uiclip"]["status"] == "disabled"
    assert body["deltas"]["uiclipRawScoreDelta"] is None
    assert body["deltas"]["uiclipRawScoreDeltaDisplay"] == "No data available"


def test_run_llm_false_disables_llm_for_both_variants_and_is_partial_success(
    client: TestClient, valid_png_bytes: bytes, valid_jpeg_bytes: bytes
) -> None:
    response = _post_variants(client, valid_png_bytes, valid_jpeg_bytes, content_type_b="image/jpeg", runLlm="false")
    body = response.json()

    assert body["variantA"]["llmInterpretation"]["status"] == "disabled"
    assert body["variantB"]["llmInterpretation"]["status"] == "disabled"
    assert body["variantA"]["status"] == "partial_success"
    assert body["status"] == "partial_success"


def test_direction_never_uses_verdict_language(
    client: TestClient, valid_png_bytes: bytes, valid_jpeg_bytes: bytes
) -> None:
    response = _post_variants(client, valid_png_bytes, valid_jpeg_bytes, content_type_b="image/jpeg")
    body = response.json()

    allowed_directions = {"higher", "lower", "equal", "not_available"}
    for metric_delta in body["deltas"]["metricDeltas"]:
        assert metric_delta["direction"] in allowed_directions
