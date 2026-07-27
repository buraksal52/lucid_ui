"""Single-analysis request/response schemas.

`AnalysisReport` is the full report returned by `POST /analyses/single` and
`GET /analyses/{id}` as of Phase 2B-2. `image_metadata` and `lucidui` reuse
the real Phase 2A/2B-1 types directly (`app.images.models.ImageMetadata`,
`app.metrics.models.DeterministicMetricResult`) rather than separate,
independently-shaped schemas, so the report always reflects exactly what the
image decoder and metric engine actually produced — no field is renamed or
re-derived at this boundary. See docs/api/api-contract.md.
"""

from pydantic import Field

from app.images.models import ImageMetadata
from app.metrics.models import DeterministicMetricResult
from app.schemas.common import AnalysisContext, AnalysisMode, AnalysisStatus, CamelModel
from app.schemas.comparison import ComparisonResult
from app.schemas.llm import LLMInterpretationResult
from app.schemas.presentation import PresentationReport
from app.schemas.uiclip import UIClipResult


class TimingResult(CamelModel):
    total_ms: int
    lucidui_ms: int
    llm_ms: int
    uiclip_ms: int
    comparison_ms: int


class AnalysisReport(CamelModel):
    schema_version: str = Field(default="2.0")
    analysis_id: str
    mode: AnalysisMode = Field(default=AnalysisMode.SINGLE)
    context: AnalysisContext
    status: AnalysisStatus
    image_metadata: ImageMetadata
    lucidui: DeterministicMetricResult
    llm_interpretation: LLMInterpretationResult
    uiclip: UIClipResult
    comparison: ComparisonResult
    timings: TimingResult
    note: str
    # Additive, backward-compatible: a ready-to-render view over the fields
    # above. Does not replace, rename, or remove any of them — see
    # app.presentation.report_builder and docs/api/presentation-schema.md.
    presentation: PresentationReport
