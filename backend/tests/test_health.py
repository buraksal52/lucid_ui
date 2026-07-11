from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_response_matches_schema(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    body = response.json()
    assert body == {"status": "ok", "service": "lucidui-backend", "version": "0.1.0"}
