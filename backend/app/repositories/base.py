"""Abstract repository interface for analysis reports.

The service layer depends on this interface, not on any concrete storage
implementation, so a future persistence adapter (PostgreSQL/Supabase, Phase 9)
can replace `InMemoryAnalysisRepository` without changing service or route
code — see ARCHITECTURE.md's Domain Interfaces / Adapters split.
"""

from typing import Protocol

from app.schemas.analysis import AnalysisReport


class AnalysisRepository(Protocol):
    """Storage contract for analysis reports."""

    def save(self, report: AnalysisReport) -> None:
        """Persist a report, keyed by its `analysis_id`."""
        ...

    def get(self, analysis_id: str) -> AnalysisReport | None:
        """Return the stored report for `analysis_id`, or None if absent."""
        ...
