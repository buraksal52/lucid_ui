# API Contract

This is the target API contract for LucidUI. It describes the long-term, image-upload-based API that Phase 2+ implementation must match, and that the frontend can be built against using the mocked examples in [examples/](examples/). See [docs/api/report-schema.md](report-schema.md) and [docs/api/error-codes.md](error-codes.md) for the shapes referenced here.

All endpoints are versioned under `/api/v1`.

> **Phase 2A temporary deviation**: `POST /api/v1/analyses/single` now accepts a real `multipart/form-data` image upload (superseding Phase 1's JSON-only mock mode) and validates/decodes it in memory, but it does not yet run any deterministic-metric, LLM, or UIClip stage, so it cannot yet return a full analysis report. See [Phase 2A: Temporary Image-Accepted Response](#phase-2a-temporary-image-accepted-response) below for the exact currently-implemented request/response shape. The full report contract documented in the section immediately below remains the target for Phase 2B onward, when the deterministic metric engine lands (see [ROADMAP.md](../../ROADMAP.md)).

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

**Success Response** (`200` or `207` for partial success): A single-analysis report matching [report-schema.md](report-schema.md), `mode: "single"`. See [examples/single-analysis-response.json](examples/single-analysis-response.json). **As of Phase 2A, this is not yet implemented** — see [Phase 2A: Temporary Image-Accepted Response](#phase-2a-temporary-image-accepted-response) for the actual current response.

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

## Phase 2A: Temporary Image-Accepted Response

This section documents the **actual, currently implemented** behavior of `POST /api/v1/analyses/single` during Phase 2A. The endpoint now accepts a real `multipart/form-data` image upload and validates/decodes it entirely in memory (see [docs/architecture/privacy-model.md](../architecture/privacy-model.md) — the file is never written to disk), but no deterministic-metric, LLM, or UIClip stage runs yet, so the response is a small, temporary "accepted" shape rather than a full analysis report. It will be replaced by the full report contract documented above once Phase 2B (the deterministic metric engine) lands.

**Request Format**: `multipart/form-data`, exactly as documented above (`image` required; `context`, `description`, `runLlm`, `runUiclip` optional). `description`, `runLlm`, and `runUiclip` are accepted and type-validated but currently unused — no LLM or UIClip stage exists yet to consume them.

**Success Response** (`200`):

```json
{
  "analysisId": "uuid",
  "status": "accepted",
  "imageMetadata": {
    "width": 1440,
    "height": 900,
    "format": "png",
    "aspectRatio": 1.6,
    "orientation": "landscape",
    "fileSizeBytes": 284213
  },
  "message": "Image successfully validated and decoded."
}
```

| Field | Type | Description |
|---|---|---|
| `analysisId` | string (UUID) | Identifies this validation/decode event. **Not currently persisted** — retrieving it via `GET /api/v1/analyses/{analysisId}` returns `ANALYSIS_NOT_FOUND` until Phase 2B's pipeline populates the repository. |
| `status` | string | Always `"accepted"` in Phase 2A. Distinct from the full `AnalysisStatus` enum in [report-schema.md](report-schema.md), which describes multi-stage pipeline completion that does not exist yet. |
| `imageMetadata` | object | `width`, `height`, `format` (`jpeg`/`png`/`webp`), `aspectRatio`, `orientation` (`landscape`/`portrait`/`square`), `fileSizeBytes` — all derived from the decoded image, never from pixel content. |
| `message` | string | Human-readable confirmation. |

**Error Responses**: `UNSUPPORTED_MEDIA_TYPE` (415), `FILE_TOO_LARGE` (413), `INVALID_IMAGE` (422, covers empty uploads, corrupted bytes, and file-signature mismatches), `INVALID_CONTEXT` (422), `VALIDATION_ERROR` (422, missing `image` field or invalid field types), `INTERNAL_ERROR` (500).

`GET /api/v1/analyses/{analysis_id}` and `GET /api/v1/analyses/{analysis_id}/raw` are unchanged from Phase 1 (in-memory repository, `ANALYSIS_NOT_FOUND` for unknown IDs); they currently have nothing to retrieve since Phase 2A does not persist its response — see above.

`POST /api/v1/analyses/variants` is not implemented yet (see [ROADMAP.md](../../ROADMAP.md) Phase 7).

## Notes

- In Phase 1–8, `analyses/{analysis_id}` retrieval is backed by an in-memory repository and will not persist across backend restarts. Durable persistence is Phase 9 — see [ROADMAP.md](../../ROADMAP.md).
- All error responses use the shared JSON error envelope defined in [error-codes.md](error-codes.md).
