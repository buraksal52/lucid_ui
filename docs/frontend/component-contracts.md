# Component Contracts

Proposed component responsibilities for the React frontend. See [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md) and [dashboard-data-mapping.md](dashboard-data-mapping.md) for surrounding context. Field names below are verified against the real, current schema ([report-schema.md](../api/report-schema.md), [presentation-schema.md](../api/presentation-schema.md), [examples/single-analysis-response.json](../api/examples/single-analysis-response.json)) — build against these, not older assumptions.

## PresentationDashboard (Primary — build this first)

- **Purpose**: Render the full ready-to-render report — title, summary, metric section cards, composite summary, UIClip summary card, recommendations, limitations, closing note — directly from `presentation` (see [presentation-schema.md](../api/presentation-schema.md)), without deriving any of it itself.
- **Required data**: `presentation` (`title`, `context`, `summary`, `metricSections[]`, `composite`, `uiclipSummary`, `recommendations[]`, `limitations[]`, `closingNote`).
- **Optional data**: None — every field it needs is already present and pre-formatted (`rawDisplay` strings, matched `explanation` text, etc.). Do not fetch or compute anything beyond this object.
- **Empty state**: N/A — only rendered once a report exists; `presentation` is always populated (never partially missing) whenever `AnalysisReport` itself is returned.
- **Error state**: Individual metric/UIClip-card sub-states (e.g. a `null` `uiclipSummary.rawScoreDisplay`, or a metric section's fallback `explanation` text) are rendered as neutral "not available" text, never as a defect in the analyzed UI, and never re-derived or reworded. The components below (`MetricCard`, `UIClipEvaluationCard`, etc.) remain valid as the raw/technical view; `PresentationDashboard` is the primary one and should be built first.

## UploadPanel

- **Purpose**: Accept a screenshot file via file picker or drag-and-drop.
- **Required data**: None (initial state).
- **Optional data**: Accepted MIME types (`image/jpeg`, `image/png`, `image/webp`) and max size (20 MB), sourced from [docs/api/api-contract.md](../api/api-contract.md), for client-side pre-validation before submission. Also collects the optional `context` (`general`/`expert`) and free-text `description` form fields.
- **Empty state**: Default prompt to select/drop a file.
- **Error state**: Client-side validation failure (wrong type, too large) shown inline before submission; server-side validation errors (`UNSUPPORTED_MEDIA_TYPE`, `FILE_TOO_LARGE`, `INVALID_IMAGE`, `INVALID_CONTEXT`, `VALIDATION_ERROR`) shown via `ErrorBanner` after submission.

## ImagePreview

- **Purpose**: Show the selected image before and during analysis.
- **Required data**: Local file/object URL of the selected image.
- **Optional data**: `imageMetadata` (`width`, `height`, `format`, `aspectRatio`, `orientation`, `fileSizeBytes`) once available, to annotate dimensions/format.
- **Empty state**: Not rendered until a file is selected.
- **Error state**: Broken/unreadable file preview falls back to a filename-only display.

## AnalysisProgress

- **Purpose**: Show progress while awaiting the single `POST /analyses/single` response — `submitting` → `analyzing_metrics`/`running_uiclip`/`interpreting` (frontend-only, inferred; the backend does not stream sub-stage progress) → `completed`/`partial_success` (see [ui-states.md](ui-states.md)).
- **Required data**: Current frontend-local UI state (there is no backend job/progress endpoint to poll).
- **Optional data**: None.
- **Empty state**: Not rendered in `idle`/`file_selected`.
- **Error state**: Transitions to `ErrorBanner` on any request-level HTTP error (see [error-codes.md](../api/error-codes.md)) — not on a report `status` value, since a `200` response is never itself an error state.

## AnalysisSummary

- **Purpose**: Top-of-dashboard overview: overall status, composite score headline, and the closing note.
- **Required data**: `status`, `presentation.closingNote` (same string as top-level `note`), `presentation.composite.rawDisplay`.
- **Optional data**: `imageMetadata`, `timings.totalMs`.
- **Empty state**: N/A — only rendered once a report exists.
- **Error state**: Renders a `partial_success` notice when `status === "partial_success"`, sourced from `presentation.closingNote` — never re-derive this explanation from individual stage statuses (see [ui-states.md](ui-states.md#partial-success-behavior)).

## MetricCard

- **Purpose**: Render one entry from `presentation.metricSections[]` (e.g. Contrast, Visual Complexity/Edge Density) — see [presentation-schema.md](../api/presentation-schema.md) for the full fixed-order list.
- **Required data**: One `presentation.metricSections[]` entry: `id`, `title`, `category`, `rawDisplay` (render verbatim, it is already formatted, e.g. `"1.27:1"`, `"74.75%"`), `explanation` (render verbatim; never `null`).
- **Optional data**: `normalizedScore` (may be `null` — not every metric has one, by design, not by omission), `source` (may be `null`), `isProxy`.
- **Empty state**: N/A — exactly 7 entries are always present, in the same fixed order, on every report (as of `corrected-v4`; see [reliability-tiers.md](../metrics/reliability-tiers.md) for the removed Tier 3 sections).
- **Error state**: N/A — there is no missing-metric case for this component; a `null` `normalizedScore`/`source` is a normal, expected value, not an error.
- **Known follow-up (not built this pass)**: some `source` strings (e.g. the `elements` section's) are long and implementation-heavy for a primary-dashboard card — see the raw JSON in [examples/single-analysis-response.json](../api/examples/single-analysis-response.json). A future pass should collapse the full `source` text behind a `<details>`/expandable affordance, defaulting closed, without altering the rest of the card's layout or classes — deliberately deferred to avoid a frontend redesign as a side effect of the Interpretation Hardening pass.

## MetricDetailDrawer (raw/technical view only)

- **Purpose**: Expanded, technical view of a single metric's underlying raw data — `lucidui.raw.*`/`lucidui.additionalSignals.*` and `lucidui.normalized` — for technical users who want the unformatted values behind a `MetricCard`.
- **Required data**: The matching raw metric object (e.g. `lucidui.raw.contrast`) plus, where present, `lucidui.normalized.<key>`.
- **Optional data**: The originating `presentation.metricSections[].evidencePaths` (to cross-reference which `llmInterpretation.observations[].metricEvidence` entries fed this metric's explanation) and relevant [known-limitations.md](../metrics/known-limitations.md) entries.
- **Empty state**: N/A — opened on demand from a `MetricCard`.
- **Error state**: N/A.

## LLMInterpretationPanel (raw/technical view only)

- **Purpose**: Show the LLM's raw summary and evidence-linked observations, independent of the per-metric linking `presentation.metricSections[].explanation` already does.
- **Required data**: `llmInterpretation.status`.
- **Optional data**: `llmInterpretation.summary`, `llmInterpretation.observations[]` (`id`, `text`, `metricEvidence[]`, `category`), `llmInterpretation.recommendations[]`, `llmInterpretation.limitations[]` (all present when `status: "completed"`, empty/`null` otherwise).
- **Empty state**: When `status` is `"disabled"`, shows a neutral "LLM interpretation was not requested" message.
- **Error state**: When `status` is `"unavailable"` or `"failed"`, shows a corresponding neutral status message — never framed as a defect in the UI being analyzed. (`"fallback"` is a reserved, currently-unused status — no fallback path exists yet.)

## UIClipEvaluationCard (raw/technical view only)

- **Purpose**: Show UIClip's raw score and generated description, independent of the ready-to-render `presentation.uiclipSummary` card.
- **Required data**: `uiclip.status`.
- **Optional data**: `uiclip.qualityScore` (the real raw model score — an uncalibrated CLIP-style logit, not a 0–100/0–1 percentage), `uiclip.normalizedQualityScore` (always `null` today), `uiclip.description`, `uiclip.descriptionSource` (`user`/`generic`), `uiclip.modelVersion` (present when `status: "completed"`), `uiclip.observations[]` (plain strings).
- **Empty state**: When `status` is `"disabled"`, shows "UIClip evaluation was not requested."
- **Error state**: When `status` is `"unavailable"` or `"failed"`, shows a corresponding neutral status message. Never label `qualityScore` as directly comparable to `lucidui.weightedScore` — see `presentation.uiclipSummary.comparabilityNote`.

## AgreementPanel / DifferencePanel — do not build against real data yet

- **Purpose (planned, Phase 6)**: Show `comparison.agreementLevel`, `comparison.sharedFindings`, `comparison.luciduiOnlyFindings`, `comparison.uiclipOnlyFindings`, `comparison.absoluteScoreDifference`.
- **Current reality**: `comparison.agreementLevel` is always `"unavailable"` and every finding list is always empty — the Comparison Engine is not implemented (see [ADR-004](../architecture/decisions/ADR-004-uiclip-independent-evaluator.md), Phase 6 in [ROADMAP.md](../../ROADMAP.md)). Do not build these components to render real agreement/disagreement data yet; if a placeholder is needed, render `comparison.interpretation` verbatim (a fixed sentence explaining that comparison hasn't been computed) rather than an empty panel that looks broken.

## LimitationNotice

- **Purpose**: Surface `presentation.limitations[]` (always includes a fixed proxy-signal disclaimer first, followed by any real `llmInterpretation.limitations[]`) next to the section they apply to, or in a dedicated limitations area.
- **Required data**: `presentation.limitations[]`.
- **Optional data**: Link to [known-limitations.md](../metrics/known-limitations.md) for the fuller per-metric detail.
- **Empty state**: Never empty — the fixed disclaimer is always present.
- **Error state**: N/A.

## RawJsonViewer

- **Purpose**: Show the full report JSON (`GET /analyses/{id}` or `/analyses/{id}/raw` — currently identical) for technical users.
- **Required data**: The full report object.
- **Optional data**: Syntax highlighting, collapsible tree view.
- **Empty state**: N/A — always available once a report exists.
- **Error state**: N/A.

## VariantUploadPanel

- **Purpose**: Accept two screenshot files (variant A and variant B) for `POST /api/v1/analyses/variants`. Two instances of `UploadPanel`'s validation logic side by side, not a new validation ruleset — see [api-contract.md](../api/api-contract.md).
- **Required data**: None (initial state).
- **Optional data**: Same accepted MIME types/max size as `UploadPanel`; one shared `context`; per-variant `descriptionA`/`descriptionB`.
- **Empty state**: Default prompt to select/drop a file, per slot.
- **Error state**: Same client-side pre-validation as `UploadPanel`, applied independently to each slot; server-side errors shown via `ErrorBanner` after submission (a validation failure on either image fails the whole request — see [api-contract.md](../api/api-contract.md)).

## VariantComparisonDashboard

- **Purpose**: Render a `VariantAnalysisReport` (`POST /api/v1/analyses/variants`'s response) — variant A's and variant B's full dashboards side by side, plus a `DeltaPanel`.
- **Required data**: `variantA`, `variantB` (each rendered via the existing `PresentationDashboard`/lane components — reuse them, do not fork or reimplement), `deltas`.
- **Optional data**: `status`, `note`, `timings`.
- **Empty state**: N/A — only rendered once a `VariantAnalysisReport` exists.
- **Error state**: Same `partial_success` handling as `AnalysisSummary`, applied per variant (`variantA.status`/`variantB.status`) and to the envelope's own `status`.

## DeltaPanel

- **Purpose**: Render `deltas` from a `VariantAnalysisReport` — relative differences between variant A and variant B, verbatim, with no client-side computation.
- **Required data**: `deltas.metricDeltas[]` (`id`, `title`, `category`, `rawDisplayA`, `rawDisplayB`, `direction`), `deltas.compositeScoreDeltaDisplay`, `deltas.uiclipRawScoreDeltaDisplay`, `deltas.note`.
- **Optional data**: `deltas.metricDeltas[].normalizedScoreDelta`/`deltas.compositeScoreDelta`/`deltas.uiclipRawScoreDelta` (the raw numeric deltas, `null` when not available — the pre-formatted `*Display` strings are what should actually be shown to the user).
- **Empty state**: N/A — `metricDeltas` always has exactly the same fixed 7 entries as `presentation.metricSections` (as of `corrected-v4`).
- **Error state**: A `null` delta (rendered via its `*Display`/`"not_available"` counterpart) is a normal, expected value when either variant didn't produce that signal — never treated as a defect. `direction` must be rendered as `higher`/`lower`/`equal`/`not_available` language only — never `better`/`worse`, per CLAUDE.md ("Flashlight, Not a Judge") and the Language Guidelines in [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md).

## ErrorBanner

- **Purpose**: Show request-level errors using the shared error envelope.
- **Required data**: `error.code`, `error.message` (see [docs/api/error-codes.md](../api/error-codes.md) for the full code catalog and per-code `details` shape).
- **Optional data**: `error.details` (shape varies by `code` — see [error-codes.md](../api/error-codes.md)'s catalog table; safe to log even when not rendered directly).
- **Empty state**: Not rendered when there is no error.
- **Error state**: This component *is* the error state for other flows; it has no further degraded state of its own. Note: `LLM_UNAVAILABLE`/`UICLIP_UNAVAILABLE` never reach this component — those degrade a `200` report's `llmInterpretation.status`/`uiclip.status` instead (see [error-codes.md](../api/error-codes.md)).
