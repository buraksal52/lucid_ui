# Error Codes

This document defines the planned JSON error format and error code catalog for the LucidUI API. See [api-contract.md](api-contract.md) for which endpoints can return which codes.

## Error Envelope

All API errors return a JSON body of this shape:

```json
{
  "error": {
    "code": "INVALID_IMAGE",
    "message": "The uploaded file could not be decoded.",
    "details": null
  }
}
```

- **`code`** — a stable, machine-readable error code from the catalog below.
- **`message`** — a human-readable explanation, safe to display to a user.
- **`details`** — optional structured additional context (e.g. which field failed validation); `null` when not applicable.

## Error Code Catalog

| Code | Typical HTTP Status | Meaning |
|---|---|---|
| `INVALID_IMAGE` | 422 | The uploaded file could not be decoded as an image. |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | The uploaded file's MIME type is not one of JPG, PNG, or WebP. |
| `FILE_TOO_LARGE` | 413 | The uploaded file exceeds the 20 MB limit. |
| `INVALID_CONTEXT` | 422 | The provided `context` value is not one of the allowed analysis contexts. |
| `ANALYSIS_NOT_FOUND` | 404 | No stored analysis exists for the given `analysis_id`. |
| `ANALYSIS_FAILED` | 500 | The deterministic metric engine failed to produce a report. |
| `LLM_UNAVAILABLE` | 502 | LLM interpretation was requested but the provider could not be reached or is not configured. Distinct from a general analysis failure — the deterministic report may still be usable (`partial_success`). |
| `UICLIP_UNAVAILABLE` | 502 | UIClip evaluation was requested but the model could not run. Distinct from a general analysis failure — the deterministic report may still be usable (`partial_success`). |
| `INTERNAL_ERROR` | 500 | An unexpected server-side error not covered by a more specific code. |

## Usage Notes

- `LLM_UNAVAILABLE` and `UICLIP_UNAVAILABLE` describe stage-level failures reflected in `llmInterpretation.status` / `uiclip.status` within an otherwise-successful report (`partial_success`) — they are not necessarily top-level request failures. See [report-schema.md](report-schema.md#llm-statuses-llminterpretationstatus) and [report-schema.md](report-schema.md#uiclip-statuses-uiclipstatus).
- `ANALYSIS_FAILED` and `INTERNAL_ERROR` represent request-level failures where no usable report body is returned.
- See [examples/error-response.json](examples/error-response.json) for a realistic instance of this envelope.
