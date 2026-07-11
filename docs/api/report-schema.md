# Report Schema

This document defines the planned structure of an analysis report — the primary response shape returned by `/api/v1/analyses/single`, `/api/v1/analyses/variants`, and `/api/v1/analyses/{analysis_id}`. See [api-contract.md](api-contract.md) for endpoints and [examples/](examples/) for realistic mocked instances.

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
  "note": ""
}
```

- **`schemaVersion`** — version of this report shape. Increment on any breaking structural change; see [ADR-006](../architecture/decisions/ADR-006-frontend-backend-independence.md).
- **`analysisId`** — UUID identifying this stored analysis.
- **`mode`** — `"single"` or `"variants"`. Variant reports nest two single-mode-shaped reports (for A and B) plus a delta section — see [api-contract.md](api-contract.md#post-apiv1analysesvariants).
- **`context`** — the analysis context used (e.g. `general`, `expert`).
- **`status`** — overall analysis status (see below).
- **`imageMetadata`** — dimensions, format, file size, and any other non-content metadata about the decoded image. Never includes the raw image bytes.
- **`lucidui`** — the deterministic metric engine output: raw metrics, normalized signals, composite signal score. See [docs/metrics/metric-catalog.md](../metrics/metric-catalog.md) and [scoring-and-normalization.md](../metrics/scoring-and-normalization.md).
- **`llmInterpretation`** — the LLM's structured interpretation of `lucidui`'s output, including a status, summary, and evidence-linked observations.
- **`uiclip`** — the UIClip evaluator's output: status, preference score, and model-generated description.
- **`comparison`** — the Comparison Engine's output: shared findings, LucidUI-only findings, UIClip-only findings, score difference, and agreement level.
- **`timings`** — per-stage and total duration in milliseconds.
- **`note`** — optional human-readable note about the analysis (e.g. explaining a partial-success condition).

## Analysis Statuses

| Status | Meaning |
|---|---|
| `queued` | Analysis has been accepted but has not started processing. |
| `processing` | Analysis is actively running. |
| `completed` | All requested stages completed successfully. |
| `partial_success` | Deterministic metrics completed, but at least one optional stage (LLM or UIClip) did not complete (`disabled`, `unavailable`, `fallback`, or `failed`). |
| `failed` | The deterministic metric engine itself failed; no usable report was produced. |

## UIClip Statuses (`uiclip.status`)

| Status | Meaning |
|---|---|
| `completed` | UIClip evaluation ran and produced a result. |
| `disabled` | UIClip evaluation was intentionally turned off for this request (`run_uiclip: false`). |
| `unavailable` | UIClip evaluation was requested but could not run (e.g. model not loaded). |
| `failed` | UIClip evaluation was attempted and errored. |

## LLM Statuses (`llmInterpretation.status`)

| Status | Meaning |
|---|---|
| `completed` | LLM interpretation ran and produced a result. |
| `disabled` | LLM interpretation was intentionally turned off for this request (`run_llm: false`). |
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

A variant-comparison report (`mode: "variants"`) wraps two single-mode reports plus a delta section:

```json
{
  "schemaVersion": "1.0",
  "analysisId": "uuid",
  "mode": "variants",
  "context": "general",
  "status": "completed",
  "variantA": { "...single-analysis report shape..." },
  "variantB": { "...single-analysis report shape..." },
  "deltas": {},
  "timings": {},
  "note": ""
}
```

`deltas` reports relative differences between `variantA` and `variantB`'s `lucidui`, `llmInterpretation`, and `uiclip` sections (e.g. composite score difference, per-metric differences). See [examples/variant-analysis-response.json](examples/variant-analysis-response.json).

## Related Documents

- [api-contract.md](api-contract.md) — endpoints that return this shape.
- [error-codes.md](error-codes.md) — error envelope used when a report cannot be produced.
- [examples/](examples/) — realistic mocked instances of this schema.
