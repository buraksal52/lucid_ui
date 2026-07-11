"""Use-case coordinator for analyses.

Validates and decodes an uploaded image, runs the deterministic
`MetricEngine` against it exactly once, interprets that result with
`LLMInterpretationService`, evaluates the decoded image independently with
`UIClipEvaluationService`, assembles a full `AnalysisReport`, and persists
it. Comparison between LucidUI and UIClip is not implemented yet (Phase 6+),
so `comparison` still uses the project's existing `unavailable` status
design rather than fabricated data — see docs/api/report-schema.md. Routes
must only parse input and call this service; all orchestration logic lives
here, per CLAUDE.md ("Do not put business logic inside FastAPI route
functions"). Prompt construction/LLM-provider calls live in `app.llm`;
UIClip provider calls live in `app.uiclip` — never here, and neither module
receives the other's output (LLM never sees UIClip output or the image;
UIClip never sees deterministic metrics or LLM output) — see ADR-003/ADR-004.
"""

import time
import uuid

from app.core.exceptions import AnalysisNotFoundError, InvalidContextError
from app.core.logging import get_logger
from app.images.decoder import ImageDecoder
from app.images.validator import ImageValidator
from app.llm.service import LLMInterpretationService
from app.metrics.engine import MetricEngine
from app.metrics.models import DeterministicMetricResult
from app.repositories.base import AnalysisRepository
from app.schemas.analysis import AnalysisReport, TimingResult
from app.schemas.comparison import ComparisonResult
from app.schemas.common import (
    ALLOWED_CONTEXTS,
    AgreementLevel,
    AnalysisContext,
    AnalysisStatus,
    LLMStatus,
    UIClipStatus,
)
from app.schemas.llm import LLMInterpretationResult
from app.schemas.uiclip import UIClipResult
from app.uiclip.service import UIClipEvaluationService

logger = get_logger("lucidui.analysis")

_NOTE = (
    "These results are design signals for review, not objective verdicts. "
    "UIClip evaluation currently uses an offline mock evaluator — no official/real "
    "UIClip model is integrated yet (see ROADMAP.md Phase 5). Comparison between "
    "LucidUI and UIClip has not been computed (see ROADMAP.md Phase 6)."
)


class AnalysisService:
    """Coordinates single-analysis creation (validate -> decode -> metrics ->
    LLM interpretation -> UIClip evaluation -> persist) and report retrieval."""

    def __init__(
        self,
        repository: AnalysisRepository,
        image_validator: ImageValidator,
        image_decoder: ImageDecoder,
        metric_engine: MetricEngine,
        llm_service: LLMInterpretationService,
        uiclip_service: UIClipEvaluationService,
    ) -> None:
        self._repository = repository
        self._image_validator = image_validator
        self._image_decoder = image_decoder
        self._metric_engine = metric_engine
        self._llm_service = llm_service
        self._uiclip_service = uiclip_service

    def create_single_analysis(
        self,
        data: bytes,
        content_type: str | None,
        context: str,
        run_llm: bool = True,
        run_uiclip: bool = True,
        description: str | None = None,
    ) -> AnalysisReport:
        context_enum = self._validate_context(context)
        start = time.monotonic()

        self._image_validator.validate(content_type, data)
        decoded = self._image_decoder.decode(data, content_type)

        metrics_start = time.monotonic()
        metric_result = self._metric_engine.analyze(decoded, context_enum)
        lucidui_ms = round((time.monotonic() - metrics_start) * 1000)

        if run_llm:
            llm_start = time.monotonic()
            llm_result = self._llm_service.interpret(metric_result, context_enum)
            llm_ms = round((time.monotonic() - llm_start) * 1000)
        else:
            llm_result = self._build_disabled_llm_result()
            llm_ms = 0

        if run_uiclip:
            uiclip_start = time.monotonic()
            uiclip_result = self._uiclip_service.evaluate(decoded, description)
            uiclip_ms = round((time.monotonic() - uiclip_start) * 1000)
        else:
            uiclip_result = self._build_disabled_uiclip_result()
            uiclip_ms = 0

        analysis_id = str(uuid.uuid4())
        timings = TimingResult(
            total_ms=round((time.monotonic() - start) * 1000),
            lucidui_ms=lucidui_ms,
            llm_ms=llm_ms,
            uiclip_ms=uiclip_ms,
            comparison_ms=0,
        )

        report = AnalysisReport(
            analysis_id=analysis_id,
            context=context_enum,
            status=self._compute_status(llm_result, uiclip_result),
            image_metadata=decoded.metadata,
            lucidui=metric_result,
            llm_interpretation=llm_result,
            uiclip=uiclip_result,
            comparison=self._build_unavailable_comparison_result(metric_result, uiclip_result),
            timings=timings,
            note=_NOTE,
        )

        self._repository.save(report)
        logger.info(
            "Created analysis %s (context=%s, status=%s, weightedScore=%s, llmStatus=%s, uiclipStatus=%s)",
            analysis_id,
            context_enum.value,
            report.status.value,
            metric_result.weighted_score,
            llm_result.status.value,
            uiclip_result.status.value,
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
    def _compute_status(llm_result: LLMInterpretationResult, uiclip_result: UIClipResult) -> AnalysisStatus:
        """Per report-schema.md: `completed` requires every requested optional
        stage (LLM, UIClip) to have actually completed; disabled, unavailable,
        fallback, and failed all count as "did not complete" — so a request
        that intentionally disables a stage is `partial_success`, same as one
        where a stage errored. Comparison is not part of this decision — it
        is not in the documented status semantics and is not implemented yet."""
        if llm_result.status == LLMStatus.COMPLETED and uiclip_result.status == UIClipStatus.COMPLETED:
            return AnalysisStatus.COMPLETED
        return AnalysisStatus.PARTIAL_SUCCESS

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
    def _build_unavailable_comparison_result(
        metric_result: DeterministicMetricResult, uiclip_result: UIClipResult
    ) -> ComparisonResult:
        # Not comparison logic: each system's own already-computed score is
        # carried through for reference, same as lucidui_weighted_score
        # always was. No agreement/difference is calculated — that is
        # explicitly Phase 6 (see ROADMAP.md).
        return ComparisonResult(
            lucidui_weighted_score=metric_result.weighted_score,
            uiclip_normalized_quality_score=uiclip_result.normalized_quality_score,
            absolute_score_difference=None,
            agreement_level=AgreementLevel.UNAVAILABLE,
            shared_findings=[],
            lucidui_only_findings=[],
            uiclip_only_findings=[],
            interpretation="Comparison between LucidUI and UIClip has not been implemented yet (see ROADMAP.md Phase 6).",
        )
