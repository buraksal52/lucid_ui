"""FastAPI dependency providers.

`get_repository` is cached so a single `InMemoryAnalysisRepository` instance
is reused across requests within a process, per the Phase 1 requirement that
the repository be shared rather than recreated per call.
"""

from functools import lru_cache

from app.repositories.base import AnalysisRepository
from app.repositories.in_memory import InMemoryAnalysisRepository
from app.services.analysis_service import AnalysisService


@lru_cache
def get_repository() -> AnalysisRepository:
    return InMemoryAnalysisRepository()


def get_analysis_service() -> AnalysisService:
    return AnalysisService(repository=get_repository())
