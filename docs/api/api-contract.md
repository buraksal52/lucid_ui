# API Contract

This is the API contract for LucidUI's implemented endpoints, and the reference the frontend should be built against — matching the live backend field-for-field. [examples/single-analysis-response.json](examples/single-analysis-response.json) is a real, captured response (mock LLM/UIClip providers, deterministic synthetic input), not a hand-written illustrative mock — treat it as authoritative alongside [report-schema.md](report-schema.md) and [presentation-schema.md](presentation-schema.md).

All endpoints are versioned under `/api/v1`. Base URL during local development: `http://localhost:8000` — see [docs/frontend/FRONTEND_GUIDE.md](../frontend/FRONTEND_GUIDE.md) ("Running the Backend Locally") for how to start it.

> **Implementation status**: `POST /api/v1/analyses/single` implements the full request/response contract documented below. `lucidui` (deterministic metrics), `llmInterpretation`, `uiclip`, and the additive `presentation` field (see [presentation-schema.md](presentation-schema.md)) are all real, computed output — not scaffolding — regardless of which provider is configured. `POST /api/v1/analyses/variants` (Phase 7, see the dedicated section below) is also real: it runs `/analyses/single`'s exact pipeline on two images concurrently and returns both reports plus computed `deltas`. One thing remains unimplemented: `comparison.agreementLevel` is always `"unavailable"` (agreement/discrepancy computation between LucidUI and UIClip is Phase 6, see [ROADMAP.md](../../ROADMAP.md)) — this is unrelated to variant comparison, which compares two *images*, not the two evaluators. Provider selection is configuration-driven, not a code/phase gate: `LLM_PROVIDER=mock` (default, no API key) or `gemini` (real, needs `GEMINI_API_KEY`); `UICLIP_PROVIDER=mock` (default, no download) or `huggingface` (real, loads the official BIG Lab checkpoint, needs a real submitted `description` — see "UIClip Evaluation" below). The response *shape* is identical regardless of which provider is configured; only the values inside `status`/`provider`/`modelId`-type fields differ.

---

## `GET /api/v1/health`

**Purpose**: Liveness/readiness check for the backend service.

**Request**: No parameters.

**Success Response** (`200`):

```json
{ "status": "ok", "service": "lucidui-backend", "version": "0.1.0" }
```

**Error Responses**: None expected; if the service cannot respond, the request fails at the infrastructure level rather than returning a JSON error body.

---

## `POST /api/v1/analyses/single`

**Purpose**: Run a full analysis (LucidUI metrics, optional LLM interpretation, optional UIClip evaluation) on one uploaded screenshot, and return a ready-to-render report.

**Request Format**: `multipart/form-data`.

**Fields**:

| Field | Type | Required | Description |
|---|---|---|---|
| `image` | file | Yes | JPG, PNG, or WebP screenshot, max 20 MB (`MAX_UPLOAD_SIZE_BYTES`). |
| `context` | string | No | Analysis context: `general` or `expert`. Defaults to `general`. Any other value returns `INVALID_CONTEXT`. |
| `description` | string | No | Free-text description of the interface. A non-blank value becomes `uiclip.descriptionSource: "user"`; omitted/blank falls back to the documented generic description (`descriptionSource: "generic"`). |
| `runLlm` | boolean | No | Whether to run LLM interpretation for this request. Defaults to `true`. `false` → `llmInterpretation.status: "disabled"`. |
| `runUiclip` | boolean | No | Whether to run UIClip evaluation for this request. Defaults to `true`. `false` → `uiclip.status: "disabled"`, `uiclip.enabled: false`. |

All field names are `camelCase`. A minimal valid request needs only the `image` file part — everything else has a default.

**Validation**:

- `image` must be present (missing → `VALIDATION_ERROR`, 422) and decodable: unsupported MIME type → `UNSUPPORTED_MEDIA_TYPE` (415); corrupt/empty/undecodable bytes → `INVALID_IMAGE` (422); oversized file → `FILE_TOO_LARGE` (413).
- `context`, if provided, must be one of the allowed values, otherwise `INVALID_CONTEXT` (422).
- `runLlm`/`runUiclip`, if provided, must parse as booleans (form values like `"true"`/`"false"` are accepted), otherwise `VALIDATION_ERROR` (422).

**Success Response** (`200`): A single-analysis report matching [report-schema.md](report-schema.md), `mode: "single"`. `status` is `"completed"` only when every requested optional stage (LLM, UIClip) actually completed; it is `"partial_success"` whenever any requested stage was disabled, unavailable, or failed — see [report-schema.md](report-schema.md#analysis-statuses). There is no `207` response — partial success is signaled entirely via the `status` field at HTTP `200`.

**Error Responses**: `VALIDATION_ERROR` (422), `UNSUPPORTED_MEDIA_TYPE` (415), `FILE_TOO_LARGE` (413), `INVALID_IMAGE` (422), `INVALID_CONTEXT` (422), `ANALYSIS_FAILED` (500), `INTERNAL_ERROR` (500). See [error-codes.md](error-codes.md).

---

## `GET /api/v1/analyses/{analysisId}`

**Purpose**: Retrieve a previously computed analysis report by ID.

**Request**: Path parameter `analysisId` (UUID, e.g. `3f9c6b1a-2e6b-4a3a-9a3a-1a2b3c4d5e6f`).

**Success Response** (`200`): The exact stored report, byte-for-byte identical to what `POST /analyses/single` originally returned (including `presentation`) — matching [report-schema.md](report-schema.md).

**Error Responses**: `ANALYSIS_NOT_FOUND` (404), `INTERNAL_ERROR` (500).

---

## `GET /api/v1/analyses/{analysisId}/raw`

**Purpose**: Retrieve the same stored analysis report for debugging/research use (see [docs/frontend/component-contracts.md](../frontend/component-contracts.md) `RawJsonViewer`).

**Request**: Path parameter `analysisId` (UUID).

**Success Response** (`200`): Currently identical to `GET /analyses/{analysisId}` — there is no separate raw payload beyond what `lucidui.raw` already carries inside the same report object. Do not assume a different shape than the primary report.

**Error Responses**: `ANALYSIS_NOT_FOUND` (404), `INTERNAL_ERROR` (500).

---

## `POST /api/v1/analyses/variants`

**Purpose**: Run LucidUI's full single-analysis pipeline on two uploaded screenshots ("variant A" and "variant B"), concurrently and fully independently, and return both reports plus relative deltas between them. See [examples/variant-analysis-response.json](examples/variant-analysis-response.json) for a real, captured response (mock providers), and [report-schema.md](report-schema.md#variant-analysis-report-structure) for the full shape.

**Request Format**: `multipart/form-data`.

**Fields**:

| Field | Type | Required | Description |
|---|---|---|---|
| `imageA` | file | Yes | Variant A screenshot — same constraints as `image` on `/analyses/single` (JPG/PNG/WebP, max 20 MB). |
| `imageB` | file | Yes | Variant B screenshot — same constraints. |
| `context` | string | No | Shared analysis context for both variants: `general` or `expert`. Defaults to `general`. |
| `descriptionA` | string | No | Free-text description of variant A, used by UIClip for variant A only. Same `user`/`generic` fallback semantics as `/analyses/single`'s `description`. |
| `descriptionB` | string | No | Same, for variant B. |
| `runLlm` | boolean | No | Shared for both variants. Defaults to `true`. |
| `runUiclip` | boolean | No | Shared for both variants. Defaults to `true`. |

A minimal valid request needs only `imageA` and `imageB`.

**Validation**: Identical per-image rules as `/analyses/single`, applied independently to `imageA` and `imageB` — a validation failure on either image (missing, unsupported MIME, oversized, corrupt, or an invalid `context`) fails the whole request with the same error codes as `/analyses/single`.

**Success Response** (`200`): A `VariantAnalysisReport`, `mode: "variants"` — `variantA` and `variantB` are each a complete, standalone `AnalysisReport` (identical shape to `/analyses/single`'s response, including `presentation`), and are independently persisted the same way a single-analysis report is, so `GET /api/v1/analyses/{analysisId}` also resolves each variant's own `analysisId` afterward. `deltas` reports variant-B-minus-variant-A differences — see [report-schema.md](report-schema.md#variant-analysis-report-structure). The outer variant envelope itself (`analysisId` at the top level) is not separately retrievable; there is no `GET /analyses/variants/{id}`. `status` follows the same `completed`/`partial_success` semantics as `/analyses/single`, applied to the pair: `completed` only when both variants completed every requested stage.

**Error Responses**: Same catalog as `/analyses/single` (`VALIDATION_ERROR` 422, `UNSUPPORTED_MEDIA_TYPE` 415, `FILE_TOO_LARGE` 413, `INVALID_IMAGE` 422, `INVALID_CONTEXT` 422, `ANALYSIS_FAILED` 500, `INTERNAL_ERROR` 500) — raised by whichever variant's validation/decoding fails first. See [error-codes.md](error-codes.md).

---

## LLM Interpretation

`llmInterpretation` is populated by `app.llm.LLMInterpretationService`. It is an **interpreter only**: it receives exclusively the deterministic `lucidui` JSON and the analysis `context` — never the uploaded image, raw bytes, or a screenshot in any form (see [ADR-003](../architecture/decisions/ADR-003-json-only-llm-input.md)). It never computes a metric, never invents evidence not present in that JSON, and every observation cites at least one metric JSON path (`metricEvidence`) as evidence.

- **Provider selection** is configuration-driven (`LLM_PROVIDER` env var; see `backend/.env.example`). `mock` (default) is a deterministic, offline provider — no API key, no network call, always returns `status: "completed"` with `provider: "mock"` and fixed generic text (see [examples/single-analysis-response.json](examples/single-analysis-response.json)). `gemini` uses a real Google Gemini model via the official `google-genai` SDK (requires `GEMINI_API_KEY`) and returns model-generated, screenshot-specific text in the same shape.
- **`runLlm`** (request field, default `true`) controls whether this stage runs at all: `false` → `llmInterpretation.status: "disabled"`, `provider: null`, `summary: null`, empty arrays — see [report-schema.md](report-schema.md#llm-statuses-llminterpretationstatus).
- **Failure handling**: if no provider is configured (e.g. `gemini` selected without a key), or the provider cannot be reached, `status` becomes `"unavailable"`. If the provider responds but the response is malformed, fails schema validation, or is missing metric evidence, `status` becomes `"failed"`. Either way, the rest of the report (deterministic metrics, `presentation`, image metadata) is still returned and persisted — an LLM failure never discards the deterministic analysis, and never surfaces as a top-level HTTP error.

## UIClip Evaluation

`uiclip` is populated by `app.uiclip.UIClipEvaluationService`. It is an **independent learned evaluator** — never ground truth, never merged with or reinterpreting LucidUI's deterministic metrics (see [ADR-004](../architecture/decisions/ADR-004-uiclip-independent-evaluator.md)). It receives only the decoded screenshot and a description string — never `lucidui`, `llmInterpretation`, or comparison results.

- **Provider selection** is configuration-driven (`UICLIP_PROVIDER` env var). `mock` (default) is a deterministic, offline evaluator — no model download, no network call, always returns `status: "completed"` with `modelVersion: "mock-uiclip-v1"` and a fixed illustrative `qualityScore`. `huggingface` loads the real official BIG Lab checkpoint (`biglab/uiclip_jitteredwebsites-2-224-paraphrased` by default, via `transformers.CLIPModel`/`CLIPProcessor`) and returns a real `qualityScore` computed from the actual image + description — see [docs/research/uiclip-integration.md](../research/uiclip-integration.md).
- **`description` is optional for every provider.** If none was submitted, the service uses the documented generic fallback description and still runs UIClip; the report preserves `descriptionSource: "generic"` so clients can tell the score was computed without user-authored context.
- **`runUiclip`** (request field, default `true`) controls whether this stage runs at all: `false` → `uiclip.status: "disabled"`, `uiclip.enabled: false` — see [report-schema.md](report-schema.md#uiclip-statuses-uiclipstatus).
- **`description`** resolves to `descriptionSource: "user"` when a non-blank value is submitted, or the documented `descriptionSource: "generic"` fallback (`"A software user interface screenshot."`) when omitted or blank — see [report-schema.md](report-schema.md#description-sources-uiclipdescriptionsource-and-anywhere-a-description-is-attached).
- **`normalizedQualityScore` is always `null`**: the official UIClip paper (arXiv:2404.12500) computes its score as the dot product between image and text embeddings — an uncalibrated, CLIP-style similarity/logit value. No documented, independently-verified 0–100 or 0–1 normalization exists, so none is invented here. `qualityScore` carries the raw score instead; `presentation.uiclipSummary.scoreType` labels it explicitly as `"Learned raw model score"`.
- **Failure handling**: if no provider is configured/available (or model loading failed), `status` becomes `"unavailable"`. If the provider runs but its output is malformed or fails validation, `status` becomes `"failed"`. Either way, the rest of the report is still returned and persisted — a UIClip failure never discards the rest of the analysis, and never surfaces as a top-level HTTP error.

## Notes

- The in-memory repository does not persist across backend restarts — durable persistence is Phase 9 (see [ROADMAP.md](../../ROADMAP.md)). Do not assume an `analysisId` from a previous backend run still resolves.
- All error responses use the shared JSON error envelope defined in [error-codes.md](error-codes.md).
- CORS is wide open (`allow_origins: ["*"]`, no credentials) by default in local development — no special headers/config are needed from the frontend to call the API cross-origin during development.
