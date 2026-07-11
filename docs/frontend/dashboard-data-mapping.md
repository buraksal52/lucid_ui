# Dashboard Data Mapping

Maps report fields (see [docs/api/report-schema.md](../api/report-schema.md)) to proposed frontend components (see [component-contracts.md](component-contracts.md)). This is the reference for wiring the dashboard without inventing new field meanings.

| Report Field | Proposed Component | Notes |
|---|---|---|
| `status`, `note` | `AnalysisSummary` | Drives banner/summary state, including `partial_success` messaging. |
| `imageMetadata` | `AnalysisSummary`, `ImagePreview` | Dimensions, format, file size shown alongside the preview. |
| `lucidui.compositeSignalScore` | `CompositeSignalCard` | Always shown with its `publicName` and non-verdict framing. |
| `lucidui.raw.contrast` | `MetricCard` + `MetricDetailDrawer` | Includes threshold comparison (WCAG 2.1 AA). |
| `lucidui.raw.edgeDensity` | `MetricCard` + `MetricDetailDrawer` | Labeled as a visual clutter proxy. |
| `lucidui.raw.detectedElementCount` | `MetricCard` + `MetricDetailDrawer` | Feeds Hick's Law and Fitts's Law derived cards. |
| `lucidui.raw.*` (remaining metrics) | `MetricCard` + `MetricDetailDrawer` | One card per metric in [metric-catalog.md](../metrics/metric-catalog.md); drawer shows raw value, normalized value, source, threshold, proxy status, limitations. |
| `lucidui.normalized`, `lucidui.additionalSignals` | `MetricDetailDrawer` | Shown as supporting detail, not as the headline value. |
| `llmInterpretation.summary` | `LLMInterpretationPanel` | Top-level natural-language summary. |
| `llmInterpretation.observations` | `LLMInterpretationPanel` | Each observation renders with its `metricEvidence` linked back to the relevant `MetricCard`. |
| `llmInterpretation.status` | `LLMInterpretationPanel` | Drives empty/disabled/unavailable states. |
| `uiclip.preferenceScore`, `uiclip.scoreScale` | `UIClipEvaluationCard` | Shown as a model preference score, never as a percentage of objective quality. |
| `uiclip.description`, `uiclip.descriptionSource` | `UIClipEvaluationCard` | Source (`user`/`generic`/`generated`) shown so users know where the description came from. |
| `uiclip.status` | `UIClipEvaluationCard` | Drives disabled/unavailable/failed states. |
| `comparison.agreementLevel` | `AgreementPanel` | High-level agreement indicator. |
| `comparison.sharedFindings` | `AgreementPanel` | List of shared findings. |
| `comparison.luciduiOnlyFindings` | `DifferencePanel` | List of LucidUI-only findings. |
| `comparison.uiclipOnlyFindings` | `DifferencePanel` | List of UIClip-only findings. |
| `comparison.scoreDifference` | `AgreementPanel` | Numeric gap between composite score and UIClip preference score. |
| `timings.totalMs`, `timings.*` | `AnalysisSummary`, `RawJsonViewer` | Total shown in summary; per-stage breakdown available in raw view. |
| Any metric's `proxyStatus`, limitation text | `LimitationNotice`, `MetricDetailDrawer` | Always paired with the metric it describes. |
| Full report / `/analyses/{id}/raw` | `RawJsonViewer` | Escape hatch for technical users; not a primary dashboard element. |
| Any failed request | `ErrorBanner` | Renders `error.code` / `error.message` from [error-codes.md](../api/error-codes.md). |

For `deltas.*` fields in variant-comparison reports, the same components render twice (once per variant) plus a delta-specific view — not separately specified here since Phase 0 does not scaffold variant-specific components beyond reusing the single-analysis set.
