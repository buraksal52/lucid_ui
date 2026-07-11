from fastapi.testclient import TestClient

ENDPOINT = "/api/v1/analyses/single"


def test_invalid_context_returns_structured_422(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(
        ENDPOINT,
        files={"image": ("shot.png", valid_png_bytes, "image/png")},
        data={"context": "nonexistent"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_CONTEXT"
    assert "error" in body


def test_invalid_field_type_returns_structured_422(client: TestClient, valid_png_bytes: bytes) -> None:
    response = client.post(
        ENDPOINT,
        files={"image": ("shot.png", valid_png_bytes, "image/png")},
        data={"runLlm": "not-a-boolean"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)


def test_missing_image_returns_structured_422(client: TestClient) -> None:
    response = client.post(ENDPOINT, data={"context": "general"})
    assert response.status_code == 422
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_unsupported_mime_type_returns_structured_415(client: TestClient) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.gif", b"GIF89a" + b"\x00" * 20, "image/gif")})
    assert response.status_code == 415
    body = response.json()
    assert body["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_oversized_image_returns_structured_413(client: TestClient) -> None:
    from app.config import get_settings

    max_bytes = get_settings().max_upload_size_bytes
    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * max_bytes
    response = client.post(ENDPOINT, files={"image": ("shot.png", oversized, "image/png")})
    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "FILE_TOO_LARGE"


def test_corrupted_image_returns_structured_422(client: TestClient, corrupted_png_bytes: bytes) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", corrupted_png_bytes, "image/png")})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_IMAGE"


def test_mismatched_signature_returns_structured_422(client: TestClient, mismatched_signature_bytes: bytes) -> None:
    response = client.post(
        ENDPOINT, files={"image": ("shot.png", mismatched_signature_bytes, "image/png")}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_IMAGE"


def test_empty_upload_returns_structured_422(client: TestClient) -> None:
    response = client.post(ENDPOINT, files={"image": ("shot.png", b"", "image/png")})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_IMAGE"


def test_all_error_responses_have_top_level_error_field(
    client: TestClient, valid_png_bytes: bytes
) -> None:
    responses = [
        client.post(
            ENDPOINT,
            files={"image": ("shot.png", valid_png_bytes, "image/png")},
            data={"context": "nonexistent"},
        ),
        client.post(ENDPOINT, files={"image": ("shot.gif", b"GIF89a" + b"\x00" * 20, "image/gif")}),
        client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000"),
    ]
    for response in responses:
        body = response.json()
        assert "error" in body
        assert set(body["error"].keys()) == {"code", "message", "details"}


def test_error_response_never_returns_html(client: TestClient) -> None:
    response = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000")
    assert response.headers["content-type"].startswith("application/json")
