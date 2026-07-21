"""Analysis endpoints.

`/analyses/single` accepts a multipart image upload, validates and decodes
it in memory, runs the deterministic metric engine, interprets the result
with the LLM interpretation layer (unless `runLlm=false`), evaluates the
image independently with the UIClip layer (unless `runUiclip=false`, using
`description` as the submitted description), persists the resulting
`AnalysisReport`, and returns it. `comparison` remains an `unavailable`
placeholder — comparison logic is Phase 6 (see AnalysisService).

`/analyses/variants` (Phase 7) accepts two multipart image uploads and runs
`/analyses/single`'s exact same pipeline on each, concurrently, then returns
both reports plus relative deltas between them (see
VariantAnalysisService). Routes here only parse input and delegate to a
service; all business logic lives in the service/images/metrics/llm/uiclip
layers per CLAUDE.md.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.dependencies import get_analysis_service, get_variant_analysis_service
from app.schemas.analysis import AnalysisReport
from app.schemas.common import AnalysisContext
from app.schemas.variants import VariantAnalysisReport
from app.services.analysis_service import AnalysisService
from app.services.variant_analysis_service import VariantAnalysisService

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


@router.post("/analyses/variants", response_model=VariantAnalysisReport)
async def create_variant_analysis(
    image_a: UploadFile = File(..., alias="imageA"),
    image_b: UploadFile = File(..., alias="imageB"),
    context: str = Form(default=AnalysisContext.GENERAL.value),
    description_a: str | None = Form(default=None, alias="descriptionA"),
    description_b: str | None = Form(default=None, alias="descriptionB"),
    run_llm: bool = Form(default=True, alias="runLlm"),
    run_uiclip: bool = Form(default=True, alias="runUiclip"),
    service: VariantAnalysisService = Depends(get_variant_analysis_service),
) -> VariantAnalysisReport:
    data_a = await image_a.read()
    data_b = await image_b.read()
    return await service.create_variant_analysis(
        data_a=data_a,
        content_type_a=image_a.content_type,
        data_b=data_b,
        content_type_b=image_b.content_type,
        context=context,
        run_llm=run_llm,
        run_uiclip=run_uiclip,
        description_a=description_a,
        description_b=description_b,
    )
