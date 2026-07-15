"""Tests for the UIClip evaluation layer (app.uiclip).

Every test here uses `MockUIClipProvider` or a small fake/monkeypatched
provider — none downloads or runs a real model, per CLAUDE.md ("Tests must
not require ... UIClip ... GPU").
"""

import inspect

import numpy as np
import pytest
from PIL import Image
from PIL.Image import Image as PILImage

from app.images.models import DecodedImage, ImageMetadata
from app.schemas.common import DescriptionSource, UIClipStatus
from app.uiclip.exceptions import UIClipEvaluationError, UIClipProviderUnavailableError
from app.uiclip.mock_provider import MockUIClipProvider
from app.uiclip.models import UIClipProviderOutput
from app.uiclip.provider import UIClipProvider
from app.uiclip.service import UIClipEvaluationService


@pytest.fixture
def decoded_screenshot() -> DecodedImage:
    pil_image = Image.new("RGB", (120, 90), color=(60, 90, 140))
    metadata = ImageMetadata(
        width=120, height=90, format="png", aspect_ratio=120 / 90, orientation="landscape", file_size_bytes=0
    )
    return DecodedImage(
        raw_bytes=b"",
        cv2_image=np.zeros((90, 120, 3), dtype=np.uint8),
        pil_image=pil_image,
        metadata=metadata,
    )


@pytest.fixture
def service() -> UIClipEvaluationService:
    return UIClipEvaluationService(provider=MockUIClipProvider(), provider_name="mock")


# ---------- Mock provider ----------


def test_mock_provider_returns_valid_structured_output() -> None:
    result = MockUIClipProvider().evaluate(Image.new("RGB", (10, 10)), "a description")
    UIClipProviderOutput.model_validate(result)  # must not raise


def test_mock_provider_is_deterministic() -> None:
    provider = MockUIClipProvider()
    img = Image.new("RGB", (10, 10))
    assert provider.evaluate(img, "a") == provider.evaluate(img, "b")


def test_mock_provider_self_identifies_as_mock() -> None:
    result = MockUIClipProvider().evaluate(Image.new("RGB", (10, 10)), "x")
    assert "mock" in result["model_version"].lower()


# ---------- Successful evaluation ----------


def test_successful_evaluation(service: UIClipEvaluationService, decoded_screenshot: DecodedImage) -> None:
    result = service.evaluate(decoded_screenshot, "A settings screen")
    assert result.enabled is True
    assert result.status == UIClipStatus.COMPLETED
    assert result.model_version == "mock-uiclip-v1"
    assert result.description == "A settings screen"
    assert result.description_source == DescriptionSource.USER
    assert isinstance(result.quality_score, float)
    assert result.normalized_quality_score is None
    assert len(result.observations) > 0
    assert result.inference_time_ms >= 0


def test_provider_receives_image_and_description(decoded_screenshot: DecodedImage) -> None:
    captured: dict = {}

    class CapturingProvider:
        name = "capturing"

        def evaluate(self, image, description):
            captured["image"] = image
            captured["description"] = description
            return MockUIClipProvider().evaluate(image, description)

    svc = UIClipEvaluationService(provider=CapturingProvider(), provider_name="capturing")
    svc.evaluate(decoded_screenshot, "A checkout page")

    assert isinstance(captured["image"], PILImage)
    assert captured["image"] is decoded_screenshot.pil_image
    assert captured["description"] == "A checkout page"


def test_provider_does_not_receive_metric_json_or_llm_output(decoded_screenshot: DecodedImage) -> None:
    """Structural proof of independence: the provider protocol's `evaluate`
    signature has no parameter through which DeterministicMetricResult,
    Gemini output, or comparison results could reach it."""
    sig = inspect.signature(UIClipProvider.evaluate)
    assert set(sig.parameters) - {"self"} == {"image", "description"}


def test_evaluate_signature_only_accepts_image_and_description() -> None:
    sig = inspect.signature(UIClipEvaluationService.evaluate)
    assert set(sig.parameters) - {"self"} == {"image", "description"}


# ---------- Description resolution ----------


def test_missing_description_uses_documented_generic_fallback(
    service: UIClipEvaluationService, decoded_screenshot: DecodedImage
) -> None:
    result = service.evaluate(decoded_screenshot, None)
    assert result.description_source == DescriptionSource.GENERIC
    assert result.description == "A software user interface screenshot."
    assert result.status == UIClipStatus.COMPLETED  # still evaluates — description absence is not a failure


def test_blank_description_is_treated_as_missing(
    service: UIClipEvaluationService, decoded_screenshot: DecodedImage
) -> None:
    result = service.evaluate(decoded_screenshot, "   ")
    assert result.description_source == DescriptionSource.GENERIC
    assert result.description == "A software user interface screenshot."


def test_description_is_trimmed(service: UIClipEvaluationService, decoded_screenshot: DecodedImage) -> None:
    result = service.evaluate(decoded_screenshot, "  A dashboard  ")
    assert result.description == "A dashboard"
    assert result.description_source == DescriptionSource.USER


# ---------- Generic fallback provider calls ----------


class _CapturingProvider:
    name = "capturing"

    def __init__(self) -> None:
        self.call_count = 0
        self.descriptions: list[str] = []

    def evaluate(self, image, description):
        self.call_count += 1
        self.descriptions.append(description)
        return MockUIClipProvider().evaluate(image, description)


def test_provider_runs_with_generic_fallback_when_description_missing(
    decoded_screenshot: DecodedImage,
) -> None:
    provider = _CapturingProvider()
    svc = UIClipEvaluationService(provider=provider, provider_name="capturing")

    result = svc.evaluate(decoded_screenshot, None)

    assert provider.call_count == 1
    assert provider.descriptions == ["A software user interface screenshot."]
    assert result.status == UIClipStatus.COMPLETED
    assert result.description_source == DescriptionSource.GENERIC


def test_provider_runs_with_generic_fallback_when_description_blank(
    decoded_screenshot: DecodedImage,
) -> None:
    provider = _CapturingProvider()
    svc = UIClipEvaluationService(provider=provider, provider_name="capturing")

    result = svc.evaluate(decoded_screenshot, "   ")

    assert provider.call_count == 1
    assert provider.descriptions == ["A software user interface screenshot."]
    assert result.status == UIClipStatus.COMPLETED
    assert result.description_source == DescriptionSource.GENERIC


def test_provider_runs_with_real_description_when_submitted(
    decoded_screenshot: DecodedImage,
) -> None:
    provider = _CapturingProvider()
    svc = UIClipEvaluationService(provider=provider, provider_name="capturing")

    result = svc.evaluate(decoded_screenshot, "A real checkout page description")

    assert provider.call_count == 1
    assert provider.descriptions == ["A real checkout page description"]
    assert result.status == UIClipStatus.COMPLETED
    assert result.description == "A real checkout page description"


def test_mock_provider_runs_with_generic_fallback(
    decoded_screenshot: DecodedImage,
) -> None:
    svc = UIClipEvaluationService(provider=MockUIClipProvider(), provider_name="mock")
    result = svc.evaluate(decoded_screenshot, None)
    assert result.status == UIClipStatus.COMPLETED


# ---------- Failure handling (must always degrade, never raise) ----------


def test_no_provider_configured_is_unavailable(decoded_screenshot: DecodedImage) -> None:
    svc = UIClipEvaluationService(provider=None, provider_name="mock")
    result = svc.evaluate(decoded_screenshot, "x")
    assert result.status == UIClipStatus.UNAVAILABLE
    assert result.enabled is True  # the user requested it; it just couldn't run
    assert result.model_version is None
    assert result.observations == []


def test_provider_unavailable_error_degrades_gracefully(decoded_screenshot: DecodedImage) -> None:
    class UnavailableProvider:
        name = "broken"

        def evaluate(self, image, description):
            raise UIClipProviderUnavailableError("model not loaded")

    svc = UIClipEvaluationService(provider=UnavailableProvider(), provider_name="broken")
    result = svc.evaluate(decoded_screenshot, "x")
    assert result.status == UIClipStatus.UNAVAILABLE


def test_malformed_output_degrades_to_failed(decoded_screenshot: DecodedImage) -> None:
    class MalformedProvider:
        name = "broken"

        def evaluate(self, image, description):
            return {"not": "matching the expected schema"}

    svc = UIClipEvaluationService(provider=MalformedProvider(), provider_name="broken")
    result = svc.evaluate(decoded_screenshot, "x")
    assert result.status == UIClipStatus.FAILED
    assert result.model_version is None


def test_unexpected_provider_exception_degrades_to_failed_not_raised(decoded_screenshot: DecodedImage) -> None:
    class CrashingProvider:
        name = "broken"

        def evaluate(self, image, description):
            raise RuntimeError("totally unexpected bug")

    svc = UIClipEvaluationService(provider=CrashingProvider(), provider_name="broken")
    result = svc.evaluate(decoded_screenshot, "x")  # must not raise
    assert result.status == UIClipStatus.FAILED


def test_deterministic_evaluation_error_raised_by_provider_degrades_to_failed(decoded_screenshot: DecodedImage) -> None:
    class ExplicitlyFailingProvider:
        name = "broken"

        def evaluate(self, image, description):
            raise UIClipEvaluationError("provider ran but produced unusable output")

    svc = UIClipEvaluationService(provider=ExplicitlyFailingProvider(), provider_name="broken")
    result = svc.evaluate(decoded_screenshot, "x")
    assert result.status == UIClipStatus.FAILED


def test_uiclip_provider_unavailable_error_maps_to_uiclip_unavailable_code() -> None:
    exc = UIClipProviderUnavailableError("no model")
    assert exc.code == "UICLIP_UNAVAILABLE"
    assert exc.status_code == 502


def test_uiclip_evaluation_error_maps_to_uiclip_unavailable_code() -> None:
    exc = UIClipEvaluationError("bad output")
    assert exc.code == "UICLIP_UNAVAILABLE"
    assert exc.status_code == 502


# ---------- Independence (module-level, not just per-call) ----------


def test_uiclip_module_does_not_import_llm_service() -> None:
    """Parses each module's actual `import`/`from ... import` statements
    (via ast, not a raw text search — a docstring mentioning "app.llm" in
    prose is fine, an executable import of it is not) and asserts none
    reference app.llm or app.metrics."""
    import ast

    import app.uiclip.exceptions
    import app.uiclip.mock_provider
    import app.uiclip.models
    import app.uiclip.provider
    import app.uiclip.service

    for module in (
        app.uiclip.exceptions,
        app.uiclip.mock_provider,
        app.uiclip.models,
        app.uiclip.provider,
        app.uiclip.service,
    ):
        source_file = inspect.getsourcefile(module)
        assert source_file is not None
        with open(source_file) as f:
            tree = ast.parse(f.read(), filename=source_file)

        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        for imported in imported_modules:
            assert not imported.startswith("app.llm"), f"{module.__name__} imports {imported}"
            assert not imported.startswith("app.metrics"), f"{module.__name__} imports {imported}"


def test_uiclip_provider_never_receives_deterministic_metric_result(decoded_screenshot: DecodedImage) -> None:
    """Belt-and-suspenders runtime check alongside the signature test above:
    even if someone tried to smuggle a DeterministicMetricResult through,
    UIClipEvaluationService.evaluate() has no parameter for it."""
    sig = inspect.signature(UIClipEvaluationService.evaluate)
    assert "metric_result" not in sig.parameters
    assert "deterministic_metric_result" not in sig.parameters


# ---------- Provider selection from configuration ----------


def test_get_uiclip_provider_defaults_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings
    from app.dependencies import get_uiclip_provider

    get_settings.cache_clear()
    get_uiclip_provider.cache_clear()
    monkeypatch.setenv("UICLIP_PROVIDER", "mock")

    provider = get_uiclip_provider()
    assert isinstance(provider, MockUIClipProvider)

    monkeypatch.delenv("UICLIP_PROVIDER", raising=False)
    get_settings.cache_clear()
    get_uiclip_provider.cache_clear()


def test_get_uiclip_provider_is_none_for_unconfigured_real_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """No official provider is implemented yet (Phase 5) — selecting
    anything other than "mock" must gracefully degrade to unavailable,
    never raise."""
    from app.config import get_settings
    from app.dependencies import get_uiclip_provider

    get_settings.cache_clear()
    get_uiclip_provider.cache_clear()
    monkeypatch.setenv("UICLIP_PROVIDER", "official")

    provider = get_uiclip_provider()
    assert provider is None

    monkeypatch.delenv("UICLIP_PROVIDER", raising=False)
    get_settings.cache_clear()
    get_uiclip_provider.cache_clear()
