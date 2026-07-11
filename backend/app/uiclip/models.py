"""Internal UIClip provider output shape.

A provider's `evaluate()` call returns a plain dict, which
`UIClipEvaluationService` validates against this model *before* mapping it
onto the public `UIClipResult` (app.schemas.uiclip). Kept as a separate,
internal (non-`CamelModel`) schema, mirroring `app.llm.models`, so a
malformed provider response fails validation here rather than silently
reshaping the public API contract.

`raw_score` intentionally has no assumed range or "quality percentage"
meaning: the official UIClip paper (arXiv:2404.12500) computes its score as
the dot product between image and text embeddings — an uncalibrated,
CLIP-style similarity/logit value, not a documented 0-100 or 0-1 quality
score. See docs/research/uiclip-integration.md for the verified findings
behind this design choice.
"""

from pydantic import BaseModel, Field


class UIClipProviderOutput(BaseModel):
    model_version: str
    raw_score: float
    observations: list[str] = Field(default_factory=list)
