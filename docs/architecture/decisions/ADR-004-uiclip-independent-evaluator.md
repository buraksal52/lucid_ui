# ADR-004: UIClip Is an Independent Evaluator, Not Ground Truth

## Status

Accepted

## Context

UIClip is a learned vision-language model that produces a global UI preference/quality signal. It would be possible to treat UIClip's output as the "correct" answer against which LucidUI's deterministic metrics are graded, or to treat the two systems as independent, comparably-fallible evaluators.

## Decision

UIClip and the LucidUI deterministic metric engine are treated as two independent evaluators. Neither is treated as ground truth for the other. The Comparison Engine reports agreements and discrepancies between them — it does not resolve disagreements in favor of either system.

## Rationale

- UIClip is itself a learned model with training-data dependence and failure modes (see [docs/metrics/known-limitations.md](../../metrics/known-limitations.md)); treating it as ground truth would contradict the "Flashlight, Not a Judge" principle just as much as treating LucidUI's metrics that way would.
- LucidUI's value is in explainable, metric-level signals; UIClip's value is in a holistic, learned signal. Collapsing them into one score would destroy the explainability that motivates LucidUI's design.
- Presenting both, with their agreements and differences, gives users more useful information than forcing a single verdict.

## Consequences

- The Comparison Engine's output schema has `sharedFindings`, `luciduiOnlyFindings`, and `uiclipOnlyFindings` — there is no "final corrected score."
- Documentation and frontend copy must never say things like "UIClip says this is better" as a verdict; see language guidelines in [docs/frontend/FRONTEND_GUIDE.md](../../frontend/FRONTEND_GUIDE.md).
- Research questions about which system correlates better with human ratings (see [docs/research/research-questions.md](../../research/research-questions.md)) are answered empirically, at the dataset level — not assumed in advance by the architecture.
