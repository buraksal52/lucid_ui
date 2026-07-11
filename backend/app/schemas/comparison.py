"""Comparison Engine result schema.

Reports agreements and discrepancies between LucidUI's interpreted metrics and
UIClip's output — it never resolves a disagreement in favor of either system,
per ADR-004. When UIClip did not run, `agreement_level` is `unavailable` and
no comparison is implied.
"""

from pydantic import Field

from app.schemas.common import AgreementLevel, CamelModel


class ComparisonResult(CamelModel):
    lucidui_weighted_score: float | None = None
    uiclip_normalized_quality_score: float | None = None
    absolute_score_difference: float | None = None
    agreement_level: AgreementLevel
    shared_findings: list[str] = Field(default_factory=list)
    lucidui_only_findings: list[str] = Field(default_factory=list)
    uiclip_only_findings: list[str] = Field(default_factory=list)
    interpretation: str | None = None
