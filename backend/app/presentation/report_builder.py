"""Pure builder for the Presentation Report layer.

Turns an already-computed `DeterministicMetricResult` + `LLMInterpretationResult`
+ `UIClipResult` into a ready-to-render `PresentationReport`
(`app.schemas.presentation`). Deliberately has no dependency on FastAPI, a
repository, or any provider — it only reads the three result objects it is
given and returns a new `PresentationReport`; the same inputs always produce
the same output. `AnalysisService` is the only caller and only ever hands
over results it has already computed once (see
`AnalysisService.create_single_analysis`) — this module never re-runs the
metric engine, never re-calls the LLM, and never re-calls UIClip.

Metric section order is fixed (see `_METRIC_SECTION_SPECS`) and mirrors
docs/metrics/metric-catalog.md. Each section's `explanation` is populated by
matching `LLMObservation.metric_evidence` JSON-path citations (e.g.
"lucidui.raw.contrast.averageContrastRatio", per app.llm.prompt) against a
fixed set of substring keywords for that metric — never by asking the LLM
again. When no observation's evidence matches a section (including whenever
the LLM stage did not complete, since `observations` is then always empty),
`explanation` falls back to a fixed, non-scientific placeholder string
rather than null, so the frontend never has to special-case a missing
explanation — see CLAUDE.md ("never invent... contradict... fabricate").
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.metrics.models import DeterministicMetricResult
from app.presentation.formatting import (
    format_count,
    format_decimal,
    format_fraction,
    format_ms,
    format_percentage,
    format_plain,
    format_ratio_to_one,
    format_score_over_100,
)
from app.schemas.common import AnalysisContext, DescriptionSource
from app.schemas.llm import LLMInterpretationResult, LLMObservation
from app.schemas.presentation import CompositeSummary, MetricSection, PresentationReport, UIClipPresentationCard
from app.schemas.uiclip import UIClipResult

_TITLE = "LucidUI Design Signal Report"

_NO_LLM_SUMMARY = "No LLM summary is available for this analysis."

_NO_EXPLANATION_FALLBACK = "No LLM interpretation is linked to this metric."

_PROXY_DISCLAIMER = (
    "Every metric above is a deterministic proxy signal for review, not a verdict — see "
    "docs/metrics/metric-catalog.md and docs/metrics/known-limitations.md."
)

_COMPOSITE_EXPLANATION = (
    "This composite score is a weighted signal summary of the metrics above, not a quality "
    "judgment — see docs/metrics/scoring-and-normalization.md."
)

_UICLIP_SCORE_TYPE = "Learned raw model score"

_UICLIP_COMPARABILITY_NOTE = (
    "UIClip's raw score is not directly comparable to LucidUI's weighted composite score — "
    "the two use different scales and methods, and comparison has not been implemented yet "
    "(see ROADMAP.md Phase 6)."
)


@dataclass(frozen=True)
class _MetricSectionFields:
    raw_display: str
    normalized_score: float | None
    source: str | None
    is_proxy: bool
    evidence_paths: tuple[str, ...]


@dataclass(frozen=True)
class _MetricSectionSpec:
    id: str
    title: str
    category: str
    # Lowercase substrings matched against a lowercased `metric_evidence`
    # path; see `_match_explanation`.
    match_keywords: tuple[str, ...]
    extract: Callable[[DeterministicMetricResult], _MetricSectionFields]


def _extract_contrast(m: DeterministicMetricResult) -> _MetricSectionFields:
    raw = m.raw.get("contrast", {})
    normalized_score = m.normalized.get("contrast")
    paths = [
        "lucidui.raw.contrast.averageContrastRatio",
        "lucidui.raw.contrast.regionsAnalyzed",
        "lucidui.raw.contrast.regionsBelowAAThreshold",
    ]
    if normalized_score is not None:
        paths.append("lucidui.normalized.contrast")
    return _MetricSectionFields(
        raw_display=format_ratio_to_one(raw.get("averageContrastRatio")),
        normalized_score=normalized_score,
        source=raw.get("source"),
        is_proxy=bool(raw.get("isProxyMetric", False)),
        evidence_paths=tuple(paths),
    )


def _extract_clutter(m: DeterministicMetricResult) -> _MetricSectionFields:
    raw = m.raw.get("clutter", {})
    normalized_score = m.normalized.get("clutter")
    paths = ["lucidui.raw.clutter.edgeDensity"]
    if normalized_score is not None:
        paths.append("lucidui.normalized.clutter")
    return _MetricSectionFields(
        raw_display=format_decimal(raw.get("edgeDensity"), 4),
        normalized_score=normalized_score,
        source=raw.get("source"),
        is_proxy=bool(raw.get("isProxyMetric", False)),
        evidence_paths=tuple(paths),
    )


def _extract_elements_target_size(m: DeterministicMetricResult) -> _MetricSectionFields:
    raw = m.raw.get("elements", {})
    normalized_score = m.normalized.get("elementSize")
    paths = [
        "lucidui.raw.elements.detectedElementCount",
        "lucidui.raw.elements.contourBasedCount",
        "lucidui.raw.elements.ocrBasedCount",
        "lucidui.raw.elements.smallTargetsBelow44px",
    ]
    if normalized_score is not None:
        paths.append("lucidui.normalized.elementSize")
    return _MetricSectionFields(
        raw_display=format_fraction(raw.get("smallTargetsBelow44px"), raw.get("detectedElementCount")),
        normalized_score=normalized_score,
        source=raw.get("source"),
        is_proxy=bool(raw.get("isProxyMetric", False)),
        evidence_paths=tuple(paths),
    )


def _extract_hicks_law(m: DeterministicMetricResult) -> _MetricSectionFields:
    raw = m.raw.get("elements", {})
    # No normalized form of the Hick's Law estimate exists in
    # `normalize_metrics` — left null rather than invented.
    return _MetricSectionFields(
        raw_display=format_ms(raw.get("hicksLawEstimateMs")),
        normalized_score=None,
        source=raw.get("source"),
        is_proxy=bool(raw.get("isProxyMetric", False)),
        evidence_paths=("lucidui.raw.elements.hicksLawEstimateMs", "lucidui.raw.elements.detectedElementCount"),
    )


def _extract_grouping(m: DeterministicMetricResult) -> _MetricSectionFields:
    raw = m.raw.get("groups", {})
    normalized_score = m.normalized.get("groupCount")
    paths = ["lucidui.raw.groups.estimatedGroupCount"]
    if normalized_score is not None:
        paths.append("lucidui.normalized.groupCount")
    return _MetricSectionFields(
        raw_display=format_count(raw.get("estimatedGroupCount"), "groups"),
        normalized_score=normalized_score,
        source=raw.get("source"),
        is_proxy=bool(raw.get("isProxyMetric", False)),
        evidence_paths=tuple(paths),
    )


def _extract_text_density(m: DeterministicMetricResult) -> _MetricSectionFields:
    raw = m.raw.get("textDensity", {})
    normalized_score = m.normalized.get("textDensity")
    paths = [
        "lucidui.raw.textDensity.textDensityRatio",
        "lucidui.raw.textDensity.fontSizeDiversityProxy",
        "lucidui.raw.textDensity.wordsDetected",
    ]
    if normalized_score is not None:
        paths.append("lucidui.normalized.textDensity")
    return _MetricSectionFields(
        raw_display=format_percentage(raw.get("textDensityRatio")),
        normalized_score=normalized_score,
        # The legacy `analyze_text_density` output has no `source` key —
        # left null rather than invented.
        source=raw.get("source"),
        is_proxy=bool(raw.get("isProxyMetric", False)),
        evidence_paths=tuple(paths),
    )


def _extract_whitespace_alignment(m: DeterministicMetricResult) -> _MetricSectionFields:
    raw = m.raw.get("whitespaceAlignment", {})
    whitespace_display = format_percentage(raw.get("whitespaceRatio"))
    alignment_display = format_decimal(raw.get("alignmentVariance"), 4)
    return _MetricSectionFields(
        raw_display=f"Whitespace {whitespace_display} · Alignment variance {alignment_display}",
        # No normalized form of whitespace/alignment exists in
        # `normalize_metrics` — left null rather than invented.
        normalized_score=None,
        source=raw.get("source"),
        is_proxy=bool(raw.get("isProxyMetric", False)),
        evidence_paths=(
            "lucidui.raw.whitespaceAlignment.whitespaceRatio",
            "lucidui.raw.whitespaceAlignment.alignmentVariance",
        ),
    )


def _extract_colorfulness(m: DeterministicMetricResult) -> _MetricSectionFields:
    raw = m.additional_signals.get("colorfulness", {})
    return _MetricSectionFields(
        raw_display=format_plain(raw.get("colorfulnessScore"), 2),
        normalized_score=None,
        source=raw.get("source"),
        is_proxy=bool(raw.get("isProxyMetric", False)),
        evidence_paths=("lucidui.additionalSignals.colorfulness.colorfulnessScore",),
    )


def _extract_fitts_law(m: DeterministicMetricResult) -> _MetricSectionFields:
    raw = m.additional_signals.get("fittsFullIndexOfDifficulty", {})
    return _MetricSectionFields(
        raw_display=format_plain(raw.get("averageIndexOfDifficulty"), 2),
        normalized_score=None,
        source=raw.get("source"),
        is_proxy=bool(raw.get("isProxyMetric", False)),
        evidence_paths=(
            "lucidui.additionalSignals.fittsFullIndexOfDifficulty.averageIndexOfDifficulty",
            "lucidui.additionalSignals.fittsFullIndexOfDifficulty.elementsConsidered",
        ),
    )


def _extract_visual_balance(m: DeterministicMetricResult) -> _MetricSectionFields:
    raw = m.additional_signals.get("visualBalance", {})
    return _MetricSectionFields(
        raw_display=format_percentage(raw.get("asymmetryScore")),
        normalized_score=None,
        source=raw.get("source"),
        is_proxy=bool(raw.get("isProxyMetric", False)),
        evidence_paths=("lucidui.additionalSignals.visualBalance.asymmetryScore",),
    )


# Fixed, predictable order — see docs/metrics/metric-catalog.md.
_METRIC_SECTION_SPECS: tuple[_MetricSectionSpec, ...] = (
    _MetricSectionSpec("contrast", "Contrast", "contrast", ("raw.contrast", "normalized.contrast"), _extract_contrast),
    _MetricSectionSpec(
        "visual-complexity",
        "Visual Complexity (Edge Density)",
        "visual-complexity",
        ("raw.clutter", "edgedensity", "normalized.clutter"),
        _extract_clutter,
    ),
    _MetricSectionSpec(
        "elements-target-size",
        "Elements & Target Size",
        "elements",
        ("raw.elements", "normalized.elementsize"),
        _extract_elements_target_size,
    ),
    _MetricSectionSpec(
        "hicks-law", "Hick's Law Estimate", "cognitive-load", ("hickslaw",), _extract_hicks_law
    ),
    _MetricSectionSpec(
        "grouping",
        "Grouping (Estimated Group Count)",
        "grouping",
        ("raw.groups", "normalized.groupcount"),
        _extract_grouping,
    ),
    _MetricSectionSpec(
        "text-density",
        "Text Density",
        "text",
        ("raw.textdensity", "normalized.textdensity"),
        _extract_text_density,
    ),
    _MetricSectionSpec(
        "whitespace-alignment",
        "Whitespace & Alignment",
        "layout",
        ("raw.whitespacealignment",),
        _extract_whitespace_alignment,
    ),
    _MetricSectionSpec("colorfulness", "Colorfulness", "color", ("colorfulness",), _extract_colorfulness),
    _MetricSectionSpec(
        "fitts-law", "Fitts's Law (Index of Difficulty)", "interaction", ("fitts",), _extract_fitts_law
    ),
    _MetricSectionSpec("visual-balance", "Visual Balance", "composition", ("visualbalance",), _extract_visual_balance),
)


def _match_explanation(observations: list[LLMObservation], keywords: tuple[str, ...]) -> str | None:
    matched = [
        observation.text
        for observation in observations
        if any(keyword in path.lower() for path in observation.metric_evidence for keyword in keywords)
    ]
    return " ".join(matched) if matched else None


def _build_metric_section(spec: _MetricSectionSpec, metric_result: DeterministicMetricResult,
                           observations: list[LLMObservation]) -> MetricSection:
    fields = spec.extract(metric_result)
    return MetricSection(
        id=spec.id,
        title=spec.title,
        category=spec.category,
        raw_display=fields.raw_display,
        normalized_score=fields.normalized_score,
        explanation=_match_explanation(observations, spec.match_keywords) or _NO_EXPLANATION_FALLBACK,
        evidence_paths=list(fields.evidence_paths),
        source=fields.source,
        is_proxy=fields.is_proxy,
    )


def _build_composite(metric_result: DeterministicMetricResult, context: AnalysisContext) -> CompositeSummary:
    return CompositeSummary(
        raw_display=format_score_over_100(metric_result.weighted_score),
        value=metric_result.weighted_score,
        score_name=metric_result.score_name,
        context=context,
        explanation=_COMPOSITE_EXPLANATION,
    )


def _build_uiclip_summary(uiclip_result: UIClipResult) -> UIClipPresentationCard:
    user_description = uiclip_result.description if uiclip_result.description_source == DescriptionSource.USER else None
    raw_score_display = format_plain(uiclip_result.quality_score, 2) if uiclip_result.quality_score is not None else None
    normalized_score_display = (
        format_plain(uiclip_result.normalized_quality_score, 2)
        if uiclip_result.normalized_quality_score is not None
        else None
    )
    return UIClipPresentationCard(
        status=uiclip_result.status,
        model_id=uiclip_result.model_version,
        user_description=user_description,
        raw_score_display=raw_score_display,
        score_type=_UICLIP_SCORE_TYPE if raw_score_display is not None else None,
        normalized_score_display=normalized_score_display,
        comparable_to_lucidui=False,
        comparability_note=_UICLIP_COMPARABILITY_NOTE,
    )


def build_presentation(
    *,
    context: AnalysisContext,
    metric_result: DeterministicMetricResult,
    llm_result: LLMInterpretationResult,
    uiclip_result: UIClipResult,
    closing_note: str,
) -> PresentationReport:
    """Builds the ready-to-render `PresentationReport` for one already-computed
    analysis. Deterministic: the same four inputs always produce the same
    output. `closing_note` is passed in rather than recomputed here so this
    module never re-derives (or contradicts) `AnalysisReport.note`."""
    metric_sections = [
        _build_metric_section(spec, metric_result, llm_result.observations) for spec in _METRIC_SECTION_SPECS
    ]
    return PresentationReport(
        title=_TITLE,
        context=context,
        summary=llm_result.summary or _NO_LLM_SUMMARY,
        metric_sections=metric_sections,
        composite=_build_composite(metric_result, context),
        uiclip_summary=_build_uiclip_summary(uiclip_result),
        recommendations=list(llm_result.recommendations),
        limitations=[_PROXY_DISCLAIMER, *llm_result.limitations],
        closing_note=closing_note,
    )
