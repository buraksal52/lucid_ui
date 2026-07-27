"""Deterministic post-hoc guard against unsupported LLM interpretation content.

`SYSTEM_PROMPT` (app.llm.prompt) instructs the LLM not to turn a
DESCRIPTIVE metric (estimated group count, colorfulness, hue diversity,
visual balance) into a prescriptive or quality-judgment claim — but a
prompt is advisory only, and a real provider has been observed to ignore
it in production (e.g. "increasing colorfulness... could enhance visual
appeal", "...could improve information chunking and reduce cognitive
load" derived solely from estimatedGroupCount, "the UI shows good visual
balance"). This module is the actual enforced guarantee:
`LLMInterpretationService.interpret()` runs the provider's summary,
observations, and recommendations through it after structural validation,
and drops (never rewrites or invents replacement text for) anything that
matches a forbidden combination.

This is a pattern-based heuristic backstop, not a semantic guarantee — an
adversarially- or unusually-phrased LLM output could still slip through.
It exists specifically to catch the failure modes documented in
docs/metrics/interpretation-taxonomy.md, which is the source of truth for
`TAXONOMY` below; the prompt hardening in app.llm.prompt is the primary
defense, this is defense-in-depth.
"""

import re
from typing import Literal

from app.llm.models import LLMObservationOutput

InterpretationCategory = Literal["actionable", "diagnostic", "descriptive"]

# Evidence-path prefix (the first segment of a "raw.X..."/"additionalSignals.X..."
# JSON path, as cited in metric_evidence) -> category. Every raw/
# additionalSignals key MetricEngine actually produces (see
# app.metrics.engine.MetricEngine.analyze) must have an entry here — see
# docs/metrics/interpretation-taxonomy.md for the full rationale per metric.
# "resolution" carries no interpretable content and is intentionally
# omitted (never cited as evidence, never appears in LLM output).
TAXONOMY: dict[str, InterpretationCategory] = {
    "contrast": "actionable",
    "elements": "diagnostic",
    "groups": "descriptive",
    "textDensity": "diagnostic",
    "colorfulness": "descriptive",
    "hueDiversity": "descriptive",
    "fittsFullIndexOfDifficulty": "diagnostic",
    "visualBalance": "descriptive",
}

_COLOR_DIRECTIONAL_TERMS = (
    "increase",
    "decrease",
    "more colorful",
    "less colorful",
    "more vivid",
    "less vivid",
    "enhance",
    "boost",
    "engaging",
    "visual appeal",
)

# (metric-term keywords, judgment/directional-term keywords): a forbidden
# combination is confirmed when a text contains at least one term from
# each side, case-insensitively. The metric-term side is intentionally
# broader (e.g. bare "groups"/"grouping") than the judgment-term side,
# which stays narrow and specific (e.g. "cognitive load", not bare
# "reduce") — this is what keeps the guard from ever tripping on a
# justified, unrelated contrast/accessibility recommendation, which never
# shares vocabulary with these judgment terms.
_FORBIDDEN_COMBINATIONS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("group count", "groups", "grouping"),
        (
            "cognitive load",
            "chunking",
            "simplify",
            "too many",
            "too few",
            "7±2",
            "7 ± 2",
            "7+/-2",
            "7 +/- 2",
            "seven plus or minus",
            "miller",
        ),
    ),
    (("colorfulness", "colourfulness"), _COLOR_DIRECTIONAL_TERMS),
    (("hue diversity", "huediversity"), _COLOR_DIRECTIONAL_TERMS),
    (
        ("visual balance", "asymmetry"),
        ("good", "bad", "poor", "well-balanced", "well balanced"),
    ),
    (("text density",), ("optimal", "ideal")),
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def is_unsupported(text: str) -> bool:
    """True if `text` matches a forbidden metric-term + judgment/directional
    combination — see `_FORBIDDEN_COMBINATIONS`."""
    lowered = text.lower()
    return any(
        any(term in lowered for term in metric_terms) and any(term in lowered for term in judgment_terms)
        for metric_terms, judgment_terms in _FORBIDDEN_COMBINATIONS
    )


def filter_recommendations(recommendations: list[str]) -> tuple[list[str], bool]:
    """Returns `(kept, any_dropped)`. Drops (never rewrites) any
    recommendation matching a forbidden combination."""
    kept = [text for text in recommendations if not is_unsupported(text)]
    return kept, len(kept) != len(recommendations)


def filter_observations(
    observations: list[LLMObservationOutput],
) -> tuple[list[LLMObservationOutput], bool]:
    """Returns `(kept, any_dropped)`. Drops (never rewrites) any
    observation whose text matches a forbidden combination. Descriptive
    metrics may still appear in surviving observations — only the specific
    judgment/directional phrasing is disqualifying, not the metric itself."""
    kept = [observation for observation in observations if not is_unsupported(observation.text)]
    return kept, len(kept) != len(observations)


def filter_summary(summary: str | None) -> tuple[str | None, bool]:
    """Returns `(filtered_summary, any_dropped)`. Splits `summary` into
    sentences (naive `.`/`!`/`?` boundary split) and drops only the
    sentences that match a forbidden combination, rejoining the rest —
    never rewrites a surviving sentence. Returns `None` if nothing
    survives; `app.presentation.report_builder` already falls back to a
    fixed placeholder for a `None`/empty summary."""
    if not summary:
        return summary, False
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(summary.strip()) if s]
    kept = [s for s in sentences if not is_unsupported(s)]
    if len(kept) == len(sentences):
        return summary, False
    return (" ".join(kept) if kept else None), True
