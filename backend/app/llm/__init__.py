"""LLM interpretation layer.

Turns `app.metrics.models.DeterministicMetricResult` (deterministic metric
JSON) into the public `app.schemas.llm.LLMInterpretationResult` (summary,
observations, recommendations, limitations). The LLM is an interpreter
only — it never computes metrics, never invents evidence, and never
receives the uploaded image, raw bytes, or a screenshot in any form; only
already-JSON-safe deterministic metric output and the analysis context.
See docs/architecture/decisions/ADR-003-json-only-llm-input.md.

This module must remain independent of app.metrics and app.uiclip beyond
importing the `DeterministicMetricResult` *type* it interprets — it never
imports OCR, OpenCV, or image-decoding code, per CLAUDE.md's module
independence rule.
"""
