"""FastAPI dependency providers.

`get_repository` and the image-infra providers are cached so a single
instance of each is reused across requests within a process, per the Phase 1
requirement that the repository be shared rather than recreated per call —
the same reasoning applies to the (stateless but non-trivial to construct)
image validator/decoder.
"""

from functools import lru_cache

from app.config import get_settings
from app.images.decoder import ImageDecoder
from app.images.metadata import ImageMetadataExtractor
from app.images.validator import ImageValidator
from app.repositories.base import AnalysisRepository
from app.repositories.in_memory import InMemoryAnalysisRepository
from app.services.analysis_service import AnalysisService


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


def get_analysis_service() -> AnalysisService:
    return AnalysisService(
        repository=get_repository(),
        image_validator=get_image_validator(),
        image_decoder=get_image_decoder(),
    )
