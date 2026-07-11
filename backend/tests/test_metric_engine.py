import numpy as np
import pytest
import pytesseract
from PIL import Image

import reference.legacy_metric_engine as legacy
from app.images.models import DecodedImage, ImageMetadata
from app.metrics.engine import MetricEngine
from app.metrics.exceptions import MetricAnalysisError, OCRExecutionError
from app.schemas.common import AnalysisContext


@pytest.fixture(autouse=True)
def _mock_ocr(monkeypatch: pytest.MonkeyPatch, mock_ocr_data: dict) -> None:
    """Every test in this module gets deterministic OCR unless it overrides it."""
    monkeypatch.setattr(pytesseract, "image_to_data", lambda *args, **kwargs: mock_ocr_data)


@pytest.fixture
def engine() -> MetricEngine:
    return MetricEngine()


# ---------- Core contract ----------


def test_accepts_a_decoded_image_and_returns_a_result(engine: MetricEngine, decoded_image: DecodedImage) -> None:
    result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    assert result is not None


def test_does_not_require_a_file_path(engine: MetricEngine, decoded_image: DecodedImage) -> None:
    # DecodedImage carries no filesystem path at all; a successful call
    # proves the engine never needed one.
    result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    assert result.weighted_score is not None


def test_ocr_runs_exactly_once(
    monkeypatch: pytest.MonkeyPatch, engine: MetricEngine, decoded_image: DecodedImage, mock_ocr_data: dict
) -> None:
    calls = {"count": 0}

    def counting_ocr(*args, **kwargs):
        calls["count"] += 1
        return mock_ocr_data

    monkeypatch.setattr(pytesseract, "image_to_data", counting_ocr)
    engine.analyze(decoded_image, AnalysisContext.GENERAL)
    assert calls["count"] == 1


def test_returns_raw_metrics(engine: MetricEngine, decoded_image: DecodedImage) -> None:
    result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    assert set(result.raw.keys()) == {
        "contrast",
        "clutter",
        "elements",
        "groups",
        "textDensity",
        "whitespaceAlignment",
    }


def test_returns_normalized_metrics(engine: MetricEngine, decoded_image: DecodedImage) -> None:
    result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    assert set(result.normalized.keys()) == {"contrast", "clutter", "textDensity", "elementSize", "groupCount"}


def test_returns_additional_signals(engine: MetricEngine, decoded_image: DecodedImage) -> None:
    result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    assert set(result.additional_signals.keys()) == {
        "colorfulness",
        "fittsFullIndexOfDifficulty",
        "visualBalance",
    }


def test_returns_weighted_score(engine: MetricEngine, decoded_image: DecodedImage) -> None:
    result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    assert isinstance(result.weighted_score, float)


def test_preserves_camel_case_legacy_field_names(engine: MetricEngine, decoded_image: DecodedImage) -> None:
    result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    assert "averageContrastRatio" in result.raw["contrast"]
    assert "regionsAnalyzed" in result.raw["contrast"]
    assert "regionsBelowAAThreshold" in result.raw["contrast"]
    assert "edgeDensity" in result.raw["clutter"]
    assert "detectedElementCount" in result.raw["elements"]
    assert "hicksLawEstimateMs" in result.raw["elements"]
    assert "smallTargetsBelow44px" in result.raw["elements"]
    assert "estimatedGroupCount" in result.raw["groups"]
    assert "textDensityRatio" in result.raw["textDensity"]
    assert "fontSizeDiversityProxy" in result.raw["textDensity"]
    assert "whitespaceRatio" in result.raw["whitespaceAlignment"]
    assert "alignmentVariance" in result.raw["whitespaceAlignment"]
    assert "colorfulnessScore" in result.additional_signals["colorfulness"]
    assert "averageIndexOfDifficulty" in result.additional_signals["fittsFullIndexOfDifficulty"]
    assert "asymmetryScore" in result.additional_signals["visualBalance"]


def test_supports_general_context(engine: MetricEngine, decoded_image: DecodedImage) -> None:
    result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    assert isinstance(result.weighted_score, float)


def test_supports_expert_context(engine: MetricEngine, decoded_image: DecodedImage) -> None:
    result = engine.analyze(decoded_image, AnalysisContext.EXPERT)
    assert isinstance(result.weighted_score, float)


def test_general_and_expert_produce_different_weighted_scores(
    engine: MetricEngine, decoded_image: DecodedImage
) -> None:
    general_result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    expert_result = engine.analyze(decoded_image, AnalysisContext.EXPERT)
    assert general_result.weighted_score != expert_result.weighted_score


def test_metric_engine_version(engine: MetricEngine, decoded_image: DecodedImage) -> None:
    result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    assert result.metric_engine_version == "legacy-v1"


def test_score_name(engine: MetricEngine, decoded_image: DecodedImage) -> None:
    result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    assert result.score_name == "LucidUI Composite Signal Score"


# ---------- Legacy equivalence (most important test in this phase) ----------


def test_engine_output_matches_legacy_reference_exactly(
    engine: MetricEngine, decoded_image: DecodedImage, deterministic_cv_image: np.ndarray, mock_ocr_data: dict
) -> None:
    elements_meta, elements = legacy.analyze_elements(deterministic_cv_image, mock_ocr_data)
    expected_raw = {
        "contrast": legacy.analyze_contrast(deterministic_cv_image, mock_ocr_data),
        "clutter": legacy.analyze_clutter(deterministic_cv_image),
        "elements": elements_meta,
        "groups": legacy.analyze_groups(elements, deterministic_cv_image.shape),
        "textDensity": legacy.analyze_text_density(deterministic_cv_image, mock_ocr_data),
        "whitespaceAlignment": legacy.analyze_whitespace_alignment(deterministic_cv_image, elements),
    }
    expected_additional = {
        "colorfulness": legacy.analyze_colorfulness(deterministic_cv_image),
        "fittsFullIndexOfDifficulty": legacy.analyze_fitts_full(elements),
        "visualBalance": legacy.analyze_visual_balance(deterministic_cv_image),
    }
    expected_normalized = legacy.normalize_metrics(expected_raw)
    expected_score_general = legacy.weighted_score(expected_normalized, "general")
    expected_score_expert = legacy.weighted_score(expected_normalized, "expert")

    general_result = engine.analyze(decoded_image, AnalysisContext.GENERAL)
    expert_result = engine.analyze(decoded_image, AnalysisContext.EXPERT)

    assert general_result.raw == expected_raw
    assert general_result.normalized == expected_normalized
    assert general_result.additional_signals == expected_additional
    assert general_result.weighted_score == expected_score_general

    assert expert_result.raw == expected_raw
    assert expert_result.normalized == expected_normalized
    assert expert_result.additional_signals == expected_additional
    assert expert_result.weighted_score == expected_score_expert


# ---------- Failure handling ----------


def test_ocr_exception_becomes_ocr_execution_error(
    monkeypatch: pytest.MonkeyPatch, engine: MetricEngine, decoded_image: DecodedImage
) -> None:
    def failing_ocr(*args, **kwargs):
        raise RuntimeError("tesseract is not installed")

    monkeypatch.setattr(pytesseract, "image_to_data", failing_ocr)
    with pytest.raises(OCRExecutionError):
        engine.analyze(decoded_image, AnalysisContext.GENERAL)


def test_missing_image_data_produces_metric_domain_error(engine: MetricEngine) -> None:
    blank_pil = Image.new("RGB", (1, 1))
    metadata = ImageMetadata(
        width=0, height=0, format="png", aspect_ratio=0.0, orientation="square", file_size_bytes=0
    )
    empty_image = DecodedImage(raw_bytes=b"", cv2_image=np.array([]), pil_image=blank_pil, metadata=metadata)
    with pytest.raises(MetricAnalysisError):
        engine.analyze(empty_image, AnalysisContext.GENERAL)


def test_invalid_image_data_produces_metric_domain_error(engine: MetricEngine) -> None:
    blank_pil = Image.new("RGB", (1, 1))
    metadata = ImageMetadata(
        width=1, height=1, format="png", aspect_ratio=1.0, orientation="square", file_size_bytes=0
    )
    # A 1-D array is not a usable image (no height/width dimensions).
    invalid_image = DecodedImage(
        raw_bytes=b"", cv2_image=np.array([1, 2, 3]), pil_image=blank_pil, metadata=metadata
    )
    with pytest.raises(MetricAnalysisError):
        engine.analyze(invalid_image, AnalysisContext.GENERAL)


def test_unexpected_metric_function_error_is_not_silently_swallowed(
    monkeypatch: pytest.MonkeyPatch, engine: MetricEngine, decoded_image: DecodedImage
) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("unexpected bug in a metric function")

    monkeypatch.setattr("app.metrics.engine.analyze_clutter", boom)
    with pytest.raises(MetricAnalysisError):
        engine.analyze(decoded_image, AnalysisContext.GENERAL)
