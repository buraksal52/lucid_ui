"""Internal structured LLM response shape.

A provider's `complete()` call returns a plain dict, which
`LLMInterpretationService` validates against this model *before* mapping it
onto the public `LLMInterpretationResult` (app.schemas.llm) by attaching
`status`/`provider`. Kept as a separate, internal (non-`CamelModel`) schema
so a malformed or incomplete provider response fails validation here, inside
the LLM layer, rather than silently reshaping the public API contract.
"""

from pydantic import BaseModel, Field


class LLMObservationOutput(BaseModel):
    id: str
    text: str
    metric_evidence: list[str] = Field(default_factory=list)
    category: str = Field(default="observation")


class LLMStructuredOutput(BaseModel):
    summary: str
    observations: list[LLMObservationOutput] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
