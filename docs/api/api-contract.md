# API Contract

This is the target API contract for LucidUI. It describes the long-term, image-upload-based API that Phase 2+ implementation must match, and that the frontend can be built against using the mocked examples in [examples/](examples/). See [docs/api/report-schema.md](report-schema.md) and [docs/api/error-codes.md](error-codes.md) for the shapes referenced here.

All endpoints are versioned under `/api/v1`.

> **Phase 1 temporary deviation**: `POST /api/v1/analyses/single` is currently implemented as a **JSON-only mock endpoint** — it does not yet accept an uploaded image. See [Phase 1: Temporary JSON Mock Mode](#phase-1-temporary-json-mock-mode) below for the exact Phase 1 request/response shape. The multipart contract documented in the section immediately below remains the target for Phase 2, when real image upload and deterministic metrics land (see [ROADMAP.md](../../ROADMAP.md)).

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
| `run_llm` | boolean | No | Whether to run LLM interpretation. Defaults to `true`. |
| `run_uiclip` | boolean | No | Whether to run UIClip evaluation. Defaults to `true`. |

**Validation**:

- `image` must be present and decodable; unsupported MIME type returns `UNSUPPORTED_MEDIA_TYPE`; corrupt/undecodable bytes return `INVALID_IMAGE`; oversized files return `FILE_TOO_LARGE`.
- `context`, if provided, must be one of the documented allowed values, otherwise `INVALID_CONTEXT`.

**Success Response** (`200` or `207` for partial success): A single-analysis report matching [report-schema.md](report-schema.md), `mode: "single"`. See [examples/single-analysis-response.json](examples/single-analysis-response.json).

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

## Phase 1: Temporary JSON Mock Mode

This section documents the **actual, currently implemented** behavior of `POST /api/v1/analyses/single` during Phase 1. It is a deliberate, temporary simplification — no image is uploaded or processed, and every response is a realistic but fabricated mock. It will be replaced by the multipart contract documented above once Phase 2 (image upload and the deterministic metric engine) lands.

**Request Format**: `application/json` (not multipart).

**Request Body**:

```json
{
  "context": "general",
  "description": "A project management dashboard",
  "runLlm": true,
  "runUiclip": true
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `context` | string | No | `general` or `expert`. Defaults to `general`. Invalid values return `INVALID_CONTEXT` (422). |
| `description` | string | No | Free-text description. Trimmed; an empty/whitespace-only string is treated as absent. Drives `uiclip.descriptionSource` (`user` if present, `generic` if absent). |
| `runLlm` | boolean | No | Whether to include a mock LLM interpretation section. Defaults to `true`. |
| `runUiclip` | boolean | No | Whether to include a mock UIClip section. Defaults to `true`. |

**Success Response** (`200`): A single-analysis report matching [report-schema.md](report-schema.md), with all `lucidui`, `llmInterpretation`, `uiclip`, and `comparison` sections populated with mocked (not computed) values. `imageMetadata` is a fixed placeholder (`{"width": 1440, "height": 900, "format": "mock", "sizeBytes": 0}`) since no image is uploaded in Phase 1 — this differs from the real, decoded-image metadata shape Phase 2 will produce.

**Error Responses**: `INVALID_CONTEXT` (422), `VALIDATION_ERROR` (422, for malformed JSON or invalid field types), `ANALYSIS_NOT_FOUND` (404, for retrieval endpoints), `INTERNAL_ERROR` (500). `UNSUPPORTED_MEDIA_TYPE`, `FILE_TOO_LARGE`, and `INVALID_IMAGE` do not apply yet, since there is no file upload in Phase 1.

`GET /api/v1/analyses/{analysis_id}` and `GET /api/v1/analyses/{analysis_id}/raw` behave as documented above; in Phase 1, `/raw` returns the same stored report as the primary endpoint, since there is no separate raw-model payload yet.

`POST /api/v1/analyses/variants` is not implemented in Phase 1 (see [ROADMAP.md](../../ROADMAP.md) Phase 7).

## Notes

- In Phase 1–8, `analyses/{analysis_id}` retrieval is backed by an in-memory repository and will not persist across backend restarts. Durable persistence is Phase 9 — see [ROADMAP.md](../../ROADMAP.md).
- All error responses use the shared JSON error envelope defined in [error-codes.md](error-codes.md).
