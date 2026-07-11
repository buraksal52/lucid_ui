# Scoring and Normalization

This document explains how individual metrics from the [metric catalog](metric-catalog.md) are normalized and combined, and what the resulting composite score does and does not mean.

## Raw Metrics vs. Normalized Signals

A **raw metric** is a value in its natural unit — a contrast ratio (`4.5:1`), an edge-pixel ratio (`0.18`), a count (`23` detected elements). Raw metrics are always preserved in the report JSON because they are the most explainable, source-traceable form of the data (see [terminology.md](../product/terminology.md)).

A **normalized signal** rescales a raw metric onto a common 0–1 range so metrics with different units and scales can be combined. Normalization requires:

- A defined input range (or reference threshold) per metric.
- A direction: whether higher-normalized means "more" of the underlying raw quantity, or has been inverted.

## Why Some Signals Are Inverted

Not every metric has the same relationship between "raw value" and "normalized signal direction." For example, a very high edge-density (clutter proxy) raw value is normalized so that the composite score treats it as reducing the overall signal, while a contrast ratio comfortably above the WCAG reference threshold is normalized so it does not reduce the score. Inversion is a normalization-layer decision, not a claim that "high" or "low" is inherently good — see the "Flashlight, Not a Judge" principle in [CLAUDE.md](../../CLAUDE.md). Each metric's normalization direction must be documented alongside its entry in the metric JSON output.

## General and Expert Contexts

LucidUI supports a `context` parameter (e.g. `general`, `expert` — see [docs/api/api-contract.md](../api/api-contract.md)) that may adjust which thresholds or weights apply during normalization. The specific weighting differences per context are not finalized in Phase 0 and must be defined explicitly, with documentation updates, when implemented.

## Weighted Score Calculation

The **LucidUI Composite Signal Score** is a weighted combination of normalized signals:

```text
composite_score = Σ (weight_i × normalized_signal_i)
```

Weights are fixed per scoring-rule version (see Versioning below) and must be documented alongside the score in the report output so the calculation is reproducible and auditable.

## Why the Weighted Score Is Not an Objective Quality Score

The composite score is a summary of proxy signals, each with known limitations (see [known-limitations.md](known-limitations.md)), combined with weights that reflect an editorial choice about relative emphasis — not a validated measurement of design quality. It must always be presented as a **signal**, not a grade. Recommended public name: **LucidUI Composite Signal Score** — never "UI Quality Score" or similar verdict-implying names.

## Versioning of Scoring Rules

The weights, normalization ranges, and thresholds used to compute the composite score constitute a "scoring ruleset" that must be versioned independently of the API schema version. Any change to weights or normalization logic must:

- Increment the scoring ruleset version.
- Be recorded in the report JSON so a report can always be traced back to the exact ruleset that produced it.
- Avoid silently changing historical interpretations of previously computed scores.

## Preserving Raw Values

Regardless of scoring ruleset changes, raw metric values must always be preserved in the report output. Normalization and weighting are derived, replayable transformations of the raw values — never a replacement for them. This is required both for explainability (see [CLAUDE.md](../../CLAUDE.md)) and for future research recomputation (see [docs/research/evaluation-plan.md](../research/evaluation-plan.md)).
