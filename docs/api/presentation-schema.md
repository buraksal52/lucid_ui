# Presentation Report Schema

`AnalysisReport.presentation` is a ready-to-render view over the same analysis's `lucidui`, `llmInterpretation`, and `uiclip` sections. It exists so the frontend never has to interpret metrics, map fields, generate text, or compute scores itself — see [docs/frontend/FRONTEND_GUIDE.md](../frontend/FRONTEND_GUIDE.md).

It is **additive**: `lucidui`, `llmInterpretation`, `uiclip`, `comparison`, and `timings` are unchanged, unrenamed, and still present — see [report-schema.md](report-schema.md). `presentation` is built once, after those sections are already computed, by a small pure function (`app/presentation/report_builder.py`). That builder:

- never re-runs `MetricEngine`,
- never calls the LLM provider again,
- never calls the UIClip provider again,
- never changes a raw or normalized numeric value — it only formats display strings and links existing LLM observations to existing metrics.

## Shape

```json
{
  "title": "LucidUI Design Signal Report",
  "context": "general",
  "summary": "…",
  "metricSections": [ { "...": "see below" } ],
  "composite": { "...": "see below" },
  "uiclipSummary": { "...": "see below" },
  "recommendations": ["…"],
  "limitations": ["…"],
  "closingNote": "…"
}
```

- **`title`** — fixed display title for the report.
- **`context`** — the same `general`/`expert` context as the top-level `AnalysisReport.context`.
- **`summary`** — `llmInterpretation.summary` verbatim, or a fixed placeholder (`"No LLM summary is available for this analysis."`) when the LLM stage did not complete.
- **`metricSections`** — see below.
- **`composite`** — see below.
- **`uiclipSummary`** — see below.
- **`recommendations`** — `llmInterpretation.recommendations` verbatim (empty list if the LLM stage did not complete).
- **`limitations`** — a fixed proxy-signal disclaimer, followed by `llmInterpretation.limitations` verbatim.
- **`closingNote`** — the same string as the top-level `AnalysisReport.note`, reused rather than re-derived, so the two never contradict each other.

## Metric Sections (`metricSections`)

Always exactly 7 entries, in this fixed order (mirrors [metric-catalog.md](../metrics/metric-catalog.md)). As of `schemaVersion: "2.0"`/`metricEngineVersion: "corrected-v4"`, the `visual-complexity`, `hicks-law`, and `whitespace-alignment` sections were removed and `elements-target-size` was reworked into `elements` — every metric backing those sections was classified Tier 3 ("Problematic") in [reliability-tiers.md](../metrics/reliability-tiers.md) and removed from `lucidui` entirely; see [metric-catalog.md](../metrics/metric-catalog.md#removed-metrics-tier-3-corrected-v4).

| # | `id` | Title | Backing `lucidui` data |
|---|---|---|---|
| 1 | `contrast` | Contrast | `raw.contrast`, `normalized.contrast` |
| 2 | `elements` | Detected Elements | `raw.elements` |
| 3 | `grouping` | Grouping (Estimated Group Count) | `raw.groups` |
| 4 | `text-density` | Text Density | `raw.textDensity`, `normalized.textDensity` |
| 5 | `colorfulness` | Colorfulness | `additionalSignals.colorfulness` |
| 6 | `fitts-law` | Fitts's Law (Index of Difficulty) | `additionalSignals.fittsFullIndexOfDifficulty` |
| 7 | `visual-balance` | Visual Balance | `additionalSignals.visualBalance` |

Each section:

```json
{
  "id": "contrast",
  "title": "Contrast",
  "category": "contrast",
  "rawDisplay": "1.27:1",
  "normalizedScore": 55.5,
  "explanation": "…",
  "evidencePaths": ["lucidui.raw.contrast.averageContrastRatio", "..."],
  "source": "WCAG 2.1 AA (4.5:1 normal text)",
  "isProxy": false
}
```

- **`rawDisplay`** — a pre-formatted string built from the same numeric value already in `lucidui.raw`/`lucidui.additionalSignals`; only the *string* is rounded, never the underlying value. Examples: Contrast `"1.27:1"`, Detected Elements `"185 elements"`, Text Density `"12.00%"`. When the backing raw value is `null` (e.g. no OCR regions detected), `rawDisplay` is the fixed string `"No data available"`.
- **`normalizedScore`** — copied from `lucidui.normalized` **only** for metrics `normalize_metrics_v2` actually normalizes (contrast, textDensity — see [scoring-and-normalization.md](../metrics/scoring-and-normalization.md)). For everything else (elements, grouping, colorfulness, Fitts's Law, visual balance) this is always `null` — no normalized score is invented for signals the engine never normalizes.
- **`explanation`** — see [Observation Matching](#observation-matching) below.
- **`evidencePaths`** — the `lucidui.*` JSON paths this section is built from, for traceability (and the same path style the LLM cites in `metricEvidence` — see [report-schema.md](report-schema.md)).
- **`source`** — the underlying metric's `source` string when the legacy engine's raw output includes one; `null` when it doesn't (e.g. `textDensity` has no `source` key upstream — left `null` rather than invented).
- **`isProxy`** — reflects the legacy engine's own `isProxyMetric` flag on that raw metric, when present; `false` otherwise. **This does not mean a metric without the flag isn't conceptually a proxy** — see each metric's "Proxy Status" in [metric-catalog.md](../metrics/metric-catalog.md) for the full picture. `isProxy` here is a narrow, mechanical passthrough of the engine's own flag, not a new judgment.

### Observation Matching

Every `llmInterpretation.observations[].metricEvidence` entry is a JSON path such as `"lucidui.raw.contrast.averageContrastRatio"` (see [report-schema.md](report-schema.md)). The builder matches these against each metric section using a fixed set of lowercase substring keywords (e.g. the `contrast` section matches any evidence path containing `"raw.contrast"` or `"normalized.contrast"`). One observation can legitimately populate more than one section's `explanation` if its evidence spans multiple metrics (e.g. an observation citing both `lucidui.raw.contrast` and `lucidui.raw.elements`). Matched observation text is used verbatim — never rewritten or summarized further.

If no observation's evidence matches a section — including whenever the LLM stage did not complete, since `observations` is then always empty — `explanation` falls back to the fixed string `"No LLM interpretation is linked to this metric."` rather than `null` or a scientific claim about the metric. No new LLM call is ever made to fill this gap.

## Composite (`composite`)

```json
{
  "rawDisplay": "47.8 / 100",
  "value": 47.8,
  "scoreName": "LucidUI Composite Signal Score",
  "context": "general",
  "explanation": "This composite score is a weighted signal summary of the metrics above, not a quality judgment — see docs/metrics/scoring-and-normalization.md."
}
```

`value` is `lucidui.weightedScore`, unchanged; `explanation` is a fixed disclaimer string, identical for every report — never a generated verdict.

## UIClip Summary Card (`uiclipSummary`)

A standalone card for UIClip's independent evaluation, present regardless of `uiclip.status`:

```json
{
  "status": "completed",
  "modelId": "biglab/uiclip_jitteredwebsites-2-224-paraphrased",
  "userDescription": "A checkout flow with a payment form",
  "rawScoreDisplay": "12.30",
  "scoreType": "Learned raw model score",
  "normalizedScoreDisplay": null,
  "comparableToLucidui": false,
  "comparabilityNote": "UIClip's raw score is not directly comparable to LucidUI's weighted composite score — the two use different scales and methods, and comparison has not been implemented yet (see ROADMAP.md Phase 6)."
}
```

- **`modelId`** — `uiclip.modelVersion` verbatim (`null` unless `status: completed`).
- **`userDescription`** — `uiclip.description`, but only when `uiclip.descriptionSource == "user"`; `null` for the `generic` fallback description, so the card never implies a user wrote something they didn't.
- **`rawScoreDisplay`** / **`scoreType`** — `null` unless a score actually exists; when it does, `scoreType` is always the fixed label `"Learned raw model score"`, never a manufactured quality label.
- **`normalizedScoreDisplay`** — `null` today, since `uiclip.normalizedQualityScore` is always `null` (no verified official normalization exists yet — see [uiclip-integration.md](../research/uiclip-integration.md)).
- **`comparableToLucidui`** — always `false`.
- **`comparabilityNote`** — always present, regardless of status; comparison between LucidUI and UIClip is Phase 6 and is never fabricated here.

## Related Documents

- [report-schema.md](report-schema.md) — the full `AnalysisReport` shape `presentation` is additive to.
- [docs/metrics/metric-catalog.md](../metrics/metric-catalog.md) — full detail on each metric section's purpose, method, and limitations.
- [docs/frontend/FRONTEND_GUIDE.md](../frontend/FRONTEND_GUIDE.md) — frontend rendering guidance for this section.
