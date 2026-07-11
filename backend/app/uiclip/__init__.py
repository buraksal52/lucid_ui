"""UIClip evaluation layer.

Turns a decoded screenshot plus an optional natural-language description
into the public `app.schemas.uiclip.UIClipResult`. UIClip is an
**independent learned evaluator** — never ground truth, never a judge of
LucidUI's deterministic metrics — see ADR-004
(docs/architecture/decisions/ADR-004-uiclip-independent-evaluator.md).

Only the mock evaluator (`MockUIClipProvider`) is implemented as of Phase 4.
No official/real UIClip model is loaded — see docs/research/uiclip-integration.md
for the verified findings on official model availability and why real
integration is deferred to Phase 5.

This module must remain independent of `app.llm` and `app.metrics`: it never
imports `DeterministicMetricResult`, Gemini output, or LLM-generated text,
per CLAUDE.md's module independence rule.
"""
