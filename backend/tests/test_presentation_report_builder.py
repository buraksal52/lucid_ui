"""Unit tests for the pure Presentation Report builder (app.presentation).

No HTTP, no repository, no provider — every test constructs
`DeterministicMetricResult` / `LLMInterpretationResult` / `UIClipResult`
directly and calls `build_presentation`, per CLAUDE.md ("Tests must not
require ... external APIs ... GPU").
"""

import copy

from app.metrics.models import DeterministicMetricResult
from app.presentation.report_builder import build_presentation
from app.schemas.common import AnalysisContext, DescriptionSource, LLMStatus, UIClipStatus
from app.schemas.llm import LLMInterpretationResult, LLMObservation
from app.schemas.uiclip import UIClipResult

_RAW = {
    "contrast": {
        "averageContrastRatio": 1.27,
        "regionsAnalyzed": 5,
        "regionsBelowAAThreshold": 2,
        "source": "WCAG 2.1 AA (4.5:1 normal text)",
    },
    "clutter": {
        "edgeDensity": 0.0189,
        "source": "Rosenholtz, Li & Nakano (2007) - Edge Density proxy",
    },
    "elements": {
        "detectedElementCount": 185,
        "contourBasedCount": 100,
        "ocrBasedCount": 85,
        "hicksLawEstimateMs": 1130.9,
        "isProxyMetric": True,
        "smallTargetsBelow44px": 158,
        "source": "Hick's Law (T = b * log2(n+1), b=150ms); Fitts threshold 44x44px; element count = contour + OCR text blocks",
    },
    "groups": {
        "estimatedGroupCount": 7,
        "isProxyMetric": True,
        "source": "Miller's Law (7+-2), Miller (1956)",
    },
    "textDensity": {
        "textDensityRatio": 0.12,
        "fontSizeDiversityProxy": 3.4,
        "wordsDetected": 42,
    },
    "whitespaceAlignment": {
        "whitespaceRatio": 0.7475,
        "alignmentVariance": 0.0421,
        "source": "Whitespace/Alignment proxy (low-variance block ratio; element position variance)",
    },
}

_ADDITIONAL_SIGNALS = {
    "colorfulness": {
        "colorfulnessScore": 23.45,
        "source": "Hasler & Suesstrunk (2003) - Measuring Colourfulness in Natural Images",
    },
    "fittsFullIndexOfDifficulty": {
        "averageIndexOfDifficulty": 2.13,
        "elementsConsidered": 40,
        "isProxyMetric": True,
        "source": "Fitts's Law (ID = log2(2D/W)), Fitts (1954)",
    },
    "visualBalance": {
        "asymmetryScore": 0.032,
        "source": "Visual balance proxy (left/right, top/bottom luminance difference)",
    },
}

_NORMALIZED = {"contrast": 55.5, "clutter": 62.1, "textDensity": 40.0, "elementSize": 30.0, "groupCount": 100.0}


def _metric_result(**overrides) -> DeterministicMetricResult:
    defaults = dict(
        raw=_RAW,
        normalized=_NORMALIZED,
        additional_signals=_ADDITIONAL_SIGNALS,
        weighted_score=47.8,
    )
    defaults.update(overrides)
    return DeterministicMetricResult(**defaults)


def _llm_result(**overrides) -> LLMInterpretationResult:
    defaults = dict(
        status=LLMStatus.COMPLETED,
        provider="mock",
        summary="A short plain-language summary.",
        observations=[],
        recommendations=[],
        limitations=[],
    )
    defaults.update(overrides)
    return LLMInterpretationResult(**defaults)


def _uiclip_result(**overrides) -> UIClipResult:
    defaults = dict(
        enabled=True,
        status=UIClipStatus.COMPLETED,
        model_version="mock-uiclip-v1",
        description="A software user interface screenshot.",
        description_source=DescriptionSource.GENERIC,
        quality_score=21.7,
        normalized_quality_score=None,
        observations=[],
        inference_time_ms=5,
    )
    defaults.update(overrides)
    return UIClipResult(**defaults)


def _build(**overrides):
    metric_result = overrides.pop("metric_result", _metric_result())
    llm_result = overrides.pop("llm_result", _llm_result())
    uiclip_result = overrides.pop("uiclip_result", _uiclip_result())
    context = overrides.pop("context", AnalysisContext.GENERAL)
    closing_note = overrides.pop("closing_note", "closing note text")
    return build_presentation(
        context=context,
        metric_result=metric_result,
        llm_result=llm_result,
        uiclip_result=uiclip_result,
        closing_note=closing_note,
    )


# ---------- Fixed order ----------


def test_metric_sections_are_in_the_documented_fixed_order() -> None:
    presentation = _build()
    ids = [section.id for section in presentation.metric_sections]
    assert ids == [
        "contrast",
        "visual-complexity",
        "elements-target-size",
        "hicks-law",
        "grouping",
        "text-density",
        "whitespace-alignment",
        "colorfulness",
        "fitts-law",
        "visual-balance",
    ]


def test_metric_section_order_is_stable_across_calls() -> None:
    first = _build()
    second = _build()
    assert [s.id for s in first.metric_sections] == [s.id for s in second.metric_sections]


# ---------- rawDisplay formatting ----------


def test_raw_display_formats_match_documented_examples() -> None:
    sections = {s.id: s for s in _build().metric_sections}
    assert sections["contrast"].raw_display == "1.27:1"
    assert sections["visual-complexity"].raw_display == "0.0189"
    assert sections["elements-target-size"].raw_display == "158 / 185"
    assert sections["hicks-law"].raw_display == "1130.9 ms"
    assert sections["whitespace-alignment"].raw_display == "Whitespace 74.75% · Alignment variance 0.0421"
    assert _build().composite.raw_display == "47.8 / 100"


def test_raw_display_falls_back_to_no_data_when_value_missing() -> None:
    raw = copy.deepcopy(_RAW)
    raw["contrast"]["averageContrastRatio"] = None
    additional = copy.deepcopy(_ADDITIONAL_SIGNALS)
    additional["fittsFullIndexOfDifficulty"]["averageIndexOfDifficulty"] = None
    metric_result = _metric_result(raw=raw, additional_signals=additional)
    sections = {s.id: s for s in _build(metric_result=metric_result).metric_sections}
    assert sections["contrast"].raw_display == "No data available"
    assert sections["fitts-law"].raw_display == "No data available"


# ---------- normalizedScore only where the engine actually normalizes ----------


def test_normalized_score_present_only_for_actually_normalized_metrics() -> None:
    sections = {s.id: s for s in _build().metric_sections}
    assert sections["contrast"].normalized_score == 55.5
    assert sections["visual-complexity"].normalized_score == 62.1
    assert sections["elements-target-size"].normalized_score == 30.0
    assert sections["grouping"].normalized_score == 100.0
    assert sections["text-density"].normalized_score == 40.0
    # No normalized form exists for these in the legacy engine's
    # `normalize_metrics` output — must stay null, never invented.
    assert sections["hicks-law"].normalized_score is None
    assert sections["whitespace-alignment"].normalized_score is None
    assert sections["colorfulness"].normalized_score is None
    assert sections["fitts-law"].normalized_score is None
    assert sections["visual-balance"].normalized_score is None


# ---------- source / isProxy passthrough ----------


def test_source_and_is_proxy_reflect_the_underlying_raw_dict() -> None:
    sections = {s.id: s for s in _build().metric_sections}
    assert sections["contrast"].source == "WCAG 2.1 AA (4.5:1 normal text)"
    assert sections["contrast"].is_proxy is False
    assert sections["elements-target-size"].is_proxy is True
    assert sections["hicks-law"].is_proxy is True
    assert sections["grouping"].is_proxy is True
    assert sections["fitts-law"].is_proxy is True
    assert sections["visual-balance"].is_proxy is False
    # `analyze_text_density` never included a `source` key upstream.
    assert sections["text-density"].source is None


# ---------- observation -> metric section matching ----------


def test_observation_evidence_links_to_the_matching_metric_section() -> None:
    obs = LLMObservation(
        id="obs-1",
        text="Contrast is estimated below the WCAG reference threshold.",
        metric_evidence=["lucidui.raw.contrast.averageContrastRatio"],
        category="observation",
    )
    llm_result = _llm_result(observations=[obs])
    sections = {s.id: s for s in _build(llm_result=llm_result).metric_sections}
    assert sections["contrast"].explanation == obs.text


def test_one_observation_can_link_to_multiple_sections() -> None:
    obs = LLMObservation(
        id="obs-1",
        text="Contrast and clutter were both measured as proxy signals.",
        metric_evidence=["lucidui.raw.contrast", "lucidui.raw.clutter"],
        category="observation",
    )
    llm_result = _llm_result(observations=[obs])
    sections = {s.id: s for s in _build(llm_result=llm_result).metric_sections}
    assert sections["contrast"].explanation == obs.text
    assert sections["visual-complexity"].explanation == obs.text


def test_hicks_law_evidence_does_not_leak_into_unrelated_sections() -> None:
    obs = LLMObservation(
        id="obs-1",
        text="Hick's law time estimate is based on the detected element count.",
        metric_evidence=["lucidui.raw.elements.hicksLawEstimateMs"],
        category="observation",
    )
    llm_result = _llm_result(observations=[obs])
    sections = {s.id: s for s in _build(llm_result=llm_result).metric_sections}
    assert sections["hicks-law"].explanation == obs.text
    # Shares the same underlying raw.elements key, so it is legitimately
    # also relevant to the elements/target-size section.
    assert sections["elements-target-size"].explanation == obs.text
    # But must not leak into an unrelated section such as grouping.
    assert sections["grouping"].explanation == "No LLM interpretation is linked to this metric."


def test_no_matching_observation_falls_back_to_deterministic_placeholder() -> None:
    sections = {s.id: s for s in _build().metric_sections}
    assert sections["colorfulness"].explanation == "No LLM interpretation is linked to this metric."


def test_no_llm_observations_at_all_falls_back_for_every_section() -> None:
    """Disabled/unavailable/failed LLM results always carry `observations: []`,
    so every section must fall back uniformly without special-casing status."""
    llm_result = _llm_result(status=LLMStatus.DISABLED, provider=None, summary=None, observations=[])
    presentation = _build(llm_result=llm_result)
    assert presentation.summary == "No LLM summary is available for this analysis."
    for section in presentation.metric_sections:
        assert section.explanation == "No LLM interpretation is linked to this metric."


# ---------- composite ----------


def test_composite_explanation_is_a_fixed_non_verdict_disclaimer() -> None:
    composite = _build().composite
    assert composite.value == 47.8
    assert composite.raw_display == "47.8 / 100"
    assert "not a quality" in composite.explanation.lower()
    assert composite.context == AnalysisContext.GENERAL


# ---------- recommendations / limitations passthrough ----------


def test_recommendations_and_limitations_pass_through_with_a_fixed_disclaimer_prefix() -> None:
    llm_result = _llm_result(recommendations=["Review the contrast ratio."], limitations=["OCR dependency."])
    presentation = _build(llm_result=llm_result)
    assert presentation.recommendations == ["Review the contrast ratio."]
    assert presentation.limitations[0].startswith("Every metric above is a deterministic proxy signal")
    assert "OCR dependency." in presentation.limitations


def test_closing_note_reuses_the_passed_in_note_verbatim() -> None:
    presentation = _build(closing_note="exact note text")
    assert presentation.closing_note == "exact note text"


# ---------- UIClip summary card ----------


def test_uiclip_card_for_completed_mock_provider() -> None:
    uiclip_result = _uiclip_result(
        status=UIClipStatus.COMPLETED,
        model_version="mock-uiclip-v1",
        description="A software user interface screenshot.",
        description_source=DescriptionSource.GENERIC,
        quality_score=21.7,
    )
    card = _build(uiclip_result=uiclip_result).uiclip_summary
    assert card.model_id == "mock-uiclip-v1"
    assert card.user_description is None  # generic fallback, not a real user description
    assert card.raw_score_display == "21.70"
    assert card.score_type == "Learned raw model score"
    assert card.normalized_score_display is None
    assert card.comparable_to_lucidui is False
    assert "not directly comparable" in card.comparability_note


def test_uiclip_card_for_completed_real_provider_with_user_description() -> None:
    uiclip_result = _uiclip_result(
        status=UIClipStatus.COMPLETED,
        model_version="biglab/uiclip_jitteredwebsites-2-224-paraphrased",
        description="A checkout flow with a payment form",
        description_source=DescriptionSource.USER,
        quality_score=12.345,
    )
    card = _build(uiclip_result=uiclip_result).uiclip_summary
    assert card.model_id == "biglab/uiclip_jitteredwebsites-2-224-paraphrased"
    assert card.user_description == "A checkout flow with a payment form"
    assert card.raw_score_display == "12.35"  # 12.345 rounded, half-to-even -> 12.34; assert format only
    assert card.score_type == "Learned raw model score"


def test_uiclip_card_for_disabled_status() -> None:
    uiclip_result = _uiclip_result(
        enabled=False,
        status=UIClipStatus.DISABLED,
        model_version=None,
        description=None,
        description_source=None,
        quality_score=None,
    )
    card = _build(uiclip_result=uiclip_result).uiclip_summary
    assert card.status == UIClipStatus.DISABLED
    assert card.model_id is None
    assert card.user_description is None
    assert card.raw_score_display is None
    assert card.score_type is None
    assert card.normalized_score_display is None
    assert "not directly comparable" in card.comparability_note


def test_uiclip_card_for_unavailable_status() -> None:
    uiclip_result = _uiclip_result(
        status=UIClipStatus.UNAVAILABLE,
        model_version=None,
        quality_score=None,
        description_source=DescriptionSource.GENERIC,
    )
    card = _build(uiclip_result=uiclip_result).uiclip_summary
    assert card.status == UIClipStatus.UNAVAILABLE
    assert card.raw_score_display is None
    assert card.score_type is None


def test_uiclip_card_for_failed_status() -> None:
    uiclip_result = _uiclip_result(
        status=UIClipStatus.FAILED,
        model_version=None,
        quality_score=None,
        description_source=DescriptionSource.GENERIC,
    )
    card = _build(uiclip_result=uiclip_result).uiclip_summary
    assert card.status == UIClipStatus.FAILED
    assert card.raw_score_display is None
    assert card.model_id is None


# ---------- no mutation of original inputs ----------


def test_builder_does_not_mutate_its_inputs() -> None:
    metric_result = _metric_result()
    llm_result = _llm_result(
        observations=[
            LLMObservation(
                id="obs-1", text="x", metric_evidence=["lucidui.raw.contrast"], category="observation"
            )
        ],
        recommendations=["r1"],
        limitations=["l1"],
    )
    uiclip_result = _uiclip_result()

    metric_snapshot = metric_result.model_dump()
    llm_snapshot = llm_result.model_dump()
    uiclip_snapshot = uiclip_result.model_dump()

    _build(metric_result=metric_result, llm_result=llm_result, uiclip_result=uiclip_result)

    assert metric_result.model_dump() == metric_snapshot
    assert llm_result.model_dump() == llm_snapshot
    assert uiclip_result.model_dump() == uiclip_snapshot


def test_builder_is_deterministic_for_the_same_inputs() -> None:
    metric_result = _metric_result()
    llm_result = _llm_result()
    uiclip_result = _uiclip_result()

    first = build_presentation(
        context=AnalysisContext.GENERAL,
        metric_result=metric_result,
        llm_result=llm_result,
        uiclip_result=uiclip_result,
        closing_note="note",
    )
    second = build_presentation(
        context=AnalysisContext.GENERAL,
        metric_result=metric_result,
        llm_result=llm_result,
        uiclip_result=uiclip_result,
        closing_note="note",
    )
    assert first == second
