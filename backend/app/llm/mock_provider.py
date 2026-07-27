"""Deterministic, offline LLM provider — no network calls.

The default provider (see app.config.Settings.llm_provider) so the full LLM
interpretation pipeline (prompt build -> provider call -> parse -> report)
is real and exercisable without any API key, and so tests never need a real
model. Returns a fixed, generically-worded structure rather than attempting
to simulate real reasoning: since this provider does no actual analysis, its
text deliberately makes no specific numeric claims about any given
screenshot — only generic, always-true statements about the metric
categories that are always present in `DeterministicMetricResult`, each
still citing real JSON paths as evidence.
"""

from typing import Any


class MockLLMProvider:
    name = "mock"

    def complete(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "summary": (
                "LucidUI's deterministic metric engine computed a composite proxy signal "
                "for this screenshot from contrast, element, and text density measurements. "
                "This is a placeholder interpretation from the mock provider, not a live model response."
            ),
            "observations": [
                {
                    "id": "obs-1",
                    "text": (
                        "A composite signal score was estimated from the normalized metrics "
                        "described below; it is a weighted proxy summary, not a quality grade."
                    ),
                    "metric_evidence": ["lucidui.weightedScore", "lucidui.normalized"],
                    "category": "observation",
                },
                {
                    "id": "obs-2",
                    "text": (
                        "Contrast and text density were measured against fixed reference "
                        "thresholds as detected, screenshot-based proxy signals."
                    ),
                    "metric_evidence": ["lucidui.raw.contrast", "lucidui.raw.textDensity"],
                    "category": "observation",
                },
            ],
            "recommendations": [
                (
                    "Reviewing the raw metric values in lucidui.raw against their documented "
                    "reference thresholds could help identify possible review areas, since "
                    "values below threshold are flagged as such rather than confirmed issues."
                ),
            ],
            "limitations": [
                "This interpretation was produced by a deterministic mock provider, not a live "
                "language model, and is intentionally generic.",
                "All underlying metrics are screenshot-based proxy signals with known limitations "
                "— see docs/metrics/known-limitations.md.",
            ],
        }
