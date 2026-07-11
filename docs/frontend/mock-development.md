# Mock Development

The frontend can be built and tested before the backend exists, using the documented API contract and mocked example responses. See [ADR-005](../architecture/decisions/ADR-005-mock-providers-before-real-integrations.md) and [ADR-006](../architecture/decisions/ADR-006-frontend-backend-independence.md) for why this pattern is used across the project.

## Mock Data Sources

Use these files as the frontend's development-time data source:

```text
docs/api/examples/single-analysis-response.json
docs/api/examples/variant-analysis-response.json
docs/api/examples/error-response.json
```

These are schema-accurate, realistic examples matching [docs/api/report-schema.md](../api/report-schema.md) and [docs/api/error-codes.md](../api/error-codes.md), including a `partial_success` case (UIClip `unavailable` in `variant-analysis-response.json`).

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
