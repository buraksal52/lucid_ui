"""Single-analysis request/response schemas.

`SingleAnalysisRequest` is Phase 1's temporary JSON-only request body — it
accepts no image, per the roadmap (image upload is Phase 2). `context` is kept
as a plain string here rather than the `AnalysisContext` enum so the service
layer can raise the documented `INVALID_CONTEXT` domain error instead of a
generic schema validation error; see app.services.analysis_service.
"""

from pydantic import Field, field_validator

from app.schemas.common import AnalysisContext, AnalysisMode, AnalysisStatus, CamelModel
from app.schemas.comparison import ComparisonResult
from app.schemas.llm import LLMInterpretationResult
from app.schemas.metrics import LucidUIResult
from app.schemas.uiclip import UIClipResult


class SingleAnalysisRequest(CamelModel):
    context: str = Field(default=AnalysisContext.GENERAL.value)
    description: str | None = Field(default=None)
    run_llm: bool = Field(default=True)
    run_uiclip: bool = Field(default=True)

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class ImageMetadata(CamelModel):
    width: int
    height: int
    format: str
    size_bytes: int


class TimingResult(CamelModel):
    total_ms: int
    lucidui_ms: int
    llm_ms: int
    uiclip_ms: int
    comparison_ms: int


class AnalysisReport(CamelModel):
    schema_version: str = Field(default="1.0")
    analysis_id: str
    mode: AnalysisMode = Field(default=AnalysisMode.SINGLE)
    context: AnalysisContext
    status: AnalysisStatus
    image_metadata: ImageMetadata
    lucidui: LucidUIResult
    llm_interpretation: LLMInterpretationResult
    uiclip: UIClipResult
    comparison: ComparisonResult
    timings: TimingResult
    note: str
