"""LLM interpretation service.

Turns a validated `DeterministicMetricResult` into a public
`LLMInterpretationResult` by building a JSON-only prompt (app.llm.prompt),
calling the configured `LLMProvider`, and validating the structured response
against `LLMStructuredOutput` before mapping it onto the public schema.

Every failure mode degrades gracefully to a documented `LLMStatus` instead of
raising — per CLAUDE.md and the report-schema.md status catalog, an LLM
failure must never discard the deterministic analysis or fail the whole
request. Provider/parsing internals are logged server-side only; the client
only ever sees the public `LLMInterpretationResult` shape.
"""

import logging

from pydantic import ValidationError

from app.llm.exceptions import LLMInterpretationError, LLMProviderUnavailableError
from app.llm.interpretation_guard import filter_observations, filter_recommendations, filter_summary
from app.llm.models import LLMStructuredOutput
from app.llm.prompt import build_prompt
from app.llm.provider import LLMProvider
from app.metrics.models import DeterministicMetricResult
from app.schemas.common import AnalysisContext, LLMStatus
from app.schemas.llm import LLMInterpretationResult, LLMObservation

logger = logging.getLogger("lucidui.llm")

_FILTERED_CONTENT_NOTICE = (
    "One or more generated statements were removed for exceeding this system's descriptive-metric "
    "interpretation rules — see docs/metrics/interpretation-taxonomy.md."
)


class LLMInterpretationService:
    """Coordinates prompt construction, provider invocation, and response
    validation for a single deterministic metric result."""

    def __init__(self, provider: LLMProvider | None, provider_name: str) -> None:
        self._provider = provider
        self._provider_name = provider_name

    def interpret(
        self,
        metric_result: DeterministicMetricResult,
        context: AnalysisContext,
    ) -> LLMInterpretationResult:
        if self._provider is None:
            logger.info("LLM interpretation unavailable: no provider configured (llm_provider=%s)", self._provider_name)
            return self._unavailable_result()

        system_prompt, user_prompt = build_prompt(metric_result, context)

        try:
            raw_response = self._provider.complete(system_prompt, user_prompt)
        except LLMProviderUnavailableError as exc:
            logger.warning("LLM provider %s unavailable: %s", self._provider_name, exc.message)
            return self._unavailable_result()
        except LLMInterpretationError as exc:
            logger.warning("LLM provider %s response unusable: %s", self._provider_name, exc.message)
            return self._failed_result()
        except Exception:
            logger.exception("Unexpected error calling LLM provider %s", self._provider_name)
            return self._failed_result()

        try:
            structured = self._validate_response(raw_response)
        except LLMInterpretationError as exc:
            logger.warning("LLM provider %s response failed validation: %s", self._provider_name, exc.message)
            return self._failed_result()

        # Deterministic content guard (app.llm.interpretation_guard): the
        # prompt is advisory only and a real provider has been observed to
        # ignore it (e.g. turning estimatedGroupCount into a cognitive-load
        # claim, or colorfulness/hue diversity into an "increase this"
        # recommendation) — this is the actual enforced backstop, applied
        # regardless of provider compliance. Drops, never rewrites, any
        # unsupported statement; a justified, unrelated recommendation
        # (e.g. a confirmed below-AA-threshold contrast finding) is
        # untouched since it shares no vocabulary with the forbidden
        # combinations.
        filtered_summary, summary_dropped = filter_summary(structured.summary)
        filtered_recommendations, recommendations_dropped = filter_recommendations(structured.recommendations)
        filtered_observations, observations_dropped = filter_observations(structured.observations)
        any_dropped = summary_dropped or recommendations_dropped or observations_dropped

        limitations = list(structured.limitations)
        if any_dropped:
            logger.info(
                "Interpretation guard filtered unsupported content from provider %s "
                "(summary=%s, recommendations=%s, observations=%s)",
                self._provider_name,
                summary_dropped,
                recommendations_dropped,
                observations_dropped,
            )
            limitations.append(_FILTERED_CONTENT_NOTICE)

        return LLMInterpretationResult(
            status=LLMStatus.COMPLETED,
            provider=self._provider_name,
            summary=filtered_summary,
            observations=[
                LLMObservation(
                    id=observation.id,
                    text=observation.text,
                    metric_evidence=observation.metric_evidence,
                    category=observation.category,
                )
                for observation in filtered_observations
            ],
            recommendations=filtered_recommendations,
            limitations=limitations,
        )

    @staticmethod
    def _validate_response(raw_response: dict) -> LLMStructuredOutput:
        try:
            structured = LLMStructuredOutput.model_validate(raw_response)
        except ValidationError as exc:
            raise LLMInterpretationError("The LLM response did not match the expected structure.") from exc

        for observation in structured.observations:
            if not observation.metric_evidence:
                raise LLMInterpretationError(
                    f"Observation '{observation.id}' has no metric evidence; every observation must "
                    "reference at least one deterministic metric."
                )

        return structured

    @staticmethod
    def _unavailable_result() -> LLMInterpretationResult:
        return LLMInterpretationResult(
            status=LLMStatus.UNAVAILABLE,
            provider=None,
            summary=None,
            observations=[],
            recommendations=[],
            limitations=[],
        )

    @staticmethod
    def _failed_result() -> LLMInterpretationResult:
        return LLMInterpretationResult(
            status=LLMStatus.FAILED,
            provider=None,
            summary=None,
            observations=[],
            recommendations=[],
            limitations=[],
        )
