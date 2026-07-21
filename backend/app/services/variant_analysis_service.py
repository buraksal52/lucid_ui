"""Use-case coordinator for variant (two-image) comparison (ROADMAP Phase 7).

Runs the existing, unmodified `AnalysisService.create_single_analysis` once
per uploaded image, concurrently (each on its own thread, via
`asyncio.to_thread`, since `create_single_analysis` is fully synchronous —
see app.services.analysis_service), then builds a relative-delta summary
from the two resulting reports via the pure
`app.presentation.variant_delta_builder.build_variant_deltas`. Neither image
nor either report influences the other's analysis in any way: each is
exactly the same computation `POST /analyses/single` would have produced on
its own, and each is independently persisted (and independently retrievable
via `GET /analyses/{analysisId}`) as a side effect of
`create_single_analysis` — this service adds no new persistence for the
outer variant envelope itself. Routes must only parse input and call this
service; all orchestration logic lives here, per CLAUDE.md.
"""

import asyncio
import time
import uuid

from app.presentation.variant_delta_builder import build_variant_deltas
from app.schemas.analysis import AnalysisReport
from app.schemas.common import AnalysisContext, AnalysisMode, AnalysisStatus
from app.schemas.variants import VariantAnalysisReport, VariantTimingResult
from app.services.analysis_service import AnalysisService

_NOTE = (
    "These results are independent design signals for review, not objective verdicts. "
    "Variant A and variant B were analyzed independently of one another; deltas describe "
    "relative differences only, not which variant is better."
)


class VariantAnalysisService:
    """Coordinates variant-comparison creation: run both single analyses
    concurrently, then build relative deltas between them."""

    def __init__(self, analysis_service: AnalysisService) -> None:
        self._analysis_service = analysis_service

    async def create_variant_analysis(
        self,
        data_a: bytes,
        content_type_a: str | None,
        data_b: bytes,
        content_type_b: str | None,
        context: str,
        run_llm: bool = True,
        run_uiclip: bool = True,
        description_a: str | None = None,
        description_b: str | None = None,
    ) -> VariantAnalysisReport:
        start = time.monotonic()

        variant_a, variant_b = await asyncio.gather(
            asyncio.to_thread(
                self._analysis_service.create_single_analysis,
                data=data_a,
                content_type=content_type_a,
                context=context,
                run_llm=run_llm,
                run_uiclip=run_uiclip,
                description=description_a,
            ),
            asyncio.to_thread(
                self._analysis_service.create_single_analysis,
                data=data_b,
                content_type=content_type_b,
                context=context,
                run_llm=run_llm,
                run_uiclip=run_uiclip,
                description=description_b,
            ),
        )

        deltas_start = time.monotonic()
        deltas = build_variant_deltas(variant_a, variant_b)
        deltas_ms = round((time.monotonic() - deltas_start) * 1000)

        timings = VariantTimingResult(
            total_ms=round((time.monotonic() - start) * 1000),
            variant_a_ms=variant_a.timings.total_ms,
            variant_b_ms=variant_b.timings.total_ms,
            deltas_ms=deltas_ms,
        )

        return VariantAnalysisReport(
            analysis_id=str(uuid.uuid4()),
            mode=AnalysisMode.VARIANTS,
            context=AnalysisContext(context),
            status=self._compute_status(variant_a, variant_b),
            variant_a=variant_a,
            variant_b=variant_b,
            deltas=deltas,
            timings=timings,
            note=_NOTE,
        )

    @staticmethod
    def _compute_status(variant_a: AnalysisReport, variant_b: AnalysisReport) -> AnalysisStatus:
        """Mirrors `AnalysisService._compute_status`'s semantics one level up:
        `completed` only when both variants themselves completed every
        requested stage; otherwise `partial_success`."""
        if variant_a.status == AnalysisStatus.COMPLETED and variant_b.status == AnalysisStatus.COMPLETED:
            return AnalysisStatus.COMPLETED
        return AnalysisStatus.PARTIAL_SUCCESS
