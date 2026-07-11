"""Image processing infrastructure: validation, in-memory decoding, and
metadata extraction for uploaded screenshots.

This package only prepares images for later pipeline stages (Phase 2B
deterministic metrics, OCR, UIClip) — it does not compute any metric or
score itself. See docs/architecture/privacy-model.md: images are never
written to disk here.
"""
