"""LucidUI deterministic metric engine result schema (mocked in Phase 1).

See docs/metrics/metric-catalog.md for what each metric represents and
docs/metrics/scoring-and-normalization.md for how they combine into a
weighted score. Per-metric substructures inside `raw` are intentionally
loose (`dict[str, Any]`) — see CLAUDE.md: full typing lands with the real
metric engine in Phase 2.
"""

from typing import Any

from pydantic import Field

from app.schemas.common import CamelModel


class LucidUIResult(CamelModel):
    metric_engine_version: str = Field(default="0.1.0-mock")
    raw: dict[str, dict[str, Any]] = Field(default_factory=dict)
    normalized: dict[str, float] = Field(default_factory=dict)
    additional_signals: dict[str, float] = Field(default_factory=dict)
    weighted_score: float
    score_name: str = Field(default="LucidUI Composite Signal Score")
