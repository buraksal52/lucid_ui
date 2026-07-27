"""Variant-comparison request/response schemas (ROADMAP Phase 7).

`VariantAnalysisReport` is returned by `POST /analyses/variants`. It wraps
two independently-computed `AnalysisReport`s (see `app.schemas.analysis`,
each produced by the existing, unmodified `AnalysisService.create_single_analysis`)
plus `deltas` — relative differences between them. Deltas are computed once,
here and in `app.presentation.variant_delta_builder`, from each variant's
already-computed `presentation`/`uiclip` output; no metric is recomputed and
no provider is called again, matching the same "additive, pure builder"
approach as `app.presentation.report_builder`. See docs/api/report-schema.md.
"""

from pydantic import Field

from app.schemas.analysis import AnalysisReport
from app.schemas.common import AnalysisContext, AnalysisMode, AnalysisStatus, CamelModel, DeltaDirection


class MetricDelta(CamelModel):
    """One metric's variant-B-minus-variant-A comparison.

    `normalized_score_delta` is only ever set when both variants produced a
    normalized score for this metric (see `app.schemas.presentation.MetricSection`)
    — never invented when either side is missing one.
    """

    id: str
    title: str
    category: str
    normalized_score_delta: float | None = None
    raw_display_a: str
    raw_display_b: str
    direction: DeltaDirection


class VariantDeltas(CamelModel):
    """Relative differences between variant A and variant B.

    All numeric deltas are variant B minus variant A. Every delta ships with
    a pre-formatted display string so the frontend never computes or formats
    a number itself — see docs/frontend/FRONTEND_GUIDE.md.
    """

    composite_score_delta: float | None = None
    composite_score_delta_display: str
    uiclip_raw_score_delta: float | None = None
    uiclip_raw_score_delta_display: str
    metric_deltas: list[MetricDelta] = Field(default_factory=list)
    note: str


class VariantTimingResult(CamelModel):
    total_ms: int
    variant_a_ms: int
    variant_b_ms: int
    deltas_ms: int


class VariantAnalysisReport(CamelModel):
    schema_version: str = Field(default="2.0")
    analysis_id: str
    mode: AnalysisMode = Field(default=AnalysisMode.VARIANTS)
    context: AnalysisContext
    status: AnalysisStatus
    variant_a: AnalysisReport
    variant_b: AnalysisReport
    deltas: VariantDeltas
    timings: VariantTimingResult
    note: str
