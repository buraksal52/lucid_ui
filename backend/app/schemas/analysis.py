"""Single-analysis request/response schemas.

`AnalysisAcceptedResponse` is Phase 2A's temporary response for
`POST /analyses/single`: the endpoint now accepts a real multipart image
upload and validates/decodes it, but does not yet run any metric, LLM, or
UIClip stage (those land in Phase 2B+), so it cannot return a full
`AnalysisReport` yet. See docs/api/api-contract.md.
"""

from typing import Literal

from pydantic import Field

from app.images.models import ImageMetadata as DecodedImageMetadata
from app.schemas.common import AnalysisContext, AnalysisMode, AnalysisStatus, CamelModel
from app.schemas.comparison import ComparisonResult
from app.schemas.llm import LLMInterpretationResult
from app.schemas.metrics import LucidUIResult
from app.schemas.uiclip import UIClipResult


class AnalysisAcceptedResponse(CamelModel):
    """Temporary Phase 2A response: the image was validated and decoded, but
    no analysis has run yet."""

    analysis_id: str
    status: Literal["accepted"] = "accepted"
    image_metadata: DecodedImageMetadata
    message: str = Field(default="Image successfully validated and decoded.")


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
