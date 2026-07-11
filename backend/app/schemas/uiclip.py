"""UIClip evaluator result schema (mocked in Phase 1, real model in Phase 5).

UIClip is an independent learned evaluator, never treated as ground truth —
see ADR-004. `preference_score`/`normalized_quality_score` are model
preference signals, not objective quality percentages.
"""

from pydantic import Field

from app.schemas.common import CamelModel, DescriptionSource, UIClipStatus


class UIClipResult(CamelModel):
    enabled: bool
    status: UIClipStatus
    model_version: str | None = None
    description: str | None = None
    description_source: DescriptionSource | None = None
    quality_score: float | None = None
    normalized_quality_score: float | None = None
    observations: list[str] = Field(default_factory=list)
    inference_time_ms: int = 0
