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

## Implementation Status: `metricEngineVersion`

As of Phase 2B-1, `app.metrics.MetricEngine` wrapped `backend/reference/legacy_metric_engine.py` (immutable — see [CLAUDE.md](../../CLAUDE.md)) unchanged, and every report carried `metricEngineVersion: "legacy-v1"`.

A subsequent practical validation pass (source-code inspection, real-pipeline runs, and manual pixel-level ground-truth checks against real screenshots) found seven of `legacy-v1`'s metrics structurally weak or mislabelled — most importantly, contrast sampling that understated real text contrast by 2×–17×, and a small-target check that fired on ordinary text line-height rather than tap-target size. `backend/reference/legacy_metric_engine.py` itself was **not modified** (it remains importable as the frozen `legacy-v1` reference/audit-trail baseline). Instead, corrected implementations were added in `backend/app/metrics/corrected.py`, and `MetricEngine` was rewired to call them. Every report now carries `metricEngineVersion: "corrected-v1"`.

`corrected-v1` changes the *computation* of `contrast`, `elements` (small-target scope + a new repeating-grid exclusion feeding Hick's Law), `groups`, `whitespaceAlignment` (brightness-gated whitespace + a new per-axis alignment ratio), `fittsFullIndexOfDifficulty` (control-like elements only), and `textDensity`'s `fontSizeDiversityProxy` (median-absolute-deviation instead of std-dev) — every existing field *name* is preserved, with a small number of new, additive fields (`regionsSkipped`, `filteredElementCount`, `repeatingGridExcludedCount`, `alignedElementRatio`) and one new additive signal (`hueDiversity`, alongside the unchanged `colorfulnessScore`). `clutter`, `colorfulness`, `visualBalance`, and the composite-score `WEIGHTS`/`normalize()` bounds are unchanged — see [known-limitations.md](known-limitations.md) for what `corrected-v1` still does not address, and `app.metrics.corrected`'s module docstring for the fix-by-fix rationale.

A follow-up per-region diagnostic run against a real screenshot found `corrected-v1`'s contrast sampling (Otsu ink/paper split, flat cluster mean) still understated contrast specifically on small, regular-weight text, because anti-aliased edge pixels dominate a small glyph's ink cluster and pull its mean toward gray — real dark-gray body text (true ratio ~5.5:1) measured at ~3.5–4.0:1 and was wrongly flagged failing AA. `analyze_contrast_v3` ("Contrast Sampling V3") replaced `analyze_contrast_v2` in `MetricEngine` — foreground came from a per-channel median of the darkest/lightest 15% of the ink cluster, background from only border-connected background pixels. Every report carried `metricEngineVersion: "corrected-v2"`.

A second cross-check — three independent whole-region methods (Otsu-cluster mean, percentile-decile, k-means) run against the same real screenshot — found V3's core-percentile estimate measurably *higher* than all three specifically on small anti-aliased paragraph text, enough to flip the WCAG AA classification. `analyze_contrast_v4` ("Contrast Sampling V4 — dual estimate") replaces `analyze_contrast_v3` in `MetricEngine` — `analyze_contrast_v2`/`v3` are both kept in `app.metrics.corrected` for reference, unused. V4 computes V3's core estimate *and* a conservative estimate (per-channel median of the whole ink cluster), and only reports a confirmed pass/fail when both agree; when they disagree it reports `status: "uncertain"`, `aaResult: "borderline"`, both ratios, and the resulting range — never fabricating a single number and never counting the region toward a confirmed pass or violation. Every report now carries `metricEngineVersion: "corrected-v3"`; `regionsBorderline` is a new additive field in `contrast`, alongside the existing `regionsUncertain` (now scoped to insufficient-sample cases only). See [metric-catalog.md](metric-catalog.md#contrast) for the full method and `app.metrics.corrected`'s module docstring for the code-level rationale.

A confidence/provenance transparency pass (research-usability request, not a computation fix) added three additive fields without changing `metricEngineVersion` or any existing computation, matching the precedent set by earlier additive-only fields (`alignedElementRatio`, `hueDiversity`): `textDensity.averageOcrConfidence`/`textDensity.lowConfidenceWordsExcluded` expose Tesseract's own per-word confidence backing `textDensityRatio`/`fontSizeDiversityProxy`, so a research correlation study can filter or stratify by OCR reliability instead of treating every analysis as equally trustworthy; `elements.hicksLawBConstantMs` exposed the previously-implicit `b=150ms` Hick's Law constant as its own field, and `elements.source`/`whitespaceAlignment.source` stated directly in the JSON (not only in [known-limitations.md](known-limitations.md)) that this constant, the repeating-grid detector's geometric thresholds, and the whitespace/alignment thresholds were unsourced or tuned against only a small internal validation set. See [scientific-references.md](scientific-references.md#hicks-law) for the full caveat (`hicksLawBConstantMs` and `whitespaceAlignment` no longer exist as of `corrected-v4` — see below).

`corrected-v4` removed every metric classified **Problematic** in [reliability-tiers.md](reliability-tiers.md) from the engine/API entirely, per explicit user instruction, for research-paper defensibility — not merely excluded from reporting. Removed: `clutter` (`edgeDensity`), `whitespaceAlignment` (`whitespaceRatio`/`alignmentVariance`/`alignedElementRatio`), and `elements.hicksLawEstimateMs`/`hicksLawBConstantMs`/`smallTargetsBelow44px`/`repeatingGridExcludedCount` (the repeating-grid *filtering* itself is retained — only its standalone count field is gone; see [metric-catalog.md](metric-catalog.md#detected-element-count)). The composite score's `clutter`/`elementSize`/`groupCount` components are dropped accordingly, leaving only `contrast`+`textDensity`. Rather than modify `legacy_metric_engine.py`'s `WEIGHTS`/`normalize_metrics`/`weighted_score` (immutable per [CLAUDE.md](../../CLAUDE.md)), `backend/app/metrics/corrected.py` adds `WEIGHTS_V2`/`normalize_metrics_v2`/`weighted_score_v2`, which `MetricEngine` now calls instead — the legacy versions remain untouched and simply unused, per the pattern every earlier `corrected-*` fix already followed. The remaining two components' relative weight is preserved by proportionally rescaling the legacy weights back up to 1.0:

```text
general:  contrast 0.25/(0.25+0.20) = 0.5556, textDensity 0.4444
expert:   contrast 0.25/(0.25+0.10) = 0.7143, textDensity 0.2857
```

`AnalysisReport.schemaVersion`/`VariantAnalysisReport.schemaVersion` were bumped from `"1.0"` to `"2.0"` alongside this change (removing JSON fields is a breaking structural change per [docs/api/report-schema.md](../api/report-schema.md)). Every report now carries `metricEngineVersion: "corrected-v4"`.

An Interpretation Hardening pass (`backend/app/presentation/report_builder.py`'s `_COMPOSITE_EXPLANATION`, no `metricEngineVersion`/schema change) strengthened the composite score's presentation-layer explanation text to state its scope explicitly: it is a weighted summary of only `contrast` and `textDensity`, not every metric on the report, and not an overall UI quality score. This was prompted by a real analysis where the composite rendered as a bare "96.2 / 100" figure that could be misread as a general quality score even though, post `corrected-v4`, it reflects only two of the report's metrics. `scoreName` (`"LucidUI Composite Signal Score"`) and the weighting math (`WEIGHTS_V2`) are unchanged — renaming `scoreName` was considered and rejected as unnecessary churn, since it is not currently rendered anywhere in the frontend (only `composite.rawDisplay`/`.explanation` are). See [interpretation-taxonomy.md](interpretation-taxonomy.md) for the broader rule this is one instance of ("measurement does not imply optimization direction" / a value must not be misread as a verdict).
