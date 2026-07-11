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

These map directly to the `status` values in [docs/api/report-schema.md](../api/report-schema.md). The `analyzing_metrics` / `running_uiclip` / `interpreting` states are frontend-only progress states inferred from elapsed time and/or streaming updates (if implemented) — the backend's own status enum does not need sub-stage granularity in Phase 0–1.

## Partial Success Behavior

When `status` is `partial_success`, the dashboard must still render every section that did complete, rather than hiding the whole results view. Example:

- LucidUI metrics: `completed` → render `MetricCard`s and `CompositeSignalCard` normally.
- LLM interpretation: `completed` → render `LLMInterpretationPanel` normally.
- UIClip: `unavailable` → render `UIClipEvaluationCard` in its unavailable state (see [component-contracts.md](component-contracts.md)), and skip or gray out `AgreementPanel`/`DifferencePanel` since no comparison could be computed.

The `note` field on the report should be surfaced near the top of the dashboard (e.g. via `AnalysisSummary`) so the user understands why a section is missing, without treating it as an error.

## Failure Behavior

When `status` is `failed`, or the request itself errors (see [docs/api/error-codes.md](../api/error-codes.md)), the frontend shows `ErrorBanner` with the error code and message, and does not attempt to render a partial dashboard, since no deterministic metrics exist to show.
