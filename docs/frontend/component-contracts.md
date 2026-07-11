# Component Contracts

Proposed component responsibilities for the React frontend. This is a planning document, not implementation — no React code is written in Phase 0. See [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md) and [dashboard-data-mapping.md](dashboard-data-mapping.md) for surrounding context.

## UploadPanel

- **Purpose**: Accept a screenshot file via file picker or drag-and-drop, and optionally a second file for variant mode.
- **Required data**: None (initial state).
- **Optional data**: Accepted MIME types and max size, sourced from [docs/api/api-contract.md](../api/api-contract.md), for client-side pre-validation before submission.
- **Empty state**: Default prompt to select/drop a file.
- **Error state**: Client-side validation failure (wrong type, too large) shown inline before submission; server-side validation errors shown via `ErrorBanner` after submission.

## ImagePreview

- **Purpose**: Show the selected image(s) before and during analysis.
- **Required data**: Local file/object URL of the selected image.
- **Optional data**: `imageMetadata` once available, to annotate dimensions/format.
- **Empty state**: Not rendered until a file is selected.
- **Error state**: Broken/unreadable file preview falls back to a filename-only display.

## AnalysisProgress

- **Purpose**: Show current progress through `submitting` → `analyzing_metrics` → (`running_uiclip` / `interpreting`) → `completed`/`partial_success`/`failed` (see [ui-states.md](ui-states.md)).
- **Required data**: Current UI state.
- **Optional data**: Per-stage timing hints if the backend streams progress.
- **Empty state**: Not rendered in `idle`/`file_selected`.
- **Error state**: Transitions to `ErrorBanner` on `failed` or a request-level error.

## AnalysisSummary

- **Purpose**: Top-of-dashboard overview: overall status, composite signal score headline, and any `note`.
- **Required data**: `status`, `note`, `lucidui.compositeSignalScore`.
- **Optional data**: `imageMetadata`, `timings.totalMs`.
- **Empty state**: N/A — only rendered once a report exists.
- **Error state**: Renders a `partial_success` notice banner when applicable, sourced from `note`.

## CompositeSignalCard

- **Purpose**: Display the LucidUI Composite Signal Score with its non-verdict framing.
- **Required data**: `lucidui.compositeSignalScore` (`value`, `scale`, `publicName`, `note`).
- **Optional data**: `scoringRulesetVersion` for technical users.
- **Empty state**: Not rendered if `lucidui` stage did not complete (should not happen outside `failed` status).
- **Error state**: N/A — this card only renders on successful deterministic metrics.

## MetricCard

- **Purpose**: Summarize a single metric from [metric-catalog.md](../metrics/metric-catalog.md) (e.g. Contrast, Edge Density).
- **Required data**: One entry from `lucidui.raw.*` (value, unit, proxyStatus).
- **Optional data**: Corresponding entry from `lucidui.normalized` or `lucidui.additionalSignals`; `threshold`/`thresholdSource` if applicable.
- **Empty state**: N/A — one card per metric present in the report.
- **Error state**: If a specific metric is missing from the payload, the card is omitted rather than shown broken.

## MetricDetailDrawer

- **Purpose**: Expanded, technical view of a single metric: raw value, normalized value, source, threshold, proxy status, known limitations.
- **Required data**: The same metric object as the triggering `MetricCard`.
- **Optional data**: Cross-reference to relevant `known-limitations.md` entries and `llmInterpretation.observations` citing this metric via `metricEvidence`.
- **Empty state**: N/A — opened on demand from a `MetricCard`.
- **Error state**: N/A.

## LLMInterpretationPanel

- **Purpose**: Show the LLM's summary and evidence-linked observations.
- **Required data**: `llmInterpretation.status`.
- **Optional data**: `llmInterpretation.summary`, `llmInterpretation.observations` (present when `status: completed`).
- **Empty state**: When `status` is `disabled`, shows a neutral "LLM interpretation was not requested" message.
- **Error state**: When `status` is `unavailable`, `fallback`, or `failed`, shows a corresponding neutral status message — never framed as a defect in the UI being analyzed.

## UIClipEvaluationCard

- **Purpose**: Show UIClip's preference score and generated description.
- **Required data**: `uiclip.status`.
- **Optional data**: `uiclip.preferenceScore`, `uiclip.scoreScale`, `uiclip.description`, `uiclip.descriptionSource`, `uiclip.modelVersion` (present when `status: completed`).
- **Empty state**: When `status` is `disabled`, shows "UIClip evaluation was not requested."
- **Error state**: When `status` is `unavailable` or `failed`, shows a corresponding neutral status message.

## AgreementPanel

- **Purpose**: Show `comparison.agreementLevel`, `comparison.sharedFindings`, and `comparison.scoreDifference`.
- **Required data**: `comparison.agreementLevel`.
- **Optional data**: `comparison.sharedFindings`, `comparison.scoreDifference`.
- **Empty state**: Not rendered if either `lucidui`/`llmInterpretation` or `uiclip` did not complete (comparison is impossible).
- **Error state**: N/A — governed by upstream stage statuses.

## DifferencePanel

- **Purpose**: Show `comparison.luciduiOnlyFindings` and `comparison.uiclipOnlyFindings` side by side.
- **Required data**: `comparison.luciduiOnlyFindings`, `comparison.uiclipOnlyFindings`.
- **Optional data**: None.
- **Empty state**: Shows "No notable differences" if both lists are empty.
- **Error state**: Not rendered if comparison could not be computed (mirrors `AgreementPanel`).

## LimitationNotice

- **Purpose**: Surface relevant known limitations (from [known-limitations.md](../metrics/known-limitations.md)) next to the metric or section they apply to.
- **Required data**: A limitation text string and the metric/section it is attached to.
- **Optional data**: Link to the full known-limitations document.
- **Empty state**: Omitted if no limitation applies.
- **Error state**: N/A.

## RawJsonViewer

- **Purpose**: Show the full raw report JSON (or `/analyses/{id}/raw` payload) for technical users.
- **Required data**: The full report object.
- **Optional data**: Syntax highlighting, collapsible tree view.
- **Empty state**: N/A — always available once a report exists.
- **Error state**: N/A.

## ErrorBanner

- **Purpose**: Show request-level or stage-level errors using the shared error envelope.
- **Required data**: `error.code`, `error.message` (see [docs/api/error-codes.md](../api/error-codes.md)).
- **Optional data**: `error.details`.
- **Empty state**: Not rendered when there is no error.
- **Error state**: This component *is* the error state for other flows; it has no further degraded state of its own.
