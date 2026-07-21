"""Unit tests for the pure `build_variant_deltas` function, isolated from the
HTTP layer. Builds two real `AnalysisReport`s via `AnalysisService` (mock
LLM/UIClip providers, no network/GPU/OCR-binary dependency, per CLAUDE.md
Testing Rules) and asserts on `build_variant_deltas`'s output directly.
"""

import pytest

from app.llm.mock_provider import MockLLMProvider
from app.llm.service import LLMInterpretationService
from app.presentation.variant_delta_builder import build_variant_deltas
from app.repositories.in_memory import InMemoryAnalysisRepository
from app.schemas.common import DeltaDirection
from app.services.analysis_service import AnalysisService
from app.uiclip.mock_provider import MockUIClipProvider
from app.uiclip.service import UIClipEvaluationService


@pytest.fixture
def analysis_service(image_validator, image_decoder, metric_engine) -> AnalysisService:
    return AnalysisService(
        repository=InMemoryAnalysisRepository(),
        image_validator=image_validator,
        image_decoder=image_decoder,
        metric_engine=metric_engine,
        llm_service=LLMInterpretationService(provider=MockLLMProvider(), provider_name="mock"),
        uiclip_service=UIClipEvaluationService(provider=MockUIClipProvider(), provider_name="mock"),
    )


@pytest.fixture
def image_validator():
    from app.images.validator import ImageValidator

    return ImageValidator(max_size_bytes=20 * 1024 * 1024)


@pytest.fixture
def image_decoder():
    from app.images.decoder import ImageDecoder
    from app.images.metadata import ImageMetadataExtractor

    return ImageDecoder(metadata_extractor=ImageMetadataExtractor())


@pytest.fixture
def metric_engine():
    from app.metrics.engine import MetricEngine

    return MetricEngine()


def test_identical_images_produce_equal_direction_and_zero_composite_delta(
    analysis_service: AnalysisService, valid_png_bytes: bytes, mock_ocr: None
) -> None:
    variant_a = analysis_service.create_single_analysis(
        data=valid_png_bytes, content_type="image/png", context="general"
    )
    variant_b = analysis_service.create_single_analysis(
        data=valid_png_bytes, content_type="image/png", context="general"
    )

    deltas = build_variant_deltas(variant_a, variant_b)

    assert deltas.composite_score_delta == 0.0
    assert deltas.composite_score_delta_display == "0.00"
    for metric_delta in deltas.metric_deltas:
        if metric_delta.normalized_score_delta is not None:
            assert metric_delta.normalized_score_delta == 0.0
            assert metric_delta.direction == DeltaDirection.EQUAL


def test_metric_deltas_cover_every_presentation_section(
    analysis_service: AnalysisService, valid_png_bytes: bytes, valid_jpeg_bytes: bytes, mock_ocr: None
) -> None:
    variant_a = analysis_service.create_single_analysis(
        data=valid_png_bytes, content_type="image/png", context="general"
    )
    variant_b = analysis_service.create_single_analysis(
        data=valid_jpeg_bytes, content_type="image/jpeg", context="general"
    )

    deltas = build_variant_deltas(variant_a, variant_b)

    assert [d.id for d in deltas.metric_deltas] == [s.id for s in variant_a.presentation.metric_sections]
    assert all(d.raw_display_a and d.raw_display_b for d in deltas.metric_deltas)


def test_uiclip_delta_not_available_when_disabled(
    analysis_service: AnalysisService, valid_png_bytes: bytes, valid_jpeg_bytes: bytes, mock_ocr: None
) -> None:
    variant_a = analysis_service.create_single_analysis(
        data=valid_png_bytes, content_type="image/png", context="general", run_uiclip=False
    )
    variant_b = analysis_service.create_single_analysis(
        data=valid_jpeg_bytes, content_type="image/jpeg", context="general", run_uiclip=False
    )

    deltas = build_variant_deltas(variant_a, variant_b)

    assert deltas.uiclip_raw_score_delta is None
    assert deltas.uiclip_raw_score_delta_display == "No data available"
