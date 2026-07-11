"""Use-case coordinator for analyses.

Phase 2B-2: validates and decodes an uploaded image, runs the deterministic
`MetricEngine` against it exactly once, assembles a full `AnalysisReport`,
and persists it. LLM interpretation and UIClip evaluation don't exist yet
(Phase 3+), so their report sections use the project's existing
`disabled`/`unavailable` status design rather than fabricated data — see
docs/api/report-schema.md. Routes must only parse input and call this
service; all orchestration logic lives here, per CLAUDE.md ("Do not put
business logic inside FastAPI route functions").
"""

import time
import uuid

from app.core.exceptions import AnalysisNotFoundError, InvalidContextError
from app.core.logging import get_logger
from app.images.decoder import ImageDecoder
from app.images.validator import ImageValidator
from app.metrics.engine import MetricEngine
from app.metrics.models import DeterministicMetricResult
from app.repositories.base import AnalysisRepository
from app.schemas.analysis import AnalysisReport, TimingResult
from app.schemas.comparison import ComparisonResult
from app.schemas.common import ALLOWED_CONTEXTS, AgreementLevel, AnalysisContext, AnalysisStatus, LLMStatus, UIClipStatus
from app.schemas.llm import LLMInterpretationResult
from app.schemas.uiclip import UIClipResult

logger = get_logger("lucidui.analysis")

_NOTE = (
    "These results are design signals for review, not objective verdicts. "
    "LLM interpretation and UIClip evaluation are not yet implemented (see ROADMAP.md)."
)


class AnalysisService:
    """Coordinates single-analysis creation (validate -> decode -> metrics ->
    persist) and report retrieval."""

    def __init__(
        self,
        repository: AnalysisRepository,
        image_validator: ImageValidator,
        image_decoder: ImageDecoder,
        metric_engine: MetricEngine,
    ) -> None:
        self._repository = repository
        self._image_validator = image_validator
        self._image_decoder = image_decoder
        self._metric_engine = metric_engine

    def create_single_analysis(
        self,
        data: bytes,
        content_type: str | None,
        context: str,
    ) -> AnalysisReport:
        context_enum = self._validate_context(context)
        start = time.monotonic()

        self._image_validator.validate(content_type, data)
        decoded = self._image_decoder.decode(data, content_type)

        metrics_start = time.monotonic()
        metric_result = self._metric_engine.analyze(decoded, context_enum)
        lucidui_ms = round((time.monotonic() - metrics_start) * 1000)

        analysis_id = str(uuid.uuid4())
        timings = TimingResult(
            total_ms=round((time.monotonic() - start) * 1000),
            lucidui_ms=lucidui_ms,
            llm_ms=0,
            uiclip_ms=0,
            comparison_ms=0,
        )

        report = AnalysisReport(
            analysis_id=analysis_id,
            context=context_enum,
            status=AnalysisStatus.PARTIAL_SUCCESS,
            image_metadata=decoded.metadata,
            lucidui=metric_result,
            llm_interpretation=self._build_disabled_llm_result(),
            uiclip=self._build_disabled_uiclip_result(),
            comparison=self._build_unavailable_comparison_result(metric_result),
            timings=timings,
            note=_NOTE,
        )

        self._repository.save(report)
        logger.info(
            "Created analysis %s (context=%s, status=%s, weightedScore=%s)",
            analysis_id,
            context_enum.value,
            report.status.value,
            metric_result.weighted_score,
        )
        return report

    def get_report(self, analysis_id: str) -> AnalysisReport:
        report = self._repository.get(analysis_id)
        if report is None:
            logger.info("Analysis not found: %s", analysis_id)
            raise AnalysisNotFoundError(analysis_id)
        logger.info("Retrieved analysis %s", analysis_id)
        return report

    def get_raw_report(self, analysis_id: str) -> AnalysisReport:
        # `lucidui.raw` inside the stored report already carries the
        # deterministic engine's full unfiltered output, so there is no
        # separate raw payload to return — see docs/api/report-schema.md.
        return self.get_report(analysis_id)

    @staticmethod
    def _validate_context(context: str) -> AnalysisContext:
        if context not in ALLOWED_CONTEXTS:
            raise InvalidContextError(context, ALLOWED_CONTEXTS)
        return AnalysisContext(context)

    @staticmethod
    def _build_disabled_llm_result() -> LLMInterpretationResult:
        return LLMInterpretationResult(
            status=LLMStatus.DISABLED,
            provider=None,
            summary=None,
            observations=[],
            recommendations=[],
            limitations=[],
        )

    @staticmethod
    def _build_disabled_uiclip_result() -> UIClipResult:
        return UIClipResult(
            enabled=False,
            status=UIClipStatus.DISABLED,
            model_version=None,
            description=None,
            description_source=None,
            quality_score=None,
            normalized_quality_score=None,
            observations=[],
            inference_time_ms=0,
        )

    @staticmethod
    def _build_unavailable_comparison_result(metric_result: DeterministicMetricResult) -> ComparisonResult:
        return ComparisonResult(
            lucidui_weighted_score=metric_result.weighted_score,
            uiclip_normalized_quality_score=None,
            absolute_score_difference=None,
            agreement_level=AgreementLevel.UNAVAILABLE,
            shared_findings=[],
            lucidui_only_findings=[],
            uiclip_only_findings=[],
            interpretation="UIClip evaluation was not run for this analysis, so no comparison could be computed.",
        )
