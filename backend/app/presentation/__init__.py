"""Presentation Report layer.

Formats already-computed `DeterministicMetricResult` / `LLMInterpretationResult`
/ `UIClipResult` output into the ready-to-render `PresentationReport` schema
(`app.schemas.presentation`). Pure and side-effect free: never calls a
provider, never re-runs the metric engine, never depends on FastAPI or a
repository — see `app.presentation.report_builder`.
"""
