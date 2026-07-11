"""Analysis endpoints.

Phase 2A: `/analyses/single` accepts a real multipart image upload, validates
and decodes it in memory, and returns a temporary "accepted" response — no
metric, LLM, or UIClip stage runs yet (Phase 2B+, see ROADMAP.md).
`/analyses/variants` remains out of scope until Phase 7. Routes here only
parse input and delegate to AnalysisService; all business logic lives in the
service/images layers per CLAUDE.md.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.dependencies import get_analysis_service
from app.schemas.analysis import AnalysisAcceptedResponse, AnalysisReport
from app.schemas.common import AnalysisContext
from app.services.analysis_service import AnalysisService

router = APIRouter()


@router.post("/analyses/single", response_model=AnalysisAcceptedResponse)
async def create_single_analysis(
    image: UploadFile = File(...),
    context: str = Form(default=AnalysisContext.GENERAL.value),
    description: str | None = Form(default=None),
    run_llm: bool = Form(default=True, alias="runLlm"),
    run_uiclip: bool = Form(default=True, alias="runUiclip"),
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisAcceptedResponse:
    data = await image.read()
    return service.accept_single_analysis_image(
        data=data,
        content_type=image.content_type,
        context=context,
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisReport)
def get_analysis(
    analysis_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisReport:
    return service.get_report(analysis_id)


@router.get("/analyses/{analysis_id}/raw", response_model=AnalysisReport)
def get_analysis_raw(
    analysis_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisReport:
    return service.get_raw_report(analysis_id)
