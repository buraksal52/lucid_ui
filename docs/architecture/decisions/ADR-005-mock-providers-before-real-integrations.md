# ADR-005: Mock Providers Before Real Integrations

## Status

Accepted

## Context

LucidUI depends on two external/heavy components: an LLM provider (e.g. Anthropic's API) and the UIClip model (a local but resource-intensive VLM). Building the API contract, pipeline, and frontend against these directly from the start would couple early development to API keys, network availability, and GPU/model-loading time.

## Decision

Both the LLM provider and the UIClip evaluator are built behind interfaces with mock implementations first (Phase 3 mock LLM provider, Phase 4 mock UIClip evaluator). Real integrations (Anthropic provider, real UIClip model loading) are added afterward (Phase 3 real provider, Phase 5) without changing the interface or the report schema.

## Rationale

- Lets the API contract, pipeline orchestration, and frontend be built and tested deterministically, without network calls or GPU dependency.
- Forces the interface design to be decided from real usage needs rather than from whatever a specific SDK happens to expose.
- Makes `disabled` and `unavailable` states first-class from the start, since a mock can simulate them, rather than being bolted on after the real integration exists.

## Consequences

- `LLMProvider` and `UIClipEvaluator` interfaces must be defined before either mock is implemented.
- Mock outputs must conform exactly to the same schema real outputs will use, so switching providers is a configuration change, not a schema change.
- Tests written against mocks in Phases 3–4 must continue to pass unchanged once real integrations land in later phases.
