# Report Schema

This document defines the structure of an analysis report — the response shape returned by `POST /api/v1/analyses/single`, `GET /api/v1/analyses/{analysisId}`, and `GET /api/v1/analyses/{analysisId}/raw` (all real/implemented today), plus the variant-comparison envelope returned by `POST /api/v1/analyses/variants` (Phase 7, also real/implemented today) — see the "Variant-Analysis Report Structure" section below and [api-contract.md](api-contract.md) for endpoints. See [examples/single-analysis-response.json](examples/single-analysis-response.json) and [examples/variant-analysis-response.json](examples/variant-analysis-response.json) for real, captured instances of each shape (not hand-written approximations).

## Single-Analysis Report Structure

```json
{
  "schemaVersion": "1.0",
  "analysisId": "uuid",
  "mode": "single",
  "context": "general",
  "status": "completed",
  "imageMetadata": {},
  "lucidui": {},
  "llmInterpretation": {},
  "uiclip": {},
  "comparison": {},
  "timings": {},
  "note": "",
  "presentation": {}
}
```

- **`schemaVersion`** — version of this report shape. Increment on any breaking structural change; see [ADR-006](../architecture/decisions/ADR-006-frontend-backend-independence.md).
- **`analysisId`** — UUID identifying this stored analysis.
- **`mode`** — always `"single"` today; `"variants"` is reserved for the not-yet-implemented variant-comparison endpoint — see [api-contract.md](api-contract.md) and "Variant-Analysis Report Structure" below.
- **`context`** — the analysis context used (e.g. `general`, `expert`).
- **`status`** — overall analysis status (see below).
- **`imageMetadata`** — dimensions, format, file size, and any other non-content metadata about the decoded image. Never includes the raw image bytes.
- **`lucidui`** — the deterministic metric engine output: raw metrics, normalized signals, composite signal score. See [docs/metrics/metric-catalog.md](../metrics/metric-catalog.md) and [scoring-and-normalization.md](../metrics/scoring-and-normalization.md).
- **`llmInterpretation`** — the LLM's structured interpretation of `lucidui`'s output, including a status, summary, and evidence-linked observations.
- **`uiclip`** — the UIClip evaluator's output: status, preference score, and model-generated description.
- **`comparison`** — the Comparison Engine's output: shared findings, LucidUI-only findings, UIClip-only findings, score difference, and agreement level.
- **`timings`** — per-stage and total duration in milliseconds.
- **`note`** — optional human-readable note about the analysis (e.g. explaining a partial-success condition).
- **`presentation`** — additive, backward-compatible: a ready-to-render view over `lucidui`, `llmInterpretation`, and `uiclip` (fixed-order metric sections, a composite summary, a UIClip summary card, recommendations, limitations). Computed once from the sections above — no metric is recomputed, no provider is called again. The frontend should render this section directly rather than re-deriving metric meaning, field mapping, or scores itself. See [presentation-schema.md](presentation-schema.md).

## Analysis Statuses

| Status | Meaning |
|---|---|
| `queued` | Reserved for a future async/job-based flow. **Never returned today** — `POST /analyses/single` is fully synchronous; there is no job queue or polling endpoint. |
| `processing` | Reserved for a future async/job-based flow. **Never returned today**, for the same reason. |
| `completed` | All requested stages (LLM, UIClip) actually completed. **The only "everything worked" value returned today.** |
| `partial_success` | Deterministic metrics completed, but at least one requested optional stage (LLM or UIClip) did not (`disabled`, `unavailable`, `fallback`, or `failed`). **Regularly returned today** (e.g. `runLlm: false`, or a misconfigured/unreachable provider). |
| `failed` | The deterministic metric engine itself failed. **Never actually appears in a response body** — if the metric engine fails, the backend raises before any report is constructed, and the request returns the `ANALYSIS_FAILED` HTTP error envelope instead (see [error-codes.md](error-codes.md)) rather than a `200` body with `status: "failed"`. Kept for schema completeness; drive failure-state UI off the HTTP error, not this value. |

**In practice, `POST /analyses/single` only ever returns `completed` or `partial_success` in a `200` body.** Do not build frontend logic (e.g. a polling loop) around `queued`/`processing` — there is nothing that produces them.

## UIClip Statuses (`uiclip.status`)

| Status | Meaning |
|---|---|
| `completed` | UIClip evaluation ran and produced a result. |
| `disabled` | UIClip evaluation was intentionally turned off for this request (`runUiclip: false`). |
| `unavailable` | UIClip evaluation was requested but could not run (e.g. model not loaded). |
| `failed` | UIClip evaluation was attempted and errored. |

## LLM Statuses (`llmInterpretation.status`)

| Status | Meaning |
|---|---|
| `completed` | LLM interpretation ran and produced a result. |
| `disabled` | LLM interpretation was intentionally turned off for this request (`runLlm: false`). |
| `unavailable` | LLM interpretation was requested but the provider could not be reached/configured. |
| `fallback` | The primary LLM provider failed and a fallback path was used (see [ROADMAP.md](../../ROADMAP.md) Phase 3). |
| `failed` | LLM interpretation was attempted and errored, with no fallback available. |

## Description Sources (`uiclip.descriptionSource`, and anywhere a description is attached)

| Source | Meaning |
|---|---|
| `user` | The description was typed by the person uploading the screenshot. |
| `generic` | A placeholder/default description was used because none was provided. |
| `generated` | The description was produced by an automated description-generation model. |

`generated` must not be used until a real description-generation model exists in the system — see [CLAUDE.md](../../CLAUDE.md) and [docs/product/terminology.md](../product/terminology.md).

## Variant-Analysis Report Structure

Returned by `POST /api/v1/analyses/variants` (Phase 7). See [examples/variant-analysis-response.json](examples/variant-analysis-response.json) for a real, captured instance (mock providers, two synthetic images).

```json
{
  "schemaVersion": "1.0",
  "analysisId": "uuid",
  "mode": "variants",
  "context": "general",
  "status": "completed",
  "variantA": { "...single-analysis report shape, see above..." },
  "variantB": { "...single-analysis report shape, see above..." },
  "deltas": {
    "compositeScoreDelta": 0.0,
    "compositeScoreDeltaDisplay": "0.00",
    "uiclipRawScoreDelta": 0.0,
    "uiclipRawScoreDeltaDisplay": "0.00",
    "metricDeltas": [
      {
        "id": "contrast",
        "title": "Contrast",
        "category": "contrast",
        "normalizedScoreDelta": 0.0,
        "rawDisplayA": "No data available",
        "rawDisplayB": "No data available",
        "direction": "equal"
      }
    ],
    "note": "Deltas are computed as variant B minus variant A, ..."
  },
  "timings": { "totalMs": 46, "variantAMs": 45, "variantBMs": 40, "deltasMs": 0 },
  "note": ""
}
```

- **`variantA`**/**`variantB`** — each a complete, standalone `AnalysisReport` — the exact same shape `POST /analyses/single` returns, including its own `presentation`. Each is computed by the same, unmodified single-analysis pipeline (no cross-influence between the two images) and independently persisted, so `GET /api/v1/analyses/{analysisId}` also resolves each variant's own `analysisId`. There is no separate `GET` endpoint for the outer variant envelope's own `analysisId`.
- **`deltas`** — relative differences between `variantA` and `variantB`, computed once, server-side, from each variant's already-computed `presentation`/`uiclip` output (see [presentation-schema.md](presentation-schema.md)); the frontend renders these values as-is and never computes or formats a delta itself.
  - **`compositeScoreDelta`**/**`compositeScoreDeltaDisplay`** — variant B's `presentation.composite.value` minus variant A's, plus a pre-formatted signed display string. Always present (the composite score is never null).
  - **`uiclipRawScoreDelta`**/**`uiclipRawScoreDeltaDisplay`** — variant B's `uiclip.qualityScore` minus variant A's (the raw model score, not `normalizedQualityScore`, which is always `null` — see "UIClip Evaluation" in [api-contract.md](api-contract.md)). `null`/`"No data available"` whenever either variant's UIClip stage did not complete.
  - **`metricDeltas`** — one entry per fixed `presentation.metricSections` entry (same 10, same order, as a single-analysis report). `normalizedScoreDelta` is `null` whenever either variant has no normalized score for that metric (several metric sections never have one, by design — see [presentation-schema.md](presentation-schema.md)). `rawDisplayA`/`rawDisplayB` are each variant's already-formatted `presentation.metricSections[].rawDisplay`, passed through unchanged. `direction` is `"higher"`/`"lower"`/`"equal"`/`"not_available"` — deliberately not `"better"`/`"worse"`, per [CLAUDE.md](../../CLAUDE.md) ("Flashlight, Not a Judge").
- **`timings`** — `totalMs` (wall-clock for the whole variant request), `variantAMs`/`variantBMs` (each variant's own `timings.totalMs`, computed concurrently, not additively), `deltasMs` (time spent building `deltas` only).
- **`status`** — `completed` only when both `variantA.status` and `variantB.status` are `completed`; otherwise `partial_success`, using the same semantics as [single-analysis `status`](#analysis-statuses).
- **`note`** — a fixed, non-verdict disclaimer that variant A and variant B were analyzed independently and that deltas describe relative differences only.

## Related Documents

- [api-contract.md](api-contract.md) — endpoints that return this shape.
- [error-codes.md](error-codes.md) — error envelope used when a report cannot be produced.
- [presentation-schema.md](presentation-schema.md) — the ready-to-render `presentation` field's full schema.
- [examples/single-analysis-response.json](examples/single-analysis-response.json), [examples/single-analysis-partial-success-response.json](examples/single-analysis-partial-success-response.json) — real, captured instances of this schema (`completed` and `partial_success`).
