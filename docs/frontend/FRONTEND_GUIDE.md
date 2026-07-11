# Frontend Guide

The React frontend is developed independently from the backend, against the documented API contract. See [ADR-006](../architecture/decisions/ADR-006-frontend-backend-independence.md) and [mock-development.md](mock-development.md) for how to build without a running backend.

## Frontend Responsibilities

- Upload images (JPG, PNG, WebP).
- Collect optional descriptions and context from the user.
- Send API requests to the LucidUI backend (`/api/v1/analyses/single`, `/api/v1/analyses/variants`).
- Display loading, partial-success, success, and error states (see [ui-states.md](ui-states.md)).
- Visualize backend results (metrics, LLM interpretation, UIClip evaluation, comparison).
- Preserve backend values exactly as returned — display, don't transform.
- Never calculate or modify metric scores, composite scores, or comparison findings client-side.
- Never present LucidUI or UIClip output as objective truth — see Language Guidelines below.

## Backend Responsibilities (Not the Frontend's Job)

- Request validation (MIME type, file size, context values).
- Image decoding.
- Deterministic metric computation (LucidUI engine).
- LLM interpretation of metrics.
- UIClip inference.
- Comparison between LucidUI and UIClip output.
- Final report generation and versioning.

If a frontend task seems to require computing or re-deriving a score, that is a sign the request belongs in the backend, not the frontend — flag it rather than implementing it client-side.

## Planned User Flow

```text
Upload
-> Preview and Description
-> Start Analysis
-> Processing
-> Results Dashboard
```

1. **Upload** — user selects or drags a screenshot file.
2. **Preview and Description** — user sees a preview of the selected image and can optionally add a free-text description and pick a context (`general`/`expert`).
3. **Start Analysis** — user submits; the frontend calls the appropriate endpoint.
4. **Processing** — the frontend shows progress across the sub-stages (metrics, LLM, UIClip) as reflected by the `analyzing_metrics` / `interpreting` / `running_uiclip` UI states (see [ui-states.md](ui-states.md)).
5. **Results Dashboard** — the frontend renders the completed (or partially completed) report.

## Dashboard Sections

1. **Analysis summary** — overall status, composite signal score, top-level note.
2. **LucidUI metrics** — raw and normalized metric values, organized by the [metric catalog](../metrics/metric-catalog.md).
3. **LLM interpretation** — summary and evidence-linked observations.
4. **UIClip evaluation** — preference score, model-generated description, status.
5. **LucidUI versus UIClip comparison** — shared findings, LucidUI-only findings, UIClip-only findings, agreement level.
6. **Technical details and limitations** — raw JSON access, proxy-status disclosures, known limitations relevant to the shown metrics.

See [dashboard-data-mapping.md](dashboard-data-mapping.md) for exact report-field-to-component mapping, and [component-contracts.md](component-contracts.md) for component-level responsibilities.

## Language Guidelines

LucidUI is a flashlight, not a judge — see [CLAUDE.md](../../CLAUDE.md) and [docs/product/terminology.md](../product/terminology.md). All frontend copy must follow this.

**Avoid**:

- "bad design" / "failed design"
- "UIClip says this is better"
- "scientifically proven quality"
- "accessibility passed"

**Prefer**:

- "below the selected reference threshold"
- "potential review area"
- "higher UIClip preference score"
- "proxy signal"
- "estimated"
- "detected"
- "model-based observation"

**Color usage**: red and green (or any color coding) must not be used to automatically mean "bad" and "good." Use color to indicate direction relative to a threshold (e.g. above/below), not a verdict. Always pair color with explicit threshold/label text, never color alone.

## Related Documents

- [dashboard-data-mapping.md](dashboard-data-mapping.md)
- [ui-states.md](ui-states.md)
- [component-contracts.md](component-contracts.md)
- [mock-development.md](mock-development.md)
- [docs/api/api-contract.md](../api/api-contract.md)
- [docs/api/report-schema.md](../api/report-schema.md)
