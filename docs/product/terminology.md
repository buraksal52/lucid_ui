# Terminology

Consistent vocabulary for LucidUI documentation, API responses, and frontend copy. See also [docs/metrics/metric-catalog.md](../metrics/metric-catalog.md) and [CLAUDE.md](../../CLAUDE.md) for the "Flashlight, Not a Judge" language rules.

**Deterministic metric** — A value computed by a fixed, reproducible algorithm (classical CV, OCR, or a formula) rather than a learned model. Given the same image and the same engine version, a deterministic metric always produces the same result.

**Proxy metric** — A deterministic metric that stands in for a concept LucidUI cannot directly measure from a screenshot (e.g. "detected element count" as a proxy for "number of choices" in a Hick's Law estimate). Proxy metrics approximate, they do not measure the underlying construct directly. See [known-limitations.md](../metrics/known-limitations.md).

**Raw metric** — The unprocessed output of a measurement, in its natural unit (e.g. a contrast ratio like `4.5:1`, an edge-pixel ratio like `0.18`).

**Normalized signal** — A raw metric rescaled onto a common range (typically 0–1) so it can be combined with other metrics into a composite score. Normalization may invert direction (see [scoring-and-normalization.md](../metrics/scoring-and-normalization.md)).

**Weighted signal score** — A single number combining multiple normalized signals using fixed weights. Publicly referred to as the **LucidUI Composite Signal Score**. It is a summary signal, not an objective quality score.

**Threshold** — A reference value (e.g. WCAG 2.1 AA's 4.5:1 contrast ratio) used to describe a metric as above or below a known reference point. Thresholds are reference points, not pass/fail verdicts on design quality.

**Observation** — A natural-language statement produced by the LLM interpretation stage, grounded in one or more specific metric values (see "metric evidence" in [docs/api/report-schema.md](../api/report-schema.md)).

**Recommendation** — A short, metric-traceable suggestion produced by the LLM interpretation stage (`llmInterpretation.recommendations`, passed through into `presentation.recommendations`). Grounded entirely in the deterministic metric JSON, never a prescriptive design verdict — see [non-goals.md](non-goals.md).

**UIClip raw model score** — The output of the UIClip model (`uiclip.qualityScore` / `presentation.uiclipSummary.rawScoreDisplay`): an uncalibrated, CLIP-style dot-product/logit value representing the model's learned signal for the given screenshot and description. It is a model output, not a measurement of objective quality, and — since no verified 0–100/0–1 normalization exists — not on the same scale as LucidUI's weighted signal score (`uiclip.normalizedQualityScore` is always `null` today). Avoid "preference score," which does not match the implemented field.

**Agreement** — A case where the LucidUI-derived interpretation and the UIClip result point in the same direction on a given aspect of the UI.

**Discrepancy** — A case where the LucidUI-derived interpretation and the UIClip result point in different directions on a given aspect of the UI. Neither side is assumed correct when a discrepancy is reported.

**Single analysis** — An analysis run on exactly one uploaded image (`/api/v1/analyses/single`).

**Variant comparison** — An analysis run on two uploaded images (A and B) analyzed independently, with relative deltas reported between their results (`/api/v1/analyses/variants`).

**Partial success** — An overall analysis status where the required deterministic metrics completed, but an optional stage (LLM interpretation or UIClip evaluation) did not (`disabled`, `unavailable`, or `failed`). The dashboard still shows all completed sections.

**Model unavailable** — A status indicating an optional model-backed stage (LLM or UIClip) could not run for operational reasons (e.g. not loaded, provider error) as opposed to being intentionally turned off (`disabled`).

**Description source** — Where a screenshot's natural-language description came from: `user` (typed by the person uploading), `generic` (a placeholder/default string), or `generated` (produced by a description-generation model — not to be used until such a model actually exists in the system).
