# ADR-001: Start as a Modular Monolith

## Status

Accepted

## Context

LucidUI's analysis pipeline chains several distinct capabilities: image validation/decoding, deterministic CV/OCR metrics, an LLM interpretation call, a UIClip model evaluation, and a comparison step. These could be built as separate networked services (e.g. a metrics service, an LLM gateway, a UIClip inference service) or as modules within a single deployable application.

## Decision

LucidUI starts as a single FastAPI application organized into internally separated layers — API, Service, Pipeline, Domain Interfaces, Adapters (see [ARCHITECTURE.md](../../../ARCHITECTURE.md)) — rather than as microservices.

## Rationale

- The pipeline stages are tightly sequenced for a single request; splitting them into networked services adds latency and failure surface without a corresponding benefit at current scale.
- There is one primary consumer (the dashboard) and no component has an independent scaling requirement yet.
- Enforcing strict internal dependency direction and interface boundaries gives most of the testability and swappability benefits of service boundaries without deployment complexity.
- The module boundaries are drawn so that a component (most likely UIClip inference, which is GPU-bound) can be extracted into its own service later without a rewrite, once real usage data justifies it.

## Consequences

- All backend code lives in one deployable unit through at least Phase 11.
- Adapters (metric engine, LLM provider, UIClip evaluator, repository) must be written behind interfaces from the start so a future extraction is a boundary change, not a redesign.
- This decision should be revisited if UIClip inference latency or resource needs make co-location with the API impractical.
