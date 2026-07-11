# ADR-002: In-Memory Image Processing, No Disk Writes by Default

## Status

Accepted

## Context

Uploaded UI screenshots may contain sensitive product interfaces, unreleased designs, or internal tools. LucidUI needs to decode and analyze these images without creating unnecessary privacy or data-retention risk.

## Decision

Uploaded images are validated and decoded entirely in memory. The backend does not write uploaded image bytes to disk as part of the default analysis flow.

## Rationale

- Minimizes the attack surface and retention footprint for potentially sensitive screenshots.
- Aligns with the "Flashlight, Not a Judge" and privacy-first product principles in [docs/product/product-scope.md](../../product/product-scope.md) and [privacy-model.md](../privacy-model.md).
- Avoids the operational burden of secure file cleanup, orphaned temp files, and disk-based attack vectors.

## Consequences

- Image validation (MIME type, 20 MB size limit) and decoding must operate on in-memory byte buffers / streams.
- Any future feature that needs persisted images (e.g. a dataset-building tool) must be a separate, explicitly opt-in code path, documented before implementation, not a side effect of the default analysis flow.
- Debugging a decoding failure cannot rely on inspecting a file on disk; error responses and logs must carry enough structured detail (dimensions attempted, format detected, error code) to diagnose without the original bytes.
