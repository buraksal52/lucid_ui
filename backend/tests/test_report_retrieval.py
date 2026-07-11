from fastapi.testclient import TestClient

ENDPOINT = "/api/v1/analyses/single"


def test_created_analysis_can_be_retrieved(client: TestClient) -> None:
    created = client.post(ENDPOINT, json={}).json()
    analysis_id = created["analysisId"]

    response = client.get(f"/api/v1/analyses/{analysis_id}")
    assert response.status_code == 200
    assert response.json() == created


def test_raw_returns_same_report_in_phase_1(client: TestClient) -> None:
    created = client.post(ENDPOINT, json={}).json()
    analysis_id = created["analysisId"]

    response = client.get(f"/api/v1/analyses/{analysis_id}/raw")
    assert response.status_code == 200
    assert response.json() == created


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
