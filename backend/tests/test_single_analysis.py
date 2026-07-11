import uuid

from fastapi.testclient import TestClient

ENDPOINT = "/api/v1/analyses/single"


def test_default_request_succeeds(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={})
    assert response.status_code == 200
    body = response.json()
    assert body["context"] == "general"
    assert body["status"] == "completed"


def test_explicit_expert_context_succeeds(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={"context": "expert"})
    assert response.status_code == 200
    assert response.json()["context"] == "expert"


def test_camel_case_fields_are_accepted(client: TestClient) -> None:
    response = client.post(
        ENDPOINT,
        json={"context": "general", "description": "A dashboard", "runLlm": False, "runUiclip": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["llmInterpretation"]["status"] == "disabled"
    assert body["uiclip"]["status"] == "disabled"


def test_report_uses_camel_case_fields(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={})
    body = response.json()
    assert "schemaVersion" in body
    assert "analysisId" in body
    assert "imageMetadata" in body
    assert "llmInterpretation" in body
    assert "sizeBytes" in body["imageMetadata"]
    assert "weightedScore" in body["lucidui"]
    assert "descriptionSource" in body["uiclip"]
    # snake_case must not leak into the public contract
    assert "analysis_id" not in body
    assert "schema_version" not in body


def test_analysis_id_is_a_valid_uuid(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={})
    analysis_id = response.json()["analysisId"]
    uuid.UUID(analysis_id)  # raises ValueError if not a valid UUID


def test_mock_report_is_stored(client: TestClient) -> None:
    created = client.post(ENDPOINT, json={}).json()
    analysis_id = created["analysisId"]
    fetched = client.get(f"/api/v1/analyses/{analysis_id}")
    assert fetched.status_code == 200
    assert fetched.json()["analysisId"] == analysis_id


def test_description_source_is_user_when_description_exists(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={"description": "A checkout flow"})
    body = response.json()
    assert body["uiclip"]["descriptionSource"] == "user"
    assert body["uiclip"]["description"] == "A checkout flow"


def test_description_source_is_generic_when_absent(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={})
    body = response.json()
    assert body["uiclip"]["descriptionSource"] == "generic"
    assert body["uiclip"]["description"] == "A software user interface screenshot."


def test_llm_disabled_state(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={"runLlm": False})
    body = response.json()
    llm = body["llmInterpretation"]
    assert llm["status"] == "disabled"
    assert llm["provider"] is None
    assert llm["summary"] is None
    assert llm["observations"] == []
    assert llm["recommendations"] == []
    assert llm["limitations"] == []
    assert body["status"] == "partial_success"


def test_uiclip_disabled_state(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={"runUiclip": False})
    body = response.json()
    uiclip = body["uiclip"]
    assert uiclip["enabled"] is False
    assert uiclip["status"] == "disabled"
    assert uiclip["modelVersion"] is None
    assert uiclip["description"] is None
    assert uiclip["descriptionSource"] is None
    assert uiclip["qualityScore"] is None
    assert uiclip["normalizedQualityScore"] is None
    assert uiclip["observations"] == []
    assert uiclip["inferenceTimeMs"] == 0
    assert body["status"] == "partial_success"


def test_comparison_unavailable_when_uiclip_disabled(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={"runUiclip": False})
    body = response.json()
    assert body["comparison"]["agreementLevel"] == "unavailable"
    assert body["comparison"]["sharedFindings"] == []


def test_comparison_present_when_uiclip_enabled(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={"runUiclip": True})
    body = response.json()
    assert body["comparison"]["agreementLevel"] != "unavailable"
    assert body["comparison"]["uiclipNormalizedQualityScore"] is not None
