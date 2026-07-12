# Error Codes

This document defines the JSON error format and error code catalog for the LucidUI API. See [api-contract.md](api-contract.md) for which endpoints can return which codes.

## Error Envelope

All API errors return a JSON body of this shape, regardless of endpoint or status code:

```json
{
  "error": {
    "code": "UNSUPPORTED_MEDIA_TYPE",
    "message": "Unsupported image type 'image/gif'. Allowed types: image/jpeg, image/png, image/webp.",
    "details": { "contentType": "image/gif", "allowed": ["image/jpeg", "image/png", "image/webp"] }
  }
}
```

- **`code`** — a stable, machine-readable error code from the catalog below.
- **`message`** — a human-readable explanation, safe to display to a user.
- **`details`** — optional structured additional context; `null` when the code carries none (see the per-code shapes below — do not assume every code has the same `details` shape).

This envelope is never wrapped, never returns an HTML error page, and never exposes a stack trace — safe to parse identically on every error response from every endpoint.

## Error Code Catalog

| Code | HTTP Status | Meaning | `details` shape |
|---|---|---|---|
| `VALIDATION_ERROR` | 422 | The request itself was malformed — a required field is missing (e.g. no `image` part in the multipart body) or a field has the wrong type (e.g. `runLlm` is not a boolean). This is FastAPI/Pydantic's own request validation, not a domain error. | A list of Pydantic-style error objects, e.g. `[{"type": "missing", "loc": ["body", "image"], "msg": "Field required", "input": null}]`. |
| `INVALID_IMAGE` | 422 | The uploaded file could not be decoded as an image (empty file, corrupted bytes, content doesn't match a supported image format). | `null`. |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | The uploaded file's MIME type is not one of `image/jpeg`, `image/png`, `image/webp`. | `{"contentType": string \| null, "allowed": string[]}`. |
| `FILE_TOO_LARGE` | 413 | The uploaded file exceeds the 20 MB limit (`MAX_UPLOAD_SIZE_BYTES`). | `{"sizeBytes": number, "maxBytes": number}`. |
| `INVALID_CONTEXT` | 422 | The provided `context` value is not one of the allowed analysis contexts (`general`, `expert`). | `{"context": string, "allowed": string[]}`. |
| `ANALYSIS_NOT_FOUND` | 404 | No stored analysis exists for the given `analysisId`. | `{"analysisId": string}`. |
| `ANALYSIS_FAILED` | 500 | The deterministic metric engine failed to produce a report (e.g. OCR execution failed). No usable report body is returned. | `null`, or a short diagnostic string — never raw internal stack traces. |
| `LLM_UNAVAILABLE` | — | **Never returned as a top-level HTTP error.** Caught internally by `LLMInterpretationService` and reflected as `llmInterpretation.status: "unavailable"` / `"failed"` in an otherwise-`200` report — see [report-schema.md](report-schema.md#llm-statuses-llminterpretationstatus). Listed here only because it is the code named in that service's internal exceptions. | n/a |
| `UICLIP_UNAVAILABLE` | — | **Never returned as a top-level HTTP error.** Caught internally by `UIClipEvaluationService` and reflected as `uiclip.status: "unavailable"` / `"failed"` in an otherwise-`200` report — see [report-schema.md](report-schema.md#uiclip-statuses-uiclipstatus). | n/a |
| `INTERNAL_ERROR` | 500 | An unexpected server-side error not covered by a more specific code. | `null`. |

## Usage Notes

- **Only `VALIDATION_ERROR`, `INVALID_IMAGE`, `UNSUPPORTED_MEDIA_TYPE`, `FILE_TOO_LARGE`, `INVALID_CONTEXT`, `ANALYSIS_NOT_FOUND`, `ANALYSIS_FAILED`, and `INTERNAL_ERROR` can actually appear as a top-level HTTP error response body.** `LLM_UNAVAILABLE` and `UICLIP_UNAVAILABLE` only ever appear inside a successful (`200`) report, as the reason a specific stage degraded — a frontend error handler (`ErrorBanner`) does not need to special-case them; a stage-status renderer (`LLMInterpretationPanel`, `UIClipEvaluationCard`) does.
- `ANALYSIS_FAILED` and `INTERNAL_ERROR` represent true request-level failures where no usable report body is returned at all — render `ErrorBanner`, do not attempt to show a partial dashboard.
- `VALIDATION_ERROR` is the most likely code to hit during frontend development (e.g. forgetting to append the `image` file part, or sending `runLlm` as a non-boolean) — its `details` is a raw list of FastAPI/Pydantic validation errors, useful for debugging but not necessarily meant for direct end-user display; prefer showing `message` to the user and logging `details`.
- See [examples/error-response.json](examples/error-response.json) for a realistic instance of this envelope.
