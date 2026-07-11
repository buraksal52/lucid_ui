# Analysis Pipeline

This document walks through the planned stages of a single-image analysis request, from upload to final report. See [ARCHITECTURE.md](../../ARCHITECTURE.md) for the high-level diagram.

## Stages

1. **Validation** — Check MIME type (JPG, PNG, WebP only) and file size (20 MB limit, see [ADR-002](decisions/ADR-002-in-memory-image-processing.md)). Reject with `UNSUPPORTED_MEDIA_TYPE` or `FILE_TOO_LARGE` before any decoding happens.
2. **In-Memory Decoding** — Decode the validated bytes into an in-memory image object. The file is never written to disk in the default flow. If decoding fails, return `INVALID_IMAGE`.
3. **LucidUI Metric Engine** (parallel branch) — Run classical CV, OCR, and proxy-metric computations against the decoded image. Produces raw metrics, normalized signals, and a composite signal score. See [docs/metrics/metric-catalog.md](../metrics/metric-catalog.md).
4. **UIClip Evaluator** (parallel branch, optional via `run_uiclip`) — Run the UIClip model against the decoded image plus an available description. Produces a preference score and model-based description. See [docs/research/uiclip-integration.md](../research/uiclip-integration.md). If disabled or unavailable, the pipeline records that status and continues.
5. **LLM Interpretation** (optional via `run_llm`) — Send only the deterministic metric JSON from stage 3 to the LLM provider. The LLM never receives the raw image or the UIClip output. Produces observations with metric evidence. See [ADR-003](decisions/ADR-003-json-only-llm-input.md).
6. **Comparison Engine** — Compares the LLM interpretation of LucidUI's metrics against the UIClip result to produce shared findings, LucidUI-only findings, UIClip-only findings, and an agreement level. Only runs if both branches produced usable output; otherwise the report notes a partial comparison.
7. **Report Assembly** — Combines image metadata, LucidUI output, LLM interpretation, UIClip output, comparison result, and stage timings into the final report shape defined in [docs/api/report-schema.md](../api/report-schema.md).

## Partial Failure Handling

Each optional stage (UIClip, LLM) can independently be `completed`, `disabled`, `unavailable`, `fallback` (LLM only), or `failed`, without failing the whole request. If the deterministic metric engine itself fails, the overall analysis status is `failed`. If deterministic metrics succeed but an optional stage does not, overall status is `partial_success`. See [docs/api/report-schema.md](../api/report-schema.md) for the full status enum.

## Variant Comparison

A variant-comparison request (`/api/v1/analyses/variants`) runs the full pipeline above independently and concurrently for image A and image B, then computes relative deltas between their two reports. It does not share intermediate state between the two runs. See [docs/api/api-contract.md](../api/api-contract.md).
