# Analysis Pipeline

This document walks through the real stages of a single-image analysis request, from upload to final report, as implemented in `AnalysisService.create_single_analysis` (`backend/app/services/analysis_service.py`). See [ARCHITECTURE.md](../../ARCHITECTURE.md) for the high-level diagram.

## Stages

All stages below run **sequentially, synchronously, within one `POST /api/v1/analyses/single` request/response cycle** — there is no parallel/concurrent execution between stages, no background job, and no progress streamed back mid-request; the frontend receives the full report only when the whole call returns. See [docs/frontend/ui-states.md](../frontend/ui-states.md).

1. **Validation** — Check MIME type (`image/jpeg`, `image/png`, `image/webp` only) and file size (20 MB limit, see [ADR-002](decisions/ADR-002-in-memory-image-processing.md)). Reject with `UNSUPPORTED_MEDIA_TYPE` or `FILE_TOO_LARGE` before any decoding happens.
2. **In-Memory Decoding** — Decode the validated bytes into an in-memory image object (`DecodedImage`: both an OpenCV array and a Pillow image, from the same bytes). The file is never written to disk. If decoding fails, return `INVALID_IMAGE`.
3. **LucidUI Metric Engine** — Run classical CV, OCR, and proxy-metric computations against the decoded image (`app.metrics.MetricEngine`, exactly once). Produces raw metrics, normalized signals, and a weighted composite signal score. See [docs/metrics/metric-catalog.md](../metrics/metric-catalog.md). If this stage itself fails (e.g. OCR execution error), the request returns the `ANALYSIS_FAILED` HTTP error — no report is constructed, and there is no `status: "failed"` report body (see [docs/api/report-schema.md](../api/report-schema.md#analysis-statuses)).
4. **LLM Interpretation** (optional via `runLlm`, runs next, after the metric engine) — Send only the deterministic metric JSON from stage 3 to the configured LLM provider (`mock` or `gemini`). The LLM never receives the raw image. Produces a summary and evidence-linked observations. See [ADR-003](decisions/ADR-003-json-only-llm-input.md). If disabled/unavailable/failed, the pipeline records that status and continues — the rest of the report is still returned.
5. **UIClip Evaluator** (optional via `runUiclip`, runs last, independently of stage 4 — neither sees the other's output) — Run the configured UIClip provider (`mock` or `huggingface`) against the decoded image plus the resolved description. Produces a raw score and (for `mock`) fixed observations. See [docs/research/uiclip-integration.md](../research/uiclip-integration.md). If disabled/unavailable/failed, the pipeline records that status and continues.
6. **Presentation Build** — Format the already-computed results from stages 3–5 into the ready-to-render `presentation` field (`app.presentation.report_builder`) — fixed-order metric sections, a composite summary, a UIClip summary card, evidence-linked explanations. Pure formatting: no metric is recomputed, no provider is called again. See [docs/api/presentation-schema.md](../api/presentation-schema.md).
7. **Report Assembly and Persistence** — Combines image metadata, LucidUI output, LLM interpretation, UIClip output, an always-`"unavailable"` comparison placeholder (see below), timings, and `presentation` into the final report shape ([docs/api/report-schema.md](../api/report-schema.md)), then persists it (in-memory repository) so it can be retrieved later via `GET /api/v1/analyses/{analysisId}`.

## Comparison Engine — not implemented (Phase 6)

There is no Comparison Engine yet. `comparison.agreementLevel` is always `"unavailable"`, every finding list is always empty, and `comparison.interpretation` is a fixed sentence stating that comparison hasn't been computed. LucidUI's metrics/LLM interpretation and UIClip's evaluation are returned as two independent results in the same report with no synthesis between them — see [ADR-004](decisions/ADR-004-uiclip-independent-evaluator.md) and [docs/frontend/FRONTEND_GUIDE.md](../frontend/FRONTEND_GUIDE.md) ("LucidUI vs. UIClip: Two Independent Results, Not a Verdict").

## Partial Failure Handling

Each optional stage (LLM, UIClip) can independently be `completed`, `disabled`, `unavailable`, `fallback` (LLM only, reserved/currently unused — no fallback path is implemented), or `failed`, without failing the whole request. If deterministic metrics succeed but an optional stage does not, overall `status` is `"partial_success"`. If the deterministic metric engine itself fails, the request never reaches report assembly at all — it returns the `ANALYSIS_FAILED` HTTP error instead of any report body (there is no `status: "failed"` report in practice). See [docs/api/report-schema.md](../api/report-schema.md#analysis-statuses) for the full status enum and which values are actually reachable.

## Variant Comparison — not implemented (Phase 7)

`POST /api/v1/analyses/variants` does not exist yet. The intended design (documented for planning purposes only) is to run the pipeline above independently for image A and image B and compute relative deltas between their two reports, without sharing intermediate state — see [docs/api/api-contract.md](../api/api-contract.md) and [docs/api/report-schema.md](../api/report-schema.md#variant-analysis-report-structure--planned-not-implemented-phase-7).
