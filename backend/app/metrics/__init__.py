"""Deterministic metric engine adapter.

Wraps the validated legacy metric functions in
`backend/reference/legacy_metric_engine.py` (immutable scientific logic —
see CLAUDE.md) so they can run against an in-memory decoded image instead of
a file path. This package does not yet connect to the FastAPI analysis
endpoint — see ROADMAP.md Phase 2B.
"""
