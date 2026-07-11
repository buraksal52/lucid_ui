"""Tests for the LLM interpretation layer (app.llm).

Every test here uses `MockLLMProvider` or a small fake/monkeypatched
provider — none makes a real network call to Gemini or any other LLM API,
per CLAUDE.md ("Tests must not require ... LLM providers").
"""

import inspect
import json
from typing import Any

import pytest

from app.llm.exceptions import LLMInterpretationError, LLMProviderUnavailableError
from app.llm.gemini_provider import GeminiLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.models import LLMStructuredOutput
from app.llm.prompt import build_prompt
from app.llm.service import LLMInterpretationService
from app.metrics.models import DeterministicMetricResult
from app.schemas.common import AnalysisContext, LLMStatus


@pytest.fixture
def metric_result() -> DeterministicMetricResult:
    return DeterministicMetricResult(
        raw={
            "contrast": {
                "averageContrastRatio": 4.1,
                "regionsAnalyzed": 3,
                "regionsBelowAAThreshold": 1,
                "source": "WCAG 2.1 AA (4.5:1 normal text)",
            },
            "clutter": {"edgeDensity": 0.12, "source": "Rosenholtz, Li & Nakano (2007) - Edge Density proxy"},
        },
        normalized={"contrast": 55.0, "clutter": 70.0},
        additional_signals={"colorfulness": {"colorfulnessScore": 32.4}},
        weighted_score=48.5,
    )


# ---------- Prompt construction: JSON only, never a screenshot ----------


def test_build_prompt_signature_has_no_image_parameter() -> None:
    sig = inspect.signature(build_prompt)
    assert set(sig.parameters) == {"metric_result", "context"}


def test_build_prompt_contains_only_metric_json_and_context(metric_result: DeterministicMetricResult) -> None:
    _, user_prompt = build_prompt(metric_result, AnalysisContext.EXPERT)
    assert "expert" in user_prompt
    assert "averageContrastRatio" in user_prompt
    assert "4.1" in user_prompt
    for forbidden in ["screenshot.png", "base64", "data:image", "cv2_image", "pil_image", "raw_bytes"]:
        assert forbidden not in user_prompt.lower()


def test_build_prompt_does_not_mutate_metric_result(metric_result: DeterministicMetricResult) -> None:
    before = metric_result.model_copy(deep=True)
    build_prompt(metric_result, AnalysisContext.GENERAL)
    assert metric_result == before


def test_system_prompt_instructs_hedged_non_verdict_language() -> None:
    system_prompt, _ = build_prompt(
        DeterministicMetricResult(raw={}, normalized={}, additional_signals={}, weighted_score=0.0),
        AnalysisContext.GENERAL,
    )
    lowered = system_prompt.lower()
    for required_phrase in ["proxy", "metric_evidence", "never invent", "screenshot"]:
        assert required_phrase.lower() in lowered

    # Verdict-language words are only allowed to appear inside the negative
    # instruction lines that forbid them, never used or endorsed elsewhere.
    lines = lowered.splitlines()
    instruction_markers = ("- never call a ui", "- avoid words like:")
    instruction_lines = [line for line in lines if line.strip().startswith(instruction_markers)]
    other_lines = "\n".join(line for line in lines if not line.strip().startswith(instruction_markers))
    assert len(instruction_lines) == 2
    for forbidden_word in ["beautiful", "ugly", "perfect", "terrible"]:
        assert any(forbidden_word in line for line in instruction_lines)
        assert forbidden_word not in other_lines


# ---------- Mock provider ----------


def test_mock_provider_returns_valid_structured_output() -> None:
    result = MockLLMProvider().complete("system", "user")
    LLMStructuredOutput.model_validate(result)  # must not raise


def test_mock_provider_is_deterministic() -> None:
    provider = MockLLMProvider()
    assert provider.complete("a", "b") == provider.complete("c", "d")


def test_mock_provider_every_observation_has_metric_evidence() -> None:
    result = MockLLMProvider().complete("system", "user")
    for observation in result["observations"]:
        assert len(observation["metric_evidence"]) > 0


# ---------- Service: successful interpretation ----------


def test_successful_interpretation(metric_result: DeterministicMetricResult) -> None:
    service = LLMInterpretationService(provider=MockLLMProvider(), provider_name="mock")
    result = service.interpret(metric_result, AnalysisContext.GENERAL)
    assert result.status == LLMStatus.COMPLETED
    assert result.provider == "mock"
    assert result.summary is not None
    assert len(result.observations) > 0
    for observation in result.observations:
        assert len(observation.metric_evidence) > 0


def test_deterministic_metrics_remain_unchanged_after_interpretation(
    metric_result: DeterministicMetricResult,
) -> None:
    before = metric_result.model_copy(deep=True)
    service = LLMInterpretationService(provider=MockLLMProvider(), provider_name="mock")
    service.interpret(metric_result, AnalysisContext.GENERAL)
    assert metric_result == before


def test_interpret_signature_never_accepts_an_image() -> None:
    sig = inspect.signature(LLMInterpretationService.interpret)
    assert set(sig.parameters) - {"self"} == {"metric_result", "context"}


def test_provider_receives_only_prompt_strings(metric_result: DeterministicMetricResult) -> None:
    captured: dict[str, str] = {}

    class CapturingProvider:
        name = "capturing"

        def complete(self, system_prompt: str, user_prompt: str) -> dict:
            captured["system_prompt"] = system_prompt
            captured["user_prompt"] = user_prompt
            return MockLLMProvider().complete(system_prompt, user_prompt)

    service = LLMInterpretationService(provider=CapturingProvider(), provider_name="capturing")
    service.interpret(metric_result, AnalysisContext.GENERAL)

    assert isinstance(captured["system_prompt"], str)
    assert isinstance(captured["user_prompt"], str)
    assert "averageContrastRatio" in captured["user_prompt"]
    for forbidden in ["DecodedImage", "cv2_image", "pil_image", "raw_bytes"]:
        assert forbidden not in captured["user_prompt"]


# ---------- Service: failure handling (must always degrade, never raise) ----------


def test_no_provider_configured_is_unavailable(metric_result: DeterministicMetricResult) -> None:
    service = LLMInterpretationService(provider=None, provider_name="gemini")
    result = service.interpret(metric_result, AnalysisContext.GENERAL)
    assert result.status == LLMStatus.UNAVAILABLE
    assert result.provider is None
    assert result.observations == []


def test_provider_unavailable_error_degrades_gracefully(metric_result: DeterministicMetricResult) -> None:
    class UnavailableProvider:
        name = "broken"

        def complete(self, system_prompt: str, user_prompt: str) -> dict:
            raise LLMProviderUnavailableError("no key configured")

    service = LLMInterpretationService(provider=UnavailableProvider(), provider_name="broken")
    result = service.interpret(metric_result, AnalysisContext.GENERAL)
    assert result.status == LLMStatus.UNAVAILABLE
    assert result.provider is None


def test_malformed_response_degrades_to_failed(metric_result: DeterministicMetricResult) -> None:
    class MalformedProvider:
        name = "broken"

        def complete(self, system_prompt: str, user_prompt: str) -> dict:
            return {"not": "matching schema at all"}

    service = LLMInterpretationService(provider=MalformedProvider(), provider_name="broken")
    result = service.interpret(metric_result, AnalysisContext.GENERAL)
    assert result.status == LLMStatus.FAILED
    assert result.provider is None


def test_missing_metric_evidence_degrades_to_failed(metric_result: DeterministicMetricResult) -> None:
    class NoEvidenceProvider:
        name = "broken"

        def complete(self, system_prompt: str, user_prompt: str) -> dict:
            return {
                "summary": "x",
                "observations": [{"id": "o1", "text": "t", "metric_evidence": [], "category": "observation"}],
                "recommendations": [],
                "limitations": [],
            }

    service = LLMInterpretationService(provider=NoEvidenceProvider(), provider_name="broken")
    result = service.interpret(metric_result, AnalysisContext.GENERAL)
    assert result.status == LLMStatus.FAILED


def test_unexpected_provider_exception_degrades_to_failed_not_raised(
    metric_result: DeterministicMetricResult,
) -> None:
    class CrashingProvider:
        name = "broken"

        def complete(self, system_prompt: str, user_prompt: str) -> dict:
            raise RuntimeError("totally unexpected bug")

    service = LLMInterpretationService(provider=CrashingProvider(), provider_name="broken")
    result = service.interpret(metric_result, AnalysisContext.GENERAL)  # must not raise
    assert result.status == LLMStatus.FAILED


def test_llm_interpretation_error_maps_to_llm_unavailable_code() -> None:
    exc = LLMInterpretationError("bad response")
    assert exc.code == "LLM_UNAVAILABLE"
    assert exc.status_code == 502


def test_llm_provider_unavailable_error_maps_to_llm_unavailable_code() -> None:
    exc = LLMProviderUnavailableError("no key")
    assert exc.code == "LLM_UNAVAILABLE"
    assert exc.status_code == 502


# ---------- Gemini provider (network mocked — no real API call) ----------


class _FakeResponse:
    """Stands in for `google.genai.types.GenerateContentResponse`.

    `parsed` defaults to `None` (not simply omitted) to match the real SDK,
    which always defines the field but leaves it `None` when it could not
    build a structured result — `getattr(response, "parsed", None)` in the
    provider must treat "attribute present but None" the same as "absent".
    """

    def __init__(self, text: str | None = None, parsed: object | None = None) -> None:
        self.text = text
        self.parsed = parsed


@pytest.fixture
def gemini_provider() -> GeminiLLMProvider:
    return GeminiLLMProvider(api_key="test-key", model="gemini-2.5-flash", max_output_tokens=1024)


# ---- Structured-output config must set BOTH fields together ----


def test_gemini_config_sets_json_mime_type_and_structured_schema_together(
    gemini_provider: GeminiLLMProvider,
) -> None:
    config = gemini_provider._build_config("system prompt")
    assert config.response_mime_type == "application/json"
    assert config.response_schema is LLMStructuredOutput


def test_gemini_config_disables_thinking(gemini_provider: GeminiLLMProvider) -> None:
    """Thinking tokens were observed consuming ~980/1024 of the output
    budget on realistic prompts, truncating the JSON answer before it could
    be parsed (finish_reason=MAX_TOKENS). Disabling thinking removes that
    failure mode at the source."""
    config = gemini_provider._build_config("system prompt")
    assert config.thinking_config.thinking_budget == 0


def test_gemini_provider_sends_the_built_config_to_generate_content(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider
) -> None:
    captured: dict[str, Any] = {}

    def capturing_generate_content(**kwargs):
        captured.update(kwargs)
        return _FakeResponse(text=json.dumps(MockLLMProvider().complete("s", "u")))

    monkeypatch.setattr(gemini_provider._client.models, "generate_content", capturing_generate_content)
    gemini_provider.complete("system", "user")

    sent_config = captured["config"]
    assert sent_config.response_mime_type == "application/json"
    assert sent_config.response_schema is LLMStructuredOutput
    assert sent_config.system_instruction == "system"
    assert captured["contents"] == "user"


# ---- Debug logging: finish_reason / usage_metadata visible, content never logged ----


class _FakeCandidate:
    def __init__(self, finish_reason: str) -> None:
        self.finish_reason = finish_reason


def test_gemini_provider_logs_finish_reason_and_usage_metadata(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider, caplog: pytest.LogCaptureFixture
) -> None:
    class _ResponseWithMetadata(_FakeResponse):
        def __init__(self) -> None:
            super().__init__(text=json.dumps(MockLLMProvider().complete("s", "u")))
            self.candidates = [_FakeCandidate(finish_reason="MAX_TOKENS")]
            self.usage_metadata = "thoughts_token_count=979 total_token_count=1024"

    monkeypatch.setattr(gemini_provider._client.models, "generate_content", lambda **kwargs: _ResponseWithMetadata())

    with caplog.at_level("DEBUG", logger="lucidui.llm.gemini"):
        gemini_provider.complete("system", "user")

    joined = "\n".join(record.message for record in caplog.records)
    assert "MAX_TOKENS" in joined
    assert "thoughts_token_count" in joined
    assert "test-key" not in joined  # the API key must never be logged


def test_gemini_provider_never_logs_raw_response_content(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider, caplog: pytest.LogCaptureFixture
) -> None:
    secret_marker = "UNIQUE_SENTINEL_TEXT_MUST_NOT_APPEAR_IN_LOGS"
    payload = MockLLMProvider().complete("s", "u")
    payload["summary"] = secret_marker
    monkeypatch.setattr(
        gemini_provider._client.models, "generate_content", lambda **kwargs: _FakeResponse(text=json.dumps(payload))
    )

    with caplog.at_level("DEBUG", logger="lucidui.llm.gemini"):
        gemini_provider.complete("system", "user")

    joined = "\n".join(record.message for record in caplog.records)
    assert secret_marker not in joined


def test_gemini_provider_wraps_network_errors(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider
) -> None:
    def boom(**kwargs):
        raise ConnectionError("network down")

    monkeypatch.setattr(gemini_provider._client.models, "generate_content", boom)
    with pytest.raises(LLMProviderUnavailableError):
        gemini_provider.complete("system", "user")


# ---- response.parsed present (preferred path) ----


def test_gemini_provider_uses_response_parsed_when_it_is_a_structured_output_instance(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider
) -> None:
    valid_payload = MockLLMProvider().complete("s", "u")
    parsed_instance = LLMStructuredOutput.model_validate(valid_payload)
    monkeypatch.setattr(
        gemini_provider._client.models,
        "generate_content",
        # response.text deliberately malformed to prove .parsed is what's used, not .text
        lambda **kwargs: _FakeResponse(text="not valid json at all", parsed=parsed_instance),
    )
    result = gemini_provider.complete("system", "user")
    assert result == parsed_instance.model_dump(by_alias=True)


def test_gemini_provider_uses_response_parsed_when_it_is_a_dict(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider
) -> None:
    valid_payload = MockLLMProvider().complete("s", "u")
    monkeypatch.setattr(
        gemini_provider._client.models,
        "generate_content",
        lambda **kwargs: _FakeResponse(text="not valid json at all", parsed=valid_payload),
    )
    result = gemini_provider.complete("system", "user")
    assert result == LLMStructuredOutput.model_validate(valid_payload).model_dump(by_alias=True)


def test_gemini_provider_raises_when_parsed_dict_fails_schema_validation(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider
) -> None:
    invalid_parsed = {"not": "matching the LLMStructuredOutput schema at all"}
    monkeypatch.setattr(
        gemini_provider._client.models,
        "generate_content",
        lambda **kwargs: _FakeResponse(text=None, parsed=invalid_parsed),
    )
    with pytest.raises(LLMInterpretationError):
        gemini_provider.complete("system", "user")


# ---- response.parsed absent — falls back to response.text ----


def test_gemini_provider_falls_back_to_text_when_parsed_is_absent(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider
) -> None:
    valid_payload = MockLLMProvider().complete("s", "u")
    monkeypatch.setattr(
        gemini_provider._client.models,
        "generate_content",
        lambda **kwargs: _FakeResponse(text=json.dumps(valid_payload), parsed=None),
    )
    result = gemini_provider.complete("system", "user")
    assert result == valid_payload


def test_gemini_provider_raises_on_empty_response(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider
) -> None:
    monkeypatch.setattr(gemini_provider._client.models, "generate_content", lambda **kwargs: _FakeResponse(text=None))
    with pytest.raises(LLMInterpretationError):
        gemini_provider.complete("system", "user")


def test_gemini_provider_raises_on_invalid_json_text_fallback(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider
) -> None:
    monkeypatch.setattr(
        gemini_provider._client.models, "generate_content", lambda **kwargs: _FakeResponse(text="not valid json")
    )
    with pytest.raises(LLMInterpretationError):
        gemini_provider.complete("system", "user")


def test_gemini_provider_raises_when_text_fallback_json_fails_schema_validation(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider
) -> None:
    monkeypatch.setattr(
        gemini_provider._client.models,
        "generate_content",
        lambda **kwargs: _FakeResponse(text=json.dumps({"not": "matching the schema"})),
    )
    with pytest.raises(LLMInterpretationError):
        gemini_provider.complete("system", "user")


def test_gemini_provider_end_to_end_through_service_on_failure(
    monkeypatch: pytest.MonkeyPatch, gemini_provider: GeminiLLMProvider, metric_result: DeterministicMetricResult
) -> None:
    """A Gemini-level failure must still degrade gracefully through the service."""

    def boom(**kwargs):
        raise ConnectionError("network down")

    monkeypatch.setattr(gemini_provider._client.models, "generate_content", boom)
    service = LLMInterpretationService(provider=gemini_provider, provider_name="gemini")
    result = service.interpret(metric_result, AnalysisContext.GENERAL)
    assert result.status == LLMStatus.UNAVAILABLE


# ---------- Provider selection from configuration ----------


def test_get_llm_provider_defaults_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings
    from app.dependencies import get_llm_provider

    get_settings.cache_clear()
    get_llm_provider.cache_clear()
    # Explicit overrides, not delenv: pydantic-settings falls through to a
    # real backend/.env file when an env var is merely removed from
    # os.environ, since env_file ranks below (not above) process env vars.
    # A developer's local .env may legitimately hold real gemini settings.
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("GEMINI_API_KEY", "")

    provider = get_llm_provider()
    assert isinstance(provider, MockLLMProvider)

    get_settings.cache_clear()
    get_llm_provider.cache_clear()


def test_get_llm_provider_is_none_when_gemini_selected_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings
    from app.dependencies import get_llm_provider

    get_settings.cache_clear()
    get_llm_provider.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "")  # explicit override — see note above

    provider = get_llm_provider()
    assert provider is None

    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    get_settings.cache_clear()
    get_llm_provider.cache_clear()


def test_get_llm_provider_returns_gemini_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings
    from app.dependencies import get_llm_provider

    get_settings.cache_clear()
    get_llm_provider.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    provider = get_llm_provider()
    assert isinstance(provider, GeminiLLMProvider)

    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_settings.cache_clear()
    get_llm_provider.cache_clear()
