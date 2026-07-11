# System Overview

LucidUI is a modular monolith with four internal layers: API, Service, Pipeline, and Adapters (implementing Domain Interfaces). See [ARCHITECTURE.md](../../ARCHITECTURE.md) for the top-level pipeline diagram and dependency direction.

## Modules (Planned)

- **`api/`** — FastAPI routers. One router per resource (`health`, `analyses`). Routes validate request shape via Pydantic, call a service method, and return its result. No metric logic, no LLM calls, no file handling beyond receiving the upload.
- **`services/`** — Use-case coordinators. Example: `AnalysisService.run_single(image, context, description, run_llm, run_uiclip)`. Services translate API-level requests into pipeline invocations and assemble the final report shape.
- **`pipelines/`** — Ordered execution of analysis stages for a single request: validate → decode → run metric engine → run UIClip evaluator (if enabled) → run LLM interpretation (if enabled) → run comparison → assemble report. Pipelines own sequencing, timing capture, and partial-failure handling.
- **`domain/`** — Abstract interfaces: `MetricEngine`, `LLMProvider`, `UIClipEvaluator`, `AnalysisRepository`. Pipelines depend only on these interfaces.
- **`adapters/`** — Concrete implementations: legacy metric engine adapter, mock/Anthropic LLM providers, mock/real UIClip evaluators, in-memory/PostgreSQL repositories.
- **`schemas/`** — Pydantic models defining every request and response contract, matching [docs/api/report-schema.md](../api/report-schema.md).

## Component Independence

The LucidUI metric engine and the UIClip evaluator are independent components that do not call each other and do not share state. Both consume the same decoded in-memory image and each produce their own JSON output. This independence is intentional — see [ADR-004](decisions/ADR-004-uiclip-independent-evaluator.md) and [docs/product/terminology.md](../product/terminology.md).

## Related Documents

- [analysis-pipeline.md](analysis-pipeline.md) — stage-by-stage walkthrough of a single analysis request.
- [privacy-model.md](privacy-model.md) — what data leaves the backend process and what stays local.
- [decisions/](decisions/ADR-001-modular-monolith.md) — architecture decision records.
