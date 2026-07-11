"""Typed, JSON-safe result of the deterministic metric engine.

Wraps the legacy engine's `raw` / `normalized` / `additionalSignals` output
(backend/reference/legacy_metric_engine.py) plus the weighted composite
score. Nested legacy field names (e.g. `averageContrastRatio`,
`hicksLawEstimateMs`, `estimatedGroupCount`) are preserved exactly as
flexible dictionaries — this model must never rename or drop a legacy
field; only the outer field names use CamelModel's camelCase aliasing.
See docs/metrics/scoring-and-normalization.md.
"""

from typing import Any

from pydantic import Field

from app.schemas.common import CamelModel


class DeterministicMetricResult(CamelModel):
    raw: dict[str, dict[str, Any]]
    normalized: dict[str, float | None]
    additional_signals: dict[str, dict[str, Any]]
    weighted_score: float
    score_name: str = Field(default="LucidUI Composite Signal Score")
    metric_engine_version: str = Field(default="legacy-v1")
