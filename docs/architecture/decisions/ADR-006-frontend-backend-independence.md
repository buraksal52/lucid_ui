# ADR-006: Frontend and Backend Are Developed Independently

## Status

Accepted

## Context

The React frontend and the FastAPI backend could be developed in lockstep (frontend PRs depend on matching backend PRs landing first) or independently against a shared, versioned API contract.

## Decision

The frontend is developed independently against the documented API contract ([docs/api/api-contract.md](../../api/api-contract.md), [docs/api/report-schema.md](../../api/report-schema.md)) and mocked example responses ([docs/api/examples/](../../api/examples/)). The frontend never computes or modifies scores — it only renders what the backend returns.

## Rationale

- Decouples frontend iteration speed from backend/model integration timelines (especially UIClip, which lands much later in the roadmap per [ROADMAP.md](../../../ROADMAP.md)).
- Forces the API contract to be explicit and stable enough to build against, which improves backend design discipline.
- Keeps all scoring/interpretation logic server-side, consistent with explainability and versioning requirements — the frontend is a rendering layer, not a second implementation of metric logic.

## Consequences

- `docs/api/examples/*.json` must be kept realistic and schema-accurate; they are the frontend's development contract until the real API exists. See [docs/frontend/mock-development.md](../../frontend/mock-development.md).
- Any backend change to the report schema must update both the documentation and the example JSON files in the same change.
- The frontend must not be modified as a side effect of backend-focused tasks, and vice versa, per [CLAUDE.md](../../../CLAUDE.md).
