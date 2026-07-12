# Mock Development

The frontend can be built and tested without running the Python backend, using the documented API contract and real, captured example responses. See [ADR-005](../architecture/decisions/ADR-005-mock-providers-before-real-integrations.md) and [ADR-006](../architecture/decisions/ADR-006-frontend-backend-independence.md) for why this pattern is used across the project.

## Mock Data Sources

Use these files as the frontend's development-time data source:

```text
docs/api/examples/single-analysis-response.json                  — completed (LLM + UIClip mock providers both ran)
docs/api/examples/single-analysis-partial-success-response.json  — partial_success (UIClip unavailable, LLM completed)
docs/api/examples/error-response.json                            — error envelope (UNSUPPORTED_MEDIA_TYPE)
```

The two `single-analysis-*` files are **real captured responses** from the live backend (mock LLM provider, a fake unavailable UIClip provider for the partial-success case) — not hand-written approximations — so they are safe to treat as field-for-field authoritative alongside [report-schema.md](../api/report-schema.md) and [presentation-schema.md](../api/presentation-schema.md). Use `single-analysis-response.json` to build and exercise the primary "everything completed" dashboard path (`presentation.uiclipSummary.status: "completed"`), and `single-analysis-partial-success-response.json` to exercise the partial-success path (`status: "partial_success"`, `presentation.uiclipSummary.status: "unavailable"`, `rawScoreDisplay: null`) — see [ui-states.md](ui-states.md).

`docs/api/examples/variant-analysis-response.json` is **not usable as mock data** — `POST /api/v1/analyses/variants` is not implemented (Phase 7), and that file's nested field names predate the real single-analysis contract (see [api-contract.md](../api/api-contract.md)). Do not use it to build or test anything yet.

## Recommended Setup

Use an environment variable to toggle between mock and real API data:

```env
VITE_USE_MOCK_API=true
```

When `true`, the frontend's data-fetching layer resolves requests using the example JSON files (or an equivalent in-memory mock module) instead of calling the backend.

## Rules

- Mock schemas must match the documented API contract exactly — no separate, frontend-invented response format.
- Mock examples must include unavailable and partial-success cases, not only the fully successful path, so those UI states (see [ui-states.md](ui-states.md)) are exercised during development.
- Switching from mock data to the real API must only require replacing the data source (e.g. flipping `VITE_USE_MOCK_API` and pointing at the backend base URL) — it must not require changing any component's props or rendering logic.
- If the backend's report shape changes, the example JSON files under `docs/api/examples/` must be updated in the same change (see [ADR-006](../architecture/decisions/ADR-006-frontend-backend-independence.md)), so mock and real data never silently diverge.
