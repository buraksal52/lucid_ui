"""Presentation Report schema — a ready-to-render view of an already-computed
`AnalysisReport`.

`PresentationReport` is purely a display-oriented re-arrangement of
`lucidui`, `llmInterpretation`, and `uiclip`: no new metric is computed here,
no provider is called again, and no numeric value differs from what those
sections already contain — see `app.presentation.report_builder` and
CLAUDE.md ("Never discard raw values", "LLMs are interpreters", "UIClip is
not ground truth"). It is additive to `AnalysisReport` and does not replace,
rename, or remove any existing field — see docs/api/api-contract.md
("Public API schemas are contracts").

The frontend should render `presentation` directly rather than re-deriving
metric meaning, field mapping, generated text, or scores from `lucidui`,
`llmInterpretation`, or `uiclip` itself — see docs/frontend/FRONTEND_GUIDE.md.
"""

from pydantic import Field

from app.schemas.common import AnalysisContext, CamelModel, UIClipStatus


class MetricSection(CamelModel):
    """One ready-to-render metric card. `normalizedScore` is only ever set
    when the deterministic engine actually produced a normalized value for
    this metric (see `app.metrics.models`/legacy `normalize_metrics`) — it
    is never invented for additional signals that have no normalized form.
    """

    id: str
    title: str
    category: str
    raw_display: str
    normalized_score: float | None = None
    explanation: str | None = None
    evidence_paths: list[str] = Field(default_factory=list)
    source: str | None = None
    is_proxy: bool = False


class CompositeSummary(CamelModel):
    """The LucidUI weighted composite score, presentation-formatted.
    `explanation` is a fixed disclaimer, never a generated verdict."""

    raw_display: str
    value: float
    score_name: str
    context: AnalysisContext
    explanation: str


class UIClipPresentationCard(CamelModel):
    """A standalone summary card for UIClip's independent evaluation.
    `comparableToLucidui` is always `false` and `comparabilityNote` always
    present — comparison between LucidUI and UIClip is not implemented yet
    (see ROADMAP.md Phase 6), so this card never implies one exists."""

    status: UIClipStatus
    model_id: str | None = None
    user_description: str | None = None
    raw_score_display: str | None = None
    score_type: str | None = None
    normalized_score_display: str | None = None
    comparable_to_lucidui: bool = False
    comparability_note: str


class PresentationReport(CamelModel):
    title: str
    context: AnalysisContext
    summary: str
    metric_sections: list[MetricSection] = Field(default_factory=list)
    composite: CompositeSummary
    uiclip_summary: UIClipPresentationCard
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    closing_note: str
