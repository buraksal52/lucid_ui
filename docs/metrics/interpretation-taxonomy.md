# Interpretation Taxonomy

This document classifies every retained metric (post `corrected-v4` Tier 3 removal — see [reliability-tiers.md](reliability-tiers.md)) by **what kind of conclusion the LLM interpretation layer is allowed to draw from it** — a different axis from reliability. Reliability tiers answer "how much should I trust this measurement." This document answers "what, if anything, may I recommend based on this measurement."

**The governing rule: measurement does not imply optimization direction.** A metric having a high or low value is never, by itself, a reason to recommend changing it. This extends [CLAUDE.md](../../CLAUDE.md)'s "Flashlight, Not a Judge" principle from the deterministic engine (which already reports observations, not verdicts) to the LLM interpretation layer, which is free text and therefore harder to constrain.

This taxonomy is enforced two ways, both required — a prompt is advisory only:
- `backend/app/llm/prompt.py`'s `SYSTEM_PROMPT` encodes these rules for the LLM directly.
- `backend/app/llm/interpretation_guard.py`'s `TAXONOMY` constant and forbidden-combination filters are the actual enforced backstop, applied to every provider response (mock or real) regardless of prompt compliance — see that module's docstring for why a deterministic backstop is necessary (a real provider has been observed to ignore the prompt).

## Categories

- **ACTIONABLE** — sufficient normative/reference grounding exists for a cautious recommendation, and only when that grounding is actually present in the specific result (not merely because the metric category is generally actionable).
- **DIAGNOSTIC** — the metric can identify something worth inspecting, but cannot by itself establish that the design is good/bad or prescribe a direction. Cautious inspection language only ("may warrant review", "this signal may indicate...").
- **DESCRIPTIVE** — the metric characterizes a property of the interface. It must never independently generate an increase/decrease recommendation or a quality judgment, regardless of how high or low the value is. It may still appear in a plain observation that simply reports the value.

## Classification

| Metric | Evidence path prefix | Category | Rationale |
|---|---|---|---|
| Contrast | `raw.contrast` | **Actionable** | WCAG 2.1 AA is a documented, external reference threshold. A *confirmed* below-threshold or borderline region (see [reliability-tiers.md](reliability-tiers.md)'s Contrast V4 entry) is real, reference-grounded evidence — not an inference from the raw number alone. |
| Detected Elements / `interactiveTargetCount` | `raw.elements` | **Diagnostic** | No validated "correct" element count exists. A detected region can be surfaced for review, but its presence/absence is never itself good or bad. |
| Grouping / `estimatedGroupCount` | `raw.groups` | **Descriptive** | No validated normative group count exists. Miller's Law (Miller, 1956) describes short-term memory chunk capacity in a different experimental context — it is **not** a UI design target. LucidUI has no cognitive-load measurement of any kind; `estimatedGroupCount` cannot be used to infer cognitive load, information chunking, or a "reduce/simplify the grouping" recommendation, at any value. |
| Text Density | `raw.textDensity` | **Diagnostic** | No validated optimal text density exists. Coverage can be surfaced for inspection, never called "too much/too little" or "optimal." |
| Colorfulness | `additionalSignals.colorfulness` | **Descriptive** | Hasler & Süsstrunk (2003)'s formula rewards saturated-area *coverage*, not aesthetic quality or engagement — see the catalog's own limitation note. Colorfulness is **not a monotonic quality signal**: neither a higher nor a lower value is inherently better, more usable, or more engaging. |
| Hue Diversity | `additionalSignals.hueDiversity` | **Descriptive** | Same non-monotonicity as colorfulness — a hue-histogram entropy statistic, not a design-quality measure. |
| Fitts's Law | `additionalSignals.fittsFullIndexOfDifficulty` | **Diagnostic** | A proxy movement-difficulty estimate with no real pointer origin and no validated threshold — worth reviewing for outliers, never a pass/fail verdict. |
| Visual Balance | `additionalSignals.visualBalance` | **Descriptive** | A brightness-only proxy (left/right, top/bottom luminance difference), not compositional balance, and with no validated normative asymmetry threshold. Must never be called "good," "bad," "well-balanced," or "poor." |

## How this is used

- **In the LLM interpretation layer**: `SYSTEM_PROMPT` states these restrictions explicitly per category, plus the specific non-negotiable rules (no 7±2 comparison, no cognitive-load inference, no colorfulness/hue-diversity increase/decrease language, no visual-balance quality adjectives) — see `backend/app/llm/prompt.py`.
- **As a deterministic backstop**: `backend/app/llm/interpretation_guard.py` scans every summary sentence, observation, and recommendation for the forbidden metric-term + judgment/directional-term combinations and drops (never rewrites) anything that matches, regardless of which provider produced it. This is a pattern-based heuristic, not a semantic guarantee — documented as a known limitation of the guard itself.
- **In presentation**: descriptive/diagnostic metrics still render as ordinary `MetricCard`s with their raw value (see [presentation-schema.md](../api/presentation-schema.md)) — this taxonomy restricts what the *LLM* may conclude from them, not whether the deterministic value itself is shown.
- **When adding a new metric**: it must be classified here (and in `interpretation_guard.TAXONOMY`) before its evidence path can be cited in LLM output — `test_interpretation_guard.py::test_taxonomy_covers_every_key_metric_engine_actually_produces` fails the build if a new `MetricEngine` output key has no classification.

## Related documents

- [reliability-tiers.md](reliability-tiers.md) — the orthogonal "how accurate is this measurement" axis.
- [metric-catalog.md](metric-catalog.md) — full per-metric method, interpretation, and known-limitations detail.
- [scoring-and-normalization.md](scoring-and-normalization.md) — composite score scope and framing.
- [CLAUDE.md](../../CLAUDE.md) — "Flashlight, Not a Judge" and the LLM Rules this taxonomy extends.
