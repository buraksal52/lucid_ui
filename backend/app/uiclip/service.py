"""UIClip evaluation service.

Turns a `DecodedImage` plus an optional submitted description into the
public `UIClipResult` (app.schemas.uiclip) by resolving the description
source, calling the configured `UIClipProvider`, and validating the
structured response against `UIClipProviderOutput` before mapping it onto
the public schema.

Every failure mode degrades gracefully to a documented `UIClipStatus`
instead of raising — a UIClip failure must never discard the deterministic
analysis or the LLM interpretation, and must never fail the whole request.
Provider internals are logged server-side only; the client only ever sees
the public `UIClipResult` shape. Mirrors `app.llm.service.LLMInterpretationService`.

Deliberately receives only `DecodedImage` and a description string — never
`DeterministicMetricResult`, Gemini/LLM output, or comparison results, per
ADR-004 (UIClip is an independent evaluator).

Providers may opt in to requiring a genuine user-submitted description (see
`requires_description` on `HuggingFaceUIClipProvider`) — for such a
provider, if only the generic screenshot-placeholder description would be
used, this service returns `unavailable` without ever calling the provider,
rather than evaluating a real model against a non-description. This is a
duck-typed, optional attribute (defaults to `False` via `getattr`), not a
change to the `UIClipProvider` Protocol itself.
"""

import logging
import time

from pydantic import ValidationError

from app.images.models import DecodedImage
from app.schemas.common import DescriptionSource, UIClipStatus
from app.schemas.uiclip import UIClipResult
from app.uiclip.exceptions import UIClipEvaluationError, UIClipProviderUnavailableError
from app.uiclip.models import UIClipProviderOutput
from app.uiclip.provider import UIClipProvider

logger = logging.getLogger("lucidui.uiclip")

_GENERIC_DESCRIPTION = "A software user interface screenshot."


class UIClipEvaluationService:
    """Coordinates description resolution, provider invocation, and response
    validation for a single decoded image."""

    def __init__(self, provider: UIClipProvider | None, provider_name: str) -> None:
        self._provider = provider
        self._provider_name = provider_name

    def evaluate(self, image: DecodedImage, description: str | None) -> UIClipResult:
        resolved_description, description_source = self._resolve_description(description)

        if self._provider is None:
            logger.info(
                "UIClip evaluation unavailable: no provider configured (uiclip_provider=%s)", self._provider_name
            )
            return self._unavailable_result(resolved_description, description_source)

        if getattr(self._provider, "requires_description", False) and description_source == DescriptionSource.GENERIC:
            logger.info(
                "UIClip provider %s requires a real user-submitted description; none was provided",
                self._provider_name,
            )
            return self._unavailable_result(resolved_description, description_source)

        inference_start = time.monotonic()
        try:
            raw_output = self._provider.evaluate(image.pil_image, resolved_description)
        except UIClipProviderUnavailableError as exc:
            logger.warning("UIClip provider %s unavailable: %s", self._provider_name, exc.message)
            return self._unavailable_result(resolved_description, description_source)
        except UIClipEvaluationError as exc:
            logger.warning("UIClip provider %s output unusable: %s", self._provider_name, exc.message)
            return self._failed_result(resolved_description, description_source)
        except Exception:
            logger.exception("Unexpected error calling UIClip provider %s", self._provider_name)
            return self._failed_result(resolved_description, description_source)
        inference_time_ms = round((time.monotonic() - inference_start) * 1000)

        try:
            validated = self._validate(raw_output)
        except UIClipEvaluationError as exc:
            logger.warning("UIClip provider %s output failed validation: %s", self._provider_name, exc.message)
            return self._failed_result(resolved_description, description_source)

        return UIClipResult(
            enabled=True,
            status=UIClipStatus.COMPLETED,
            model_version=validated.model_version,
            description=resolved_description,
            description_source=description_source,
            # No documented, verified 0-100/0-1 normalization exists for the
            # official model's raw dot-product score (see app.uiclip.models
            # and docs/research/uiclip-integration.md) — left null rather
            # than invented, per CLAUDE.md.
            quality_score=validated.raw_score,
            normalized_quality_score=None,
            observations=validated.observations,
            inference_time_ms=inference_time_ms,
        )

    @staticmethod
    def _resolve_description(description: str | None) -> tuple[str, DescriptionSource]:
        """`user` if a non-blank description was submitted, else the
        already-documented `generic` fallback (report-schema.md Description
        Sources) — never a silently invented one-off string."""
        if description and description.strip():
            return description.strip(), DescriptionSource.USER
        return _GENERIC_DESCRIPTION, DescriptionSource.GENERIC

    @staticmethod
    def _validate(raw_output: dict) -> UIClipProviderOutput:
        try:
            return UIClipProviderOutput.model_validate(raw_output)
        except ValidationError as exc:
            raise UIClipEvaluationError("The UIClip provider output did not match the expected structure.") from exc

    @staticmethod
    def _unavailable_result(description: str, description_source: DescriptionSource) -> UIClipResult:
        return UIClipResult(
            enabled=True,
            status=UIClipStatus.UNAVAILABLE,
            model_version=None,
            description=description,
            description_source=description_source,
            quality_score=None,
            normalized_quality_score=None,
            observations=[],
            inference_time_ms=0,
        )

    @staticmethod
    def _failed_result(description: str, description_source: DescriptionSource) -> UIClipResult:
        return UIClipResult(
            enabled=True,
            status=UIClipStatus.FAILED,
            model_version=None,
            description=description,
            description_source=description_source,
            quality_score=None,
            normalized_quality_score=None,
            observations=[],
            inference_time_ms=0,
        )
