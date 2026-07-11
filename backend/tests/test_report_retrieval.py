"""Retrieval tests for GET /analyses/{id} and /analyses/{id}/raw.

Phase 2A's `/analyses/single` no longer produces a persisted `AnalysisReport`
(see docs/api/api-contract.md) — it returns a temporary "accepted" response
and does not run analysis, so there is nothing yet to store or retrieve.
These endpoints are otherwise unchanged from Phase 1; a full report becomes
retrievable again once Phase 2B's pipeline populates the repository.
"""

from fastapi.testclient import TestClient


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
