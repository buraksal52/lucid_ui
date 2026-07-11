"""Analysis endpoints.

`/analyses/single` accepts a multipart image upload, validates and decodes
it in memory, runs the deterministic metric engine, interprets the result
with the LLM interpretation layer (unless `runLlm=false`), evaluates the
image independently with the UIClip layer (unless `runUiclip=false`, using
`description` as the submitted description), persists the resulting
`AnalysisReport`, and returns it. `comparison` remains an `unavailable`
placeholder — comparison logic is Phase 6 (see AnalysisService).
`/analyses/variants` remains out of scope until Phase 7. Routes here only
parse input and delegate to AnalysisService; all business logic lives in the
service/images/metrics/llm/uiclip layers per CLAUDE.md.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.dependencies import get_analysis_service
from app.schemas.analysis import AnalysisReport
from app.schemas.common import AnalysisContext
from app.services.analysis_service import AnalysisService

router = APIRouter()


@router.post("/analyses/single", response_model=AnalysisReport)
async def create_single_analysis(
    image: UploadFile = File(...),
    context: str = Form(default=AnalysisContext.GENERAL.value),
    description: str | None = Form(default=None),
    run_llm: bool = Form(default=True, alias="runLlm"),
    run_uiclip: bool = Form(default=True, alias="runUiclip"),
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisReport:
    data = await image.read()
    return service.create_single_analysis(
        data=data,
        content_type=image.content_type,
        context=context,
        run_llm=run_llm,
        run_uiclip=run_uiclip,
        description=description,
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
