from fastapi.testclient import TestClient

ENDPOINT = "/api/v1/analyses/single"


def test_invalid_context_returns_structured_422(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={"context": "nonexistent"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_CONTEXT"
    assert "error" in body


def test_invalid_field_type_returns_structured_422(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={"runLlm": "not-a-boolean"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)


def test_malformed_json_returns_structured_json_error(client: TestClient) -> None:
    response = client.post(
        ENDPOINT,
        content="{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_all_error_responses_have_top_level_error_field(client: TestClient) -> None:
    responses = [
        client.post(ENDPOINT, json={"context": "nonexistent"}),
        client.post(ENDPOINT, json={"runUiclip": 12345}),
        client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000"),
    ]
    for response in responses:
        body = response.json()
        assert "error" in body
        assert set(body["error"].keys()) == {"code", "message", "details"}


def test_error_response_never_returns_html(client: TestClient) -> None:
    response = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000")
    assert response.headers["content-type"].startswith("application/json")
