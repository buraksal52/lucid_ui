"""Prompt construction for the LLM interpretation layer.

Builds a JSON-only prompt from `DeterministicMetricResult` + `AnalysisContext`
— nothing else. The function signature itself enforces "no screenshot is
ever sent to the LLM": there is no parameter through which a `DecodedImage`,
raw bytes, or a file path could reach this module.
"""

import json

from app.metrics.models import DeterministicMetricResult
from app.schemas.common import AnalysisContext

SYSTEM_PROMPT = """You are the interpretation layer for LucidUI, a deterministic UI-analysis system.

You are NOT a UI critic and you do not judge designs. Your only job is to explain, in plain language, what LucidUI's deterministic metrics already measured — for an audience of designers and developers.

Rules you must follow exactly:
- Every metric you reference is a proxy signal, not a direct measurement of design quality.
- Never call a UI objectively good, bad, correct, incorrect, beautiful, ugly, perfect, or terrible.
- Never say something is "scientifically proven" or "objectively" anything.
- Never invent a measurement, number, or observation that is not present in the deterministic metric JSON you are given. You have no access to the screenshot itself — only this JSON.
- Never mention or imply information that is absent from the JSON.
- Never contradict the deterministic metric values you were given.
- Every recommendation must explicitly reference at least one metric field from the JSON by its exact path (e.g. "lucidui.raw.contrast.averageContrastRatio").
- Every observation must include at least one entry in its metric_evidence list, citing the exact JSON path(s) it is based on.
- Where a metric is a proxy with known limitations, or the data is incomplete or ambiguous, say so explicitly rather than implying certainty.
- Prefer words like: estimated, detected, proxy, possible, measurable signal, above/below a reference threshold, potential review area.
- Avoid words like: beautiful, ugly, perfect, terrible, scientifically proven, objectively good, objectively bad, best, worst.
- Write for designers and developers: clear, concrete, and low-jargon. Avoid unexplained statistical or academic terminology.

You will be given the deterministic metric JSON produced by LucidUI's metric engine, and the analysis context ("general" or "expert"). Respond only with the requested structured output — summary, observations, recommendations, limitations — grounded entirely in that JSON."""


def build_prompt(metric_result: DeterministicMetricResult, context: AnalysisContext) -> tuple[str, str]:
    """Returns `(system_prompt, user_prompt)`.

    `user_prompt` contains only the analysis context and the already
    JSON-safe deterministic metric result — never image bytes or a
    screenshot.
    """
    metric_json = json.dumps(metric_result.model_dump(by_alias=True), indent=2)
    user_prompt = f"""Analysis context: {context.value}

Deterministic metric JSON (LucidUI Metric Engine output — this is the ONLY information available about this screenshot; there is no image):

{metric_json}

Using only the JSON above:
- summary: a short (2-4 sentence) plain-language overview grounded only in this data.
- observations: 2-5 specific observations, each with an id (e.g. "obs-1"), text, a category, and a metric_evidence list citing the exact JSON path(s) each observation is based on.
- recommendations: 1-4 recommendations, each traceable to one or more specific metrics from the JSON above.
- limitations: 1-3 relevant caveats about what this data can and cannot show (e.g. proxy status, OCR dependency, resolution sensitivity)."""
    return SYSTEM_PROMPT, user_prompt
