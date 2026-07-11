"""Analysis endpoints.

Phase 1 only: a JSON-only mock `/analyses/single`, plus retrieval endpoints.
`/analyses/variants` and image upload are out of scope until Phase 2/7 — see
ROADMAP.md. Routes here only parse input and delegate to AnalysisService; all
report-construction logic lives in the service layer per CLAUDE.md.
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_analysis_service
from app.schemas.analysis import AnalysisReport, SingleAnalysisRequest
from app.services.analysis_service import AnalysisService

router = APIRouter()


@router.post("/analyses/single", response_model=AnalysisReport)
def create_single_analysis(
    payload: SingleAnalysisRequest,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisReport:
    return service.create_single_analysis(payload)


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
