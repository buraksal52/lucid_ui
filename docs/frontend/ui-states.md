# UI States

The frontend must model these states explicitly across the upload-to-results flow described in [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md).

| State | Meaning |
|---|---|
| `idle` | No image selected yet; initial screen. |
| `file_selected` | An image has been selected/dropped but analysis has not started. |
| `submitting` | The analysis request is being sent to the backend. |
| `analyzing_metrics` | The backend has accepted the request and deterministic metrics are being computed. |
| `running_uiclip` | UIClip evaluation is in progress (may overlap with `interpreting` since they run independently — see [docs/architecture/analysis-pipeline.md](../architecture/analysis-pipeline.md)). |
| `interpreting` | LLM interpretation of the deterministic metrics is in progress. |
| `completed` | All requested stages finished successfully; full dashboard is shown. |
| `partial_success` | Deterministic metrics completed but at least one optional stage did not (`disabled`, `unavailable`, `fallback`, or `failed`). |
| `failed` | The deterministic metric engine failed; no usable report was produced. |

These map directly to the `status` values in [docs/api/report-schema.md](../api/report-schema.md). The `analyzing_metrics` / `running_uiclip` / `interpreting` states are frontend-only progress states inferred from elapsed time (the backend's single `POST /analyses/single` call does not stream sub-stage progress — the whole report arrives at once when the request completes).

**`status: "failed"` never actually appears in a report body in the current implementation.** If the deterministic metric engine fails, the backend raises before any `AnalysisReport` is constructed, and the request returns the `ANALYSIS_FAILED` HTTP error envelope instead (see [error-codes.md](../api/error-codes.md)) — there is no partial report to show. Treat the frontend's `failed` UI state as driven entirely by that HTTP-level error (or any other top-level error response), not by a `status` field value you need to check in a `200` body. The `failed` row above is kept for schema completeness/forward-compatibility, not because it is reachable today.

## Partial Success Behavior

When `status` is `partial_success`, render `presentation` exactly as given — it already reflects which stage did and didn't complete, so **no extra branching on `llmInterpretation.status`/`uiclip.status` is needed at the dashboard level**:

- `presentation.metricSections[].explanation` falls back to a fixed placeholder (`"No LLM interpretation is linked to this metric."`) on its own when the LLM stage didn't complete — every section still renders with its `rawDisplay` value.
- `presentation.uiclipSummary.status` carries `"disabled"`/`"unavailable"`/`"failed"`; `rawScoreDisplay`/`modelId`/`scoreType` are simply `null` in those cases — render the card in a neutral "not available" state (see [component-contracts.md](component-contracts.md) `PresentationDashboard`/`UIClipEvaluationCard`), never as an error.
- `presentation.closingNote` (same string as `note`) already explains, in one sentence, why a section is missing — surface it near the top of the dashboard (e.g. via `AnalysisSummary`) rather than re-deriving that explanation from individual statuses.

See [examples/single-analysis-partial-success-response.json](../api/examples/single-analysis-partial-success-response.json) for a real captured `partial_success` report (UIClip `unavailable`) to develop and test this state against.

## Failure Behavior

When the request itself errors (see [docs/api/error-codes.md](../api/error-codes.md) — in practice `VALIDATION_ERROR`, `UNSUPPORTED_MEDIA_TYPE`, `FILE_TOO_LARGE`, `INVALID_IMAGE`, `INVALID_CONTEXT`, `ANALYSIS_FAILED`, or `INTERNAL_ERROR`), the frontend shows `ErrorBanner` with the error code and message, and does not attempt to render any dashboard, since no report exists at all.
