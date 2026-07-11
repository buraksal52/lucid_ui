# UIClip Integration

This document explains the plan for integrating UIClip as LucidUI's independent learned evaluator. See [ADR-004](../architecture/decisions/ADR-004-uiclip-independent-evaluator.md) and [ADR-005](../architecture/decisions/ADR-005-mock-providers-before-real-integrations.md) for the underlying architectural decisions.

## Why UIClip Is Being Integrated

LucidUI's deterministic metric engine provides explainable, metric-level signals, but it cannot capture holistic, learned notions of UI quality the way a model trained on UI preference data can. UIClip is integrated to provide that second, independent perspective — not to validate or override the deterministic engine.

## UIClip's Role as an Independent Learned Evaluator

UIClip and LucidUI's metric engine are never merged into a single score. They are run independently against the same decoded image and compared afterward by the Comparison Engine (see [docs/architecture/analysis-pipeline.md](../architecture/analysis-pipeline.md)). Neither is ground truth for the other — see [ADR-004](../architecture/decisions/ADR-004-uiclip-independent-evaluator.md).

## Planned Local Execution

UIClip is planned to run locally within the backend's environment (not as a call to an external hosted API), consistent with LucidUI's privacy model — see [docs/architecture/privacy-model.md](../architecture/privacy-model.md). This means the screenshot never has to leave the backend for UIClip evaluation, same as for the deterministic engine.

## Image Plus Natural-Language Description Input

UIClip is expected to take both the image and an optional natural-language description as input. The description improves the relevance of its evaluation. See Description Sources below.

## Description Sources

Per [docs/api/report-schema.md](../api/report-schema.md), a description passed to UIClip has a `descriptionSource`:

- `user` — typed by the person uploading the screenshot.
- `generic` — a placeholder/default string used when no description was provided.
- `generated` — produced by an automated description-generation model. Not to be used until such a model is actually implemented (see [CLAUDE.md](../../CLAUDE.md)).

## Sliding-Window Processing

UIClip integration is expected to use sliding-window processing over the image (evaluating sub-regions in addition to or instead of the whole image at once) as part of its planned inference approach (see [ROADMAP.md](../../ROADMAP.md) Phase 5). Exact windowing strategy is an implementation detail to be finalized in Phase 5, not decided in Phase 0.

## Model Checkpoint Metadata

Every UIClip result must report which model checkpoint/version produced it (`uiclip.modelVersion` in the report schema), so results remain traceable and reproducible across model updates.

## Preference-Score Interpretation

UIClip's output is called a **preference score**, not a quality score or percentage. It reflects the model's learned relative preference given its training data — it must never be presented as a percentage of objective UI quality, and must always be shown alongside its scale and model version. See language guidance in [docs/frontend/FRONTEND_GUIDE.md](../frontend/FRONTEND_GUIDE.md).

## Mock Evaluator First, Real Evaluator Later

Per [ADR-005](../architecture/decisions/ADR-005-mock-providers-before-real-integrations.md), a mock UIClip evaluator (Phase 4) is built before the real model integration (Phase 5), behind a shared `UIClipEvaluator` interface, so the API contract, pipeline, and frontend do not need to change when the real model is added.

## Failure Isolation

UIClip failures (`unavailable`, `failed`) must not fail the overall analysis. The deterministic metrics and LLM interpretation must still be returned, with the overall status reflected as `partial_success`. See [docs/api/report-schema.md](../api/report-schema.md).
