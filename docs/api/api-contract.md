# API Contract

This is the target API contract for LucidUI. It describes the long-term, image-upload-based API that Phase 2+ implementation must match, and that the frontend can be built against using the mocked examples in [examples/](examples/). See [docs/api/report-schema.md](report-schema.md) and [docs/api/error-codes.md](error-codes.md) for the shapes referenced here.

All endpoints are versioned under `/api/v1`.

> **Phase 2B-2 status**: `POST /api/v1/analyses/single` now implements the full request/response contract documented below, with one real gap: `llmInterpretation` and `uiclip` are always `disabled` placeholders (per the statuses documented in [report-schema.md](report-schema.md)), since no LLM or UIClip integration exists yet (Phase 3/4/5, see [ROADMAP.md](../../ROADMAP.md)). `comparison.agreementLevel` is correspondingly always `unavailable`. `lucidui` is real, computed output from the deterministic metric engine — see [docs/metrics/scoring-and-normalization.md](../metrics/scoring-and-normalization.md). The `runLlm`/`runUiclip` request fields are accepted and type-validated but have no effect yet, since there is nothing for them to toggle.

---

## `GET /api/v1/health`

**Purpose**: Liveness/readiness check for the backend service.

**Request**: No parameters.

**Success Response** (`200`):

```json
{ "status": "ok", "version": "0.1.0" }
```

**Error Responses**: None expected; if the service cannot respond, the request fails at the infrastructure level rather than returning a JSON error body.

---

## `POST /api/v1/analyses/single`

**Purpose**: Run a full analysis (LucidUI metrics, optional LLM interpretation, optional UIClip evaluation, comparison) on one uploaded screenshot.

**Request Format**: `multipart/form-data`.

**Fields**:

| Field | Type | Required | Description |
|---|---|---|---|
| `image` | file | Yes | JPG, PNG, or WebP screenshot, max 20 MB. |
| `context` | string | No | Analysis context, e.g. `general` or `expert`. Defaults to `general`. |
| `description` | string | No | Free-text description of the interface, used as a `user` description source for UIClip. |
| `runLlm` | boolean | No | Whether to run LLM interpretation. Defaults to `true`. |
| `runUiclip` | boolean | No | Whether to run UIClip evaluation. Defaults to `true`. |

Field names use `camelCase` for consistency with the rest of this JSON API (this corrects an earlier draft of this document, which used `run_llm`/`run_uiclip`; no implementation ever shipped with the snake_case names).

**Validation**:

- `image` must be present and decodable; unsupported MIME type returns `UNSUPPORTED_MEDIA_TYPE`; corrupt/undecodable bytes return `INVALID_IMAGE`; oversized files return `FILE_TOO_LARGE`.
- `context`, if provided, must be one of the documented allowed values, otherwise `INVALID_CONTEXT`.

**Success Response** (`200`): A single-analysis report matching [report-schema.md](report-schema.md), `mode: "single"`, `status: "partial_success"` (deterministic metrics complete; LLM/UIClip are disabled placeholders — see the Phase 2B-2 status note above). The `lucidui` section reflects the deterministic metric engine's real output, including its own field names exactly as documented in [docs/metrics/metric-catalog.md](../metrics/metric-catalog.md) — note the current [examples/single-analysis-response.json](examples/single-analysis-response.json) predates this implementation and does not yet match it field-for-field; treat the live API and [report-schema.md](report-schema.md)'s status/field descriptions as authoritative until that example is regenerated. `207` (partial success as an HTTP status) is not currently used — partial success is signaled via the `status` field at `200`, not the HTTP status code.

**Error Responses**: `UNSUPPORTED_MEDIA_TYPE` (415), `FILE_TOO_LARGE` (413), `INVALID_IMAGE` (422), `INVALID_CONTEXT` (422), `ANALYSIS_FAILED` (500), `INTERNAL_ERROR` (500). See [error-codes.md](error-codes.md).

---

## `POST /api/v1/analyses/variants`

**Purpose**: Run independent analyses on two screenshots (A and B) and report relative deltas between them.

**Request Format**: `multipart/form-data`.

**Fields**:

| Field | Type | Required | Description |
|---|---|---|---|
| `imageA` | file | Yes | JPG, PNG, or WebP screenshot, max 20 MB. |
| `imageB` | file | Yes | JPG, PNG, or WebP screenshot, max 20 MB. |
| `context` | string | No | Shared analysis context applied to both images. Defaults to `general`. |
| `descriptionA` | string | No | Free-text description for image A. |
| `descriptionB` | string | No | Free-text description for image B. |
| `run_llm` | boolean | No | Whether to run LLM interpretation for both images. Defaults to `true`. |
| `run_uiclip` | boolean | No | Whether to run UIClip evaluation for both images. Defaults to `true`. |

**Validation**: Same per-image rules as `/analyses/single`, applied independently to `imageA` and `imageB`. A validation failure on either image is reported against that image specifically.

**Success Response** (`200` or `207` for partial success): A variant-comparison report, `mode: "variants"`, containing independent reports for A and B plus relative deltas. See [examples/variant-analysis-response.json](examples/variant-analysis-response.json).

**Error Responses**: Same set as `/analyses/single`, applied per-image where relevant. See [error-codes.md](error-codes.md).

---

## `GET /api/v1/analyses/{analysis_id}`

**Purpose**: Retrieve a previously computed analysis report by ID.

**Request**: Path parameter `analysis_id` (UUID).

**Success Response** (`200`): The stored report matching [report-schema.md](report-schema.md).

**Error Responses**: `ANALYSIS_NOT_FOUND` (404), `INTERNAL_ERROR` (500).

---

## `GET /api/v1/analyses/{analysis_id}/raw`

**Purpose**: Retrieve the raw, unfiltered metric/model output for a previously computed analysis, for debugging and research use (see [docs/frontend/component-contracts.md](../frontend/component-contracts.md) `RawJsonViewer`).

**Request**: Path parameter `analysis_id` (UUID).

**Success Response** (`200`): The full raw JSON payload underlying the report, including any fields not surfaced in the primary report shape.

**Error Responses**: `ANALYSIS_NOT_FOUND` (404), `INTERNAL_ERROR` (500).

---

## Current Implementation Notes (Phase 2B-2)

- `image_metadata` in a live report uses the real decoded-image fields: `width`, `height`, `format` (`jpeg`/`png`/`webp`), `aspectRatio`, `orientation` (`landscape`/`portrait`/`square`), `fileSizeBytes` — not the illustrative `fileName`/`widthPx`/`heightPx`/`colorMode` shape shown in [examples/single-analysis-response.json](examples/single-analysis-response.json), which predates this implementation.
- `analysisId` **is now persisted**: a report returned by `POST /analyses/single` can immediately be retrieved via `GET /api/v1/analyses/{analysisId}` and `/raw` (both return the identical stored report — there is no separate raw payload beyond what `lucidui.raw` already carries).
- `POST /api/v1/analyses/variants` is not implemented yet (see [ROADMAP.md](../../ROADMAP.md) Phase 7).

## Notes

- In Phase 1–8, `analyses/{analysis_id}` retrieval is backed by an in-memory repository and will not persist across backend restarts. Durable persistence is Phase 9 — see [ROADMAP.md](../../ROADMAP.md).
- All error responses use the shared JSON error envelope defined in [error-codes.md](error-codes.md).
