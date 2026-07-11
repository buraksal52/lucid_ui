import uuid

from fastapi.testclient import TestClient

ENDPOINT = "/api/v1/analyses/single"


def test_valid_png_upload_succeeds(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["imageMetadata"]["format"] == "png"
    assert body["imageMetadata"]["width"] == 64
    assert body["imageMetadata"]["height"] == 40


def test_valid_jpeg_upload_succeeds(client: TestClient, valid_jpeg_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.jpg", valid_jpeg_bytes, "image/jpeg")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["imageMetadata"]["format"] == "jpeg"


def test_valid_webp_upload_succeeds(client: TestClient, valid_webp_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.webp", valid_webp_bytes, "image/webp")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["imageMetadata"]["format"] == "webp"


def test_response_uses_camel_case_fields(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", valid_png_bytes, "image/png")})
    body = response.json()
    assert "analysisId" in body
    assert "imageMetadata" in body
    assert "aspectRatio" in body["imageMetadata"]
    assert "fileSizeBytes" in body["imageMetadata"]
    assert "message" in body
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


def test_explicit_expert_context_succeeds(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(
        ENDPOINT,
        files={"image": ("shot.png", valid_png_bytes, "image/png")},
        data={"context": "expert"},
    )
    assert response.status_code == 200


def test_description_and_flags_are_accepted_but_do_not_affect_response(
    client: TestClient, valid_png_bytes: bytes
) -> None:
    response = client.post(
        ENDPOINT,
        files={"image": ("shot.png", valid_png_bytes, "image/png")},
        data={"description": "A dashboard", "runLlm": "false", "runUiclip": "false"},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"analysisId", "status", "imageMetadata", "message"}
