# Dashboard Data Mapping

Maps real report fields (see [docs/api/report-schema.md](../api/report-schema.md), field names verified against [examples/single-analysis-response.json](../api/examples/single-analysis-response.json)) to proposed frontend components (see [component-contracts.md](component-contracts.md)). This is the reference for wiring the dashboard without inventing new field meanings.

## Primary Path: `presentation.*`

`presentation` (see [presentation-schema.md](../api/presentation-schema.md)) is built once by the backend from `lucidui`/`llmInterpretation`/`uiclip` — fixed-order metric sections, pre-formatted display strings, a composite summary, a UIClip summary card, and evidence-linked explanations, all ready to render. **Build the primary dashboard against this table**, not the raw fields further down.

| Report Field | Proposed Component | Notes |
|---|---|---|
| `presentation.title`, `presentation.summary` | `AnalysisSummary` | Top-of-dashboard heading and plain-language summary (already falls back to a fixed placeholder if the LLM stage didn't complete — no empty-state branching needed). |
| `presentation.closingNote` | `AnalysisSummary` | Same string as top-level `note`; explains any partial-success condition in one sentence. |
| `presentation.metricSections[]` | `PresentationDashboard` → one `MetricCard` per entry | Iterate in array order — it is already the fixed, documented order (contrast → clutter → elements → Hick's Law → grouping → text density → whitespace/alignment → colorfulness → Fitts's Law → visual balance). Each entry has everything one card needs: `title`, `category`, `rawDisplay` (pre-formatted string, render as-is), `normalizedScore` (may be `null` — omit or show "not normalized" rather than treating as an error), `explanation` (never `null` — always either a matched LLM observation or a fixed placeholder string), `source` (may be `null`), `isProxy`. |
| `presentation.composite` | `CompositeSignalCard`-equivalent | `rawDisplay` (e.g. `"46.9 / 100"`), `value` (same number as `lucidui.weightedScore`), `scoreName`, fixed `explanation` disclaimer — render `explanation` verbatim, do not paraphrase it into a verdict. |
| `presentation.uiclipSummary` | `UIClipEvaluationCard` | `status` drives the card's state (`completed`/`disabled`/`unavailable`/`failed`). `modelId`, `userDescription`, `rawScoreDisplay`, `scoreType`, `normalizedScoreDisplay` are all `null` unless there is real data for them — render `null` as a neutral "not available," never as an error. `comparableToLucidui` is always `false`; always render `comparabilityNote` next to the score so it's never implied to be on the same scale as `presentation.composite`. |
| `presentation.recommendations` | `LLMInterpretationPanel`-equivalent | List of strings, verbatim; empty list if the LLM stage didn't complete. |
| `presentation.limitations` | `LimitationNotice` | List of strings; always has at least the fixed proxy-signal disclaimer as its first entry. |

## Raw / Technical View: `lucidui`, `llmInterpretation`, `uiclip`, `comparison`, `timings`

These remain available, unchanged, for a secondary technical/raw view (`RawJsonViewer`, an expandable "technical details" drawer) — not the primary dashboard.

| Report Field | Proposed Component | Notes |
|---|---|---|
| `status`, `note` | `AnalysisSummary` | `status` is `"completed"` or `"partial_success"` in practice — see [report-schema.md](../api/report-schema.md#analysis-statuses) for why `queued`/`processing`/`failed` don't occur in a `200` body. |
| `imageMetadata` (`width`, `height`, `format`, `aspectRatio`, `orientation`, `fileSizeBytes`) | `AnalysisSummary`, `ImagePreview` | Real decoded-image fields — not `fileName`/`widthPx`/`heightPx`/`colorMode`. |
| `lucidui.weightedScore`, `lucidui.scoreName` | Raw view only | Same value as `presentation.composite.value`/`scoreName` — prefer the presentation version for display. |
| `lucidui.raw.contrast`, `.clutter`, `.elements`, `.groups`, `.textDensity`, `.whitespaceAlignment` | `MetricDetailDrawer` | Exact legacy engine field names (e.g. `contrast.averageContrastRatio`, `elements.hicksLawEstimateMs`, `elements.smallTargetsBelow44px`) — see [metric-catalog.md](../metrics/metric-catalog.md). Each already has its formatted counterpart in `presentation.metricSections`. |
| `lucidui.additionalSignals.colorfulness`, `.fittsFullIndexOfDifficulty`, `.visualBalance` | `MetricDetailDrawer` | Same relationship — `presentation.metricSections` already surfaces these as the Colorfulness/Fitts's Law/Visual Balance cards. |
| `lucidui.normalized` | `MetricDetailDrawer` | Only 5 keys exist: `contrast`, `clutter`, `textDensity`, `elementSize`, `groupCount` — there is no normalized form for Hick's Law, whitespace/alignment, colorfulness, Fitts's Law, or visual balance (`presentation.metricSections[].normalizedScore` is `null` for those, by design, not by omission). |
| `llmInterpretation.summary`, `.observations[].text`/`.metricEvidence`/`.category` | `LLMInterpretationPanel` (raw view) | `metricEvidence` entries are JSON paths like `"lucidui.raw.contrast.averageContrastRatio"` — `presentation.metricSections[].evidencePaths`/`.explanation` already resolve this linkage for you. |
| `llmInterpretation.status`, `.provider` | `LLMInterpretationPanel` | `status`: `completed`/`disabled`/`unavailable`/`fallback` (reserved, unused today)/`failed`. `provider`: `"mock"` or `"gemini"`, `null` unless `completed`. |
| `uiclip.status`, `.enabled`, `.modelVersion`, `.description`, `.descriptionSource`, `.qualityScore`, `.normalizedQualityScore`, `.observations`, `.inferenceTimeMs` | `UIClipEvaluationCard` (raw view) | `qualityScore` is the real UIClip raw model score; `normalizedQualityScore` is always `null` (no verified normalization exists) — see [api-contract.md](../api/api-contract.md) "UIClip Evaluation". `presentation.uiclipSummary` already formats these. |
| `comparison.*` | Not rendered as a comparison UI yet | `comparison.agreementLevel` is always `"unavailable"` — Phase 6 is not implemented. `comparison.luciduiWeightedScore`/`uiclipNormalizedQualityScore` just carry each system's own already-shown score through for reference; `sharedFindings`/`luciduiOnlyFindings`/`uiclipOnlyFindings` are always empty today. Do not build `AgreementPanel`/`DifferencePanel` against real disagreement data yet — there is none. |
| `timings.totalMs`, `.luciduiMs`, `.llmMs`, `.uiclipMs`, `.comparisonMs` | `AnalysisSummary`, `RawJsonViewer` | Per-stage duration in ms; `comparisonMs` is always `0` (Phase 6 not implemented). With the mock providers these are near-instant (single-digit/zero ms); with real `gemini`/`huggingface` providers, `llmMs`/`uiclipMs` will be much higher (hundreds to low thousands of ms). |
| Full report / `GET /analyses/{id}/raw` | `RawJsonViewer` | Currently identical to `GET /analyses/{id}` — no separate raw payload exists beyond what `lucidui.raw` already carries. |
| Any failed request | `ErrorBanner` | Renders `error.code`/`error.message` from [error-codes.md](../api/error-codes.md) — see that document's `details` shape per code. |

## Not Yet Applicable

`POST /api/v1/analyses/variants` and its `deltas.*` fields are **not implemented** (Phase 7) — do not build a variants dashboard yet. See [api-contract.md](../api/api-contract.md) and [report-schema.md](../api/report-schema.md#variant-analysis-report-structure--planned-not-implemented-phase-7).
