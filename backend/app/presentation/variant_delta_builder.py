"""Pure builder for variant-comparison deltas (ROADMAP Phase 7).

Turns two already-computed `AnalysisReport`s (variant A and variant B, each
produced once by the existing, unmodified `AnalysisService.create_single_analysis`)
into a `VariantDeltas` object. Deliberately has no dependency on FastAPI, a
repository, or any provider — the same two inputs always produce the same
output, mirroring `app.presentation.report_builder`. Never recomputes a
metric and never re-calls a provider; only reads each report's
already-computed `presentation`/`uiclip` output.

All deltas are variant B minus variant A. `normalizedScore`/`qualityScore`
deltas are only computed when both sides have a non-null value — never
invented when either is missing. Direction is reported as
`higher`/`lower`/`equal`/`not_available`, never `better`/`worse` — see
CLAUDE.md ("Flashlight, Not a Judge").

`uiclip`'s raw `qualityScore` (not `normalizedQualityScore`, which is always
null — see docs/api/api-contract.md) is the delta basis: comparing the same
model's raw score across two images is exactly the pairwise use the UIClip
paper describes, unlike comparing UIClip to LucidUI which has no verified
common scale.
"""

from app.presentation.formatting import format_delta
from app.schemas.analysis import AnalysisReport
from app.schemas.common import DeltaDirection, UIClipStatus
from app.schemas.variants import MetricDelta, VariantDeltas

_NOTE = (
    "Deltas are computed as variant B minus variant A, using each variant's already-computed "
    "presentation/UIClip output. A missing delta means one or both variants did not produce a "
    "value for that signal."
)


def _direction(delta: float | None) -> DeltaDirection:
    if delta is None:
        return DeltaDirection.NOT_AVAILABLE
    if delta > 0:
        return DeltaDirection.HIGHER
    if delta < 0:
        return DeltaDirection.LOWER
    return DeltaDirection.EQUAL


def _build_metric_deltas(variant_a: AnalysisReport, variant_b: AnalysisReport) -> list[MetricDelta]:
    # Both sides' `metricSections` are built from the same fixed, ordered
    # spec list in report_builder.py, so index-aligned zipping always pairs
    # the same metric on both sides.
    sections_a = variant_a.presentation.metric_sections
    sections_b = variant_b.presentation.metric_sections
    deltas: list[MetricDelta] = []
    for section_a, section_b in zip(sections_a, sections_b):
        score_a = section_a.normalized_score
        score_b = section_b.normalized_score
        delta = score_b - score_a if score_a is not None and score_b is not None else None
        deltas.append(
            MetricDelta(
                id=section_a.id,
                title=section_a.title,
                category=section_a.category,
                normalized_score_delta=delta,
                raw_display_a=section_a.raw_display,
                raw_display_b=section_b.raw_display,
                direction=_direction(delta),
            )
        )
    return deltas


def _uiclip_score_delta(variant_a: AnalysisReport, variant_b: AnalysisReport) -> float | None:
    if variant_a.uiclip.status != UIClipStatus.COMPLETED or variant_b.uiclip.status != UIClipStatus.COMPLETED:
        return None
    score_a = variant_a.uiclip.quality_score
    score_b = variant_b.uiclip.quality_score
    if score_a is None or score_b is None:
        return None
    return score_b - score_a


def build_variant_deltas(variant_a: AnalysisReport, variant_b: AnalysisReport) -> VariantDeltas:
    composite_delta = variant_b.presentation.composite.value - variant_a.presentation.composite.value
    uiclip_delta = _uiclip_score_delta(variant_a, variant_b)
    return VariantDeltas(
        composite_score_delta=composite_delta,
        composite_score_delta_display=format_delta(composite_delta, 2),
        uiclip_raw_score_delta=uiclip_delta,
        uiclip_raw_score_delta_display=format_delta(uiclip_delta, 2),
        metric_deltas=_build_metric_deltas(variant_a, variant_b),
        note=_NOTE,
    )
