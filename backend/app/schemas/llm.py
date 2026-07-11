"""LLM interpretation result schema (mocked in Phase 1, real provider in Phase 3).

The LLM only ever interprets LucidUI's deterministic metric JSON — never a raw
image — per ADR-003. Every observation must cite the metric(s) it is based on
via `metric_evidence`.
"""

from pydantic import Field

from app.schemas.common import CamelModel, LLMStatus


class LLMObservation(CamelModel):
    id: str
    text: str
    metric_evidence: list[str] = Field(default_factory=list)
    category: str = Field(default="observation")


class LLMInterpretationResult(CamelModel):
    status: LLMStatus
    provider: str | None = None
    summary: str | None = None
    observations: list[LLMObservation] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
