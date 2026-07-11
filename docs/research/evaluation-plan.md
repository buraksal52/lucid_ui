# Evaluation Plan

This is an early, non-final plan for how LucidUI's research questions ([research-questions.md](research-questions.md)) would eventually be evaluated at the dataset level. It is scoped for Phase 10 ([ROADMAP.md](../../ROADMAP.md)) and is not being executed in Phase 0.

## UI Categories

Evaluation datasets should span multiple UI categories rather than a single type, to surface where LucidUI and UIClip agree or diverge (research question 2):

- Dashboards
- Landing pages
- Forms
- E-commerce screens
- Mobile screens

## Human Rating Dimensions

Human raters would score each screenshot along multiple dimensions (exact dimensions TBD, informed by existing HCI/design-evaluation literature), rather than a single overall "quality" number, to allow more granular comparison against specific LucidUI metrics.

## Multiple Raters Per Screenshot

Each screenshot should be rated by more than one human rater, so inter-rater agreement can be assessed and single-rater idiosyncrasy does not dominate the dataset.

## LucidUI Outputs

For each screenshot in the dataset: full raw metrics, normalized signals, and composite signal score, captured with the exact engine and scoring-ruleset version used (see [docs/metrics/scoring-and-normalization.md](../metrics/scoring-and-normalization.md)), so results are reproducible.

## UIClip Outputs

For each screenshot: preference score, description used, and model checkpoint version (see [uiclip-integration.md](uiclip-integration.md)).

## Statistical Analysis

- **Pearson correlation** — for linear association between LucidUI/UIClip signals and human ratings.
- **Spearman correlation** — for rank-based association, more robust to non-linear relationships and rating-scale artifacts.
- **Confidence intervals** — reported alongside every correlation estimate, not point estimates alone.
- **Inter-rater agreement** — computed among human raters per screenshot/dimension, to establish how much noise exists in the human-rating baseline itself before comparing model/metric signals against it.

## Limitations and Ethics

- Any evaluation dataset must have appropriate rights/permissions for the screenshots used.
- Human raters must be treated fairly (compensated appropriately, informed about the study) if this becomes a formal study.
- Results are only as generalizable as the dataset's category coverage and rater pool — findings should be reported with these caveats, not as universal claims.
- See [docs/metrics/known-limitations.md](../metrics/known-limitations.md) for caveats that must be disclosed alongside any correlation results.

## Exploratory vs. Confirmatory Analysis

This plan distinguishes two phases of analysis:

- **Exploratory** — open-ended examination of the dataset to generate hypotheses (e.g. "LucidUI's edge density seems to track human clutter ratings better in dashboards than in landing pages").
- **Confirmatory** — pre-registered, specific hypothesis tests run on held-out data or a separate dataset, to avoid overstating findings that were only observed after looking at the same data used to generate the hypothesis.

Exploratory findings must be clearly labeled as such and not presented as confirmed results. See [experiment-log.md](experiment-log.md) for how individual experiments (exploratory or confirmatory) should be recorded.
