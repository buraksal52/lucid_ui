"""FastAPI dependency providers.

`get_repository` and the image-infra providers are cached so a single
instance of each is reused across requests within a process, per the Phase 1
requirement that the repository be shared rather than recreated per call —
the same reasoning applies to the (stateless but non-trivial to construct)
image validator/decoder/metric engine/LLM/UIClip providers.

As of Phase 2B-2, `get_metric_engine` is injected into `get_analysis_service`
so `POST /analyses/single` runs real deterministic metrics. As of Phase 3,
`get_llm_interpretation_service` is injected too. As of Phase 4,
`get_uiclip_evaluation_service` is injected too — see ROADMAP.md.
"""

from functools import lru_cache

from app.config import get_settings
from app.images.decoder import ImageDecoder
from app.images.metadata import ImageMetadataExtractor
from app.images.validator import ImageValidator
from app.llm.gemini_provider import GeminiLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.provider import LLMProvider
from app.llm.service import LLMInterpretationService
from app.metrics.engine import MetricEngine
from app.repositories.base import AnalysisRepository
from app.repositories.in_memory import InMemoryAnalysisRepository
from app.services.analysis_service import AnalysisService
from app.uiclip.mock_provider import MockUIClipProvider
from app.uiclip.provider import UIClipProvider
from app.uiclip.service import UIClipEvaluationService


@lru_cache
def get_repository() -> AnalysisRepository:
    return InMemoryAnalysisRepository()


@lru_cache
def get_image_metadata_extractor() -> ImageMetadataExtractor:
    return ImageMetadataExtractor()


@lru_cache
def get_image_decoder() -> ImageDecoder:
    return ImageDecoder(metadata_extractor=get_image_metadata_extractor())


@lru_cache
def get_image_validator() -> ImageValidator:
    settings = get_settings()
    return ImageValidator(max_size_bytes=settings.max_upload_size_bytes)


@lru_cache
def get_metric_engine() -> MetricEngine:
    return MetricEngine()


@lru_cache
def get_llm_provider() -> LLMProvider | None:
    """Selects the configured LLM provider.

    Defaults to the offline `MockLLMProvider` (no API key required). Only
    returns `GeminiLLMProvider` when `llm_provider == "gemini"` *and* an API
    key is actually configured; otherwise returns `None` so
    `LLMInterpretationService` reports `llmInterpretation.status =
    "unavailable"` instead of raising at startup.
    """
    settings = get_settings()
    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            return None
        return GeminiLLMProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            max_output_tokens=settings.llm_max_output_tokens,
        )
    return MockLLMProvider()


@lru_cache
def get_llm_interpretation_service() -> LLMInterpretationService:
    settings = get_settings()
    return LLMInterpretationService(provider=get_llm_provider(), provider_name=settings.llm_provider)


@lru_cache
def get_uiclip_provider() -> UIClipProvider | None:
    """Selects the configured UIClip provider.

    Only `"mock"` is implemented as of Phase 4 — no official/real UIClip
    model is loaded (see docs/research/uiclip-integration.md for why).
    Any other configured value gracefully returns `None` so
    `UIClipEvaluationService` reports `uiclip.status = "unavailable"`
    instead of raising, exactly like `get_llm_provider`.
    """
    settings = get_settings()
    if settings.uiclip_provider == "mock":
        return MockUIClipProvider()
    return None


@lru_cache
def get_uiclip_evaluation_service() -> UIClipEvaluationService:
    settings = get_settings()
    return UIClipEvaluationService(provider=get_uiclip_provider(), provider_name=settings.uiclip_provider)


def get_analysis_service() -> AnalysisService:
    return AnalysisService(
        repository=get_repository(),
        image_validator=get_image_validator(),
        image_decoder=get_image_decoder(),
        metric_engine=get_metric_engine(),
        llm_service=get_llm_interpretation_service(),
        uiclip_service=get_uiclip_evaluation_service(),
    )
