# Non-Goals

These are explicit boundaries for the first versions of LucidUI. They may be revisited later, but only through a deliberate scope decision, not an incremental feature creep. See [product-scope.md](product-scope.md) and the "Flashlight, Not a Judge" principle in [CLAUDE.md](../../CLAUDE.md).

The first versions of LucidUI will **not**:

- Replace professional designers or design review processes.
- Declare objective design quality — no verdicts of "good," "bad," "correct," or "beautiful."
- Edit UI source code.
- Generate production-ready frontend code.
- Inspect DOM or CSS — all analysis is screenshot/pixel-based only.
- Identify all accessibility violations — contrast-related signals are a partial proxy, not an accessibility audit (see [docs/metrics/known-limitations.md](../metrics/known-limitations.md)).
- Support Figma plugins or other design-tool integrations.
- Train a new foundation model — UIClip is used as an existing, independent evaluator, not trained from scratch.
- Produce academic-grade correlation statistics from a single screenshot — correlation and significance claims require dataset-level evaluation (see [docs/research/evaluation-plan.md](../research/evaluation-plan.md)).
- Store raw screenshots by default (see [docs/architecture/privacy-model.md](../architecture/privacy-model.md)).
