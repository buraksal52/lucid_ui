"""In-memory implementation of AnalysisRepository.

Backs `/api/v1/analyses/*` for Phase 1-8; does not persist across process
restarts. Durable persistence is Phase 9 — see ROADMAP.md and
docs/api/api-contract.md's notes section. Not process-safe across multiple
workers; fine for single-process development use.
"""

from app.repositories.base import AnalysisRepository
from app.schemas.analysis import AnalysisReport


class InMemoryAnalysisRepository(AnalysisRepository):
    def __init__(self) -> None:
        self._reports: dict[str, AnalysisReport] = {}

    def save(self, report: AnalysisReport) -> None:
        self._reports[report.analysis_id] = report

    def get(self, analysis_id: str) -> AnalysisReport | None:
        return self._reports.get(analysis_id)
