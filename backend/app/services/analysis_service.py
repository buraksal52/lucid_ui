"""Use-case coordinator for analyses.

Phase 1 builds a realistic, fully mocked report (no real image analysis, no
real LLM or UIClip calls — see ROADMAP.md Phase 2-5 for when those land).
Routes must only parse input and call this service; all report-construction
logic lives here, per CLAUDE.md ("Do not put business logic inside FastAPI
route functions").
"""

import uuid

from app.core.exceptions import AnalysisNotFoundError, InvalidContextError
from app.core.logging import get_logger
from app.repositories.base import AnalysisRepository
from app.schemas.analysis import (
    AnalysisReport,
    ImageMetadata,
    SingleAnalysisRequest,
    TimingResult,
)
from app.schemas.comparison import ComparisonResult
from app.schemas.common import (
    ALLOWED_CONTEXTS,
    AgreementLevel,
    AnalysisContext,
    AnalysisStatus,
    DescriptionSource,
    LLMStatus,
    UIClipStatus,
)
from app.schemas.llm import LLMInterpretationResult, LLMObservation
from app.schemas.metrics import LucidUIResult
from app.schemas.uiclip import UIClipResult

logger = get_logger("lucidui.analysis")

_MOCK_UICLIP_MODEL_VERSION = "mock-uiclip-v0"
_MOCK_GENERIC_DESCRIPTION = "A software user interface screenshot."


class AnalysisService:
    """Coordinates single-analysis creation and retrieval."""

    def __init__(self, repository: AnalysisRepository) -> None:
        self._repository = repository

    def create_single_analysis(self, request: SingleAnalysisRequest) -> AnalysisReport:
        context = self._validate_context(request.context)

        analysis_id = str(uuid.uuid4())

        lucidui_result = self._build_mock_lucidui_result()
        llm_result = self._build_mock_llm_result(run_llm=request.run_llm, lucidui_result=lucidui_result)
        uiclip_result = self._build_mock_uiclip_result(
            run_uiclip=request.run_uiclip, description=request.description
        )
        comparison_result = self._build_mock_comparison_result(
            lucidui_result=lucidui_result, uiclip_result=uiclip_result
        )
        timings = self._build_mock_timings(llm_result=llm_result, uiclip_result=uiclip_result)

        status = self._determine_status(llm_result=llm_result, uiclip_result=uiclip_result)

        report = AnalysisReport(
            analysis_id=analysis_id,
            context=context,
            status=status,
            image_metadata=self._build_mock_image_metadata(),
            lucidui=lucidui_result,
            llm_interpretation=llm_result,
            uiclip=uiclip_result,
            comparison=comparison_result,
            timings=timings,
            note="These results are design signals for review, not objective verdicts.",
        )

        self._repository.save(report)
        logger.info("Created analysis %s (context=%s, status=%s)", analysis_id, context.value, status.value)
        return report

    def get_report(self, analysis_id: str) -> AnalysisReport:
        report = self._repository.get(analysis_id)
        if report is None:
            logger.info("Analysis not found: %s", analysis_id)
            raise AnalysisNotFoundError(analysis_id)
        logger.info("Retrieved analysis %s", analysis_id)
        return report

    def get_raw_report(self, analysis_id: str) -> AnalysisReport:
        # Phase 1 has no separate "raw" model underlying the report — the
        # stored report already contains every mocked field, so /raw returns
        # the same object. A distinct raw payload lands with the real metric
        # engine in Phase 2.
        return self.get_report(analysis_id)

    @staticmethod
    def _validate_context(context: str) -> AnalysisContext:
        if context not in ALLOWED_CONTEXTS:
            raise InvalidContextError(context, ALLOWED_CONTEXTS)
        return AnalysisContext(context)

    @staticmethod
    def _build_mock_image_metadata() -> ImageMetadata:
        return ImageMetadata(width=1440, height=900, format="mock", size_bytes=0)

    @staticmethod
    def _build_mock_lucidui_result() -> LucidUIResult:
        raw = {
            "contrast": {
                "value": "4.1:1",
                "unit": "ratio",
                "threshold": "4.5:1",
                "thresholdSource": "WCAG 2.1 AA",
                "aboveThreshold": False,
                "proxyStatus": "partial_proxy",
            },
            "edgeDensity": {
                "value": 0.21,
                "unit": "ratio",
                "proxyStatus": "proxy",
            },
            "detectedElementCount": {
                "value": 47,
                "unit": "count",
                "proxyStatus": "proxy",
            },
            "textDensity": {
                "value": 0.14,
                "unit": "ratio",
                "wordsDetected": 132,
                "proxyStatus": "proxy",
            },
            "whitespaceRatio": {
                "value": 0.38,
                "unit": "ratio",
                "proxyStatus": "proxy",
            },
            "colorfulness": {
                "value": 42.7,
                "unit": "hasler_susstrunk_score",
                "proxyStatus": "direct_computation",
            },
        }
        normalized = {
            "contrast": 0.78,
            "edgeDensity": 0.55,
            "detectedElementCount": 0.62,
            "textDensity": 0.48,
            "whitespaceRatio": 0.60,
            "colorfulness": 0.51,
        }
        additional_signals = {
            "hicksLawEstimateNormalized": 0.58,
            "fittsLawIndexOfDifficultyNormalized": 0.53,
            "estimatedGroupCountNormalized": 0.64,
        }
        return LucidUIResult(
            raw=raw,
            normalized=normalized,
            additional_signals=additional_signals,
            weighted_score=0.63,
        )

    @staticmethod
    def _build_mock_llm_result(run_llm: bool, lucidui_result: LucidUIResult) -> LLMInterpretationResult:
        if not run_llm:
            return LLMInterpretationResult(
                status=LLMStatus.DISABLED,
                provider=None,
                summary=None,
                observations=[],
                recommendations=[],
                limitations=[],
            )

        return LLMInterpretationResult(
            status=LLMStatus.COMPLETED,
            provider="mock",
            summary=(
                "Sampled contrast is below the WCAG 2.1 AA reference threshold, and edge "
                "density is moderately high relative to comparable screens, suggesting a "
                "potential review area around visual density."
            ),
            observations=[
                LLMObservation(
                    id="obs-1",
                    text=(
                        "Sampled contrast (4.1:1) is below the WCAG 2.1 AA reference "
                        "threshold (4.5:1) in at least one detected text region."
                    ),
                    metric_evidence=["lucidui.raw.contrast"],
                    category="review_area",
                ),
                LLMObservation(
                    id="obs-2",
                    text=(
                        "Detected element count (47) and edge density (0.21) are both "
                        "moderately high relative to typical dashboard screenshots analyzed so far."
                    ),
                    metric_evidence=["lucidui.raw.detectedElementCount", "lucidui.raw.edgeDensity"],
                    category="observation",
                ),
            ],
            recommendations=[
                "The contrast region flagged below the reference threshold may be worth a closer look.",
            ],
            limitations=[
                "Contrast is estimated from sampled foreground/background colors, not exact glyph-level analysis.",
                "This interpretation is derived only from LucidUI's deterministic metric JSON, not the raw image.",
            ],
        )

    @staticmethod
    def _build_mock_uiclip_result(run_uiclip: bool, description: str | None) -> UIClipResult:
        if not run_uiclip:
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

        if description:
            description_source = DescriptionSource.USER
            resolved_description = description
        else:
            description_source = DescriptionSource.GENERIC
            resolved_description = _MOCK_GENERIC_DESCRIPTION

        return UIClipResult(
            enabled=True,
            status=UIClipStatus.COMPLETED,
            model_version=_MOCK_UICLIP_MODEL_VERSION,
            description=resolved_description,
            description_source=description_source,
            quality_score=72.0,
            normalized_quality_score=0.72,
            observations=[
                "Detected a structured interface with multiple distinct content sections.",
            ],
            inference_time_ms=400,
        )

    @staticmethod
    def _build_mock_comparison_result(
        lucidui_result: LucidUIResult, uiclip_result: UIClipResult
    ) -> ComparisonResult:
        if not uiclip_result.enabled or uiclip_result.normalized_quality_score is None:
            return ComparisonResult(
                lucidui_weighted_score=lucidui_result.weighted_score,
                uiclip_normalized_quality_score=None,
                absolute_score_difference=None,
                agreement_level=AgreementLevel.UNAVAILABLE,
                shared_findings=[],
                lucidui_only_findings=[],
                uiclip_only_findings=[],
                interpretation="UIClip evaluation was not run for this analysis, so no comparison could be computed.",
            )

        difference = round(abs(lucidui_result.weighted_score - uiclip_result.normalized_quality_score), 4)
        if difference < 0.1:
            agreement_level = AgreementLevel.HIGH
        elif difference < 0.25:
            agreement_level = AgreementLevel.PARTIAL
        else:
            agreement_level = AgreementLevel.LOW

        return ComparisonResult(
            lucidui_weighted_score=lucidui_result.weighted_score,
            uiclip_normalized_quality_score=uiclip_result.normalized_quality_score,
            absolute_score_difference=difference,
            agreement_level=agreement_level,
            shared_findings=[
                "Both LucidUI and UIClip signals indicate moderate-to-high visual density in this screenshot.",
            ],
            lucidui_only_findings=[
                "Contrast below the WCAG 2.1 AA reference threshold was only surfaced by the deterministic contrast metric.",
            ],
            uiclip_only_findings=[
                "UIClip's preference score reflects a learned, holistic impression not tied to a specific measurable factor.",
            ],
            interpretation=(
                "LucidUI's composite signal score and UIClip's preference score are a "
                f"{agreement_level.value} agreement for this screenshot."
            ),
        )

    @staticmethod
    def _build_mock_timings(
        llm_result: LLMInterpretationResult, uiclip_result: UIClipResult
    ) -> TimingResult:
        lucidui_ms = 180
        llm_ms = 520 if llm_result.status == LLMStatus.COMPLETED else 0
        uiclip_ms = uiclip_result.inference_time_ms
        comparison_ms = 5 if uiclip_result.enabled else 0
        base_overhead_ms = 15
        total_ms = base_overhead_ms + lucidui_ms + llm_ms + uiclip_ms + comparison_ms
        return TimingResult(
            total_ms=total_ms,
            lucidui_ms=lucidui_ms,
            llm_ms=llm_ms,
            uiclip_ms=uiclip_ms,
            comparison_ms=comparison_ms,
        )

    @staticmethod
    def _determine_status(
        llm_result: LLMInterpretationResult, uiclip_result: UIClipResult
    ) -> AnalysisStatus:
        if llm_result.status == LLMStatus.COMPLETED and uiclip_result.status == UIClipStatus.COMPLETED:
            return AnalysisStatus.COMPLETED
        return AnalysisStatus.PARTIAL_SUCCESS
