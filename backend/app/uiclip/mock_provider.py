"""Deterministic, offline UIClip provider — no model loading, no inference.

The default provider (see app.config.Settings.uiclip_provider) so the full
UIClip evaluation pipeline (service -> provider -> validate -> report) is
real and exercisable without downloading or running the official model, and
so tests never need GPU/model weights. Explicitly self-identifies as mock
via `model_version` — never claims to represent real UIClip inference.

`raw_score` is a fixed illustrative value in a CLIP-logit-like range (not a
0-100 or 0-1 "quality percentage" — see app.uiclip.models), deliberately
chosen to avoid looking like a calibrated score, consistent with the
official model's own output semantics as verified in
docs/research/uiclip-integration.md.
"""

from typing import Any

from PIL.Image import Image


class MockUIClipProvider:
    name = "mock"

    def evaluate(self, image: Image, description: str) -> dict[str, Any]:
        return {
            "model_version": "mock-uiclip-v1",
            "raw_score": 21.7,
            "observations": [
                "Mock UIClip output only; no real model evaluation was run.",
            ],
        }
