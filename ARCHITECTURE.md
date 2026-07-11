# ARCHITECTURE

This document describes the planned architecture of LucidUI. No implementation exists yet; this defines the target shape for future phases. See [ROADMAP.md](ROADMAP.md) for sequencing and [docs/architecture/](docs/architecture/system-overview.md) for detailed breakdowns.

## High-Level Pipeline

```text
Image Upload
     |
     v
Validation and In-Memory Decoding
     |
     +----------------------------+
     |                            |
     v                            v
LucidUI Metric Engine       UIClip Evaluator
     |                            |
     v                            v
Deterministic Metric JSON   UIClip Result JSON
     |
     v
LLM Interpretation
     |
     +-------------+
                   |
                   v
           Comparison Engine
                   |
                   v
             Final Report
```

The LucidUI Metric Engine and the UIClip Evaluator both run against the same in-memory decoded image, independently. The LLM interpretation step consumes only the deterministic Metric JSON — never the raw image and never the UIClip output directly. The Comparison Engine is the only stage that reads both the LLM interpretation and the UIClip result together, and it produces agreement/discrepancy findings rather than a merged "correct" answer.

## Dependency Direction

```text
API -> Service -> Pipeline -> Domain Interfaces -> Adapters
```

- **API** routes only handle HTTP concerns: parsing requests, validating shape, returning responses and status codes. No business logic lives here.
- **Service** layer coordinates use cases (e.g. "run a single analysis," "run a variant comparison") and orchestrates calls into the pipeline.
- **Pipeline** layer coordinates the ordered analysis stages (validate → decode → metrics → LLM → UIClip → compare → assemble report).
- **Domain Interfaces** define abstract contracts for metric engines, LLM providers, UIClip evaluators, and repositories, so pipelines depend on behavior, not implementation.
- **Adapters** are concrete implementations of those interfaces (e.g. the legacy metric engine, the Anthropic LLM provider, the mock UIClip evaluator, an in-memory or PostgreSQL repository). Adapters are swappable without changing pipeline or service code.
- **Pydantic schemas** define the public data contracts crossing every one of these boundaries — they are the source of truth for shape, not internal dataclasses.
- The **frontend** consumes API contracts only. It never calculates or re-derives scores; it renders exactly what the backend reports.

## Why a Modular Monolith, Not Microservices

LucidUI starts as a single deployable FastAPI application organized into clearly separated internal modules (API, services, pipelines, domain interfaces, adapters) rather than as separate networked services. Reasons:

- The analysis pipeline is a single logical unit of work (decode → metrics → LLM → UIClip → compare) with tight sequencing; splitting it into services would add network latency and failure modes without a corresponding benefit at this stage.
- The system has one primary consumer (the dashboard) and no independent scaling requirements per component yet.
- A modular monolith preserves the option to extract a service later (for example, UIClip inference, which is GPU-bound) once real usage patterns justify it — see [ADR-001](docs/architecture/decisions/ADR-001-modular-monolith.md).
- Enforcing the dependency direction above inside one codebase gives most of the benefit of service boundaries (testability, replaceable adapters) without deployment complexity.

## Related Documents

- [docs/architecture/system-overview.md](docs/architecture/system-overview.md)
- [docs/architecture/analysis-pipeline.md](docs/architecture/analysis-pipeline.md)
- [docs/architecture/privacy-model.md](docs/architecture/privacy-model.md)
- [docs/architecture/decisions/](docs/architecture/decisions/ADR-001-modular-monolith.md)
