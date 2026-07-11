"""Use-case coordinator for analyses.

Phase 2A: validates and decodes an uploaded image and returns a temporary
"accepted" response — no metric, LLM, or UIClip stage runs yet (those land in
Phase 2B+, see ROADMAP.md). Routes must only parse input and call this
service; all image-handling logic lives here, per CLAUDE.md ("Do not put
business logic inside FastAPI route functions").
"""

import uuid

from app.core.exceptions import AnalysisNotFoundError, InvalidContextError
from app.core.logging import get_logger
from app.images.decoder import ImageDecoder
from app.images.validator import ImageValidator
from app.repositories.base import AnalysisRepository
from app.schemas.analysis import AnalysisAcceptedResponse, AnalysisReport
from app.schemas.common import ALLOWED_CONTEXTS, AnalysisContext

logger = get_logger("lucidui.analysis")


class AnalysisService:
    """Coordinates single-analysis image acceptance and report retrieval."""

    def __init__(
        self,
        repository: AnalysisRepository,
        image_validator: ImageValidator,
        image_decoder: ImageDecoder,
    ) -> None:
        self._repository = repository
        self._image_validator = image_validator
        self._image_decoder = image_decoder

    def accept_single_analysis_image(
        self,
        data: bytes,
        content_type: str | None,
        context: str,
    ) -> AnalysisAcceptedResponse:
        self._validate_context(context)

        self._image_validator.validate(content_type, data)
        decoded = self._image_decoder.decode(data, content_type)

        analysis_id = str(uuid.uuid4())
        logger.info(
            "Accepted analysis image %s (format=%s, width=%s, height=%s, sizeBytes=%s)",
            analysis_id,
            decoded.metadata.format,
            decoded.metadata.width,
            decoded.metadata.height,
            decoded.metadata.file_size_bytes,
        )
        return AnalysisAcceptedResponse(analysis_id=analysis_id, image_metadata=decoded.metadata)

    def get_report(self, analysis_id: str) -> AnalysisReport:
        report = self._repository.get(analysis_id)
        if report is None:
            logger.info("Analysis not found: %s", analysis_id)
            raise AnalysisNotFoundError(analysis_id)
        logger.info("Retrieved analysis %s", analysis_id)
        return report

    def get_raw_report(self, analysis_id: str) -> AnalysisReport:
        # No separate "raw" model underlying the report yet — the real
        # deterministic pipeline (and a distinct raw payload) lands in
        # Phase 2B.
        return self.get_report(analysis_id)

    @staticmethod
    def _validate_context(context: str) -> AnalysisContext:
        if context not in ALLOWED_CONTEXTS:
            raise InvalidContextError(context, ALLOWED_CONTEXTS)
        return AnalysisContext(context)
