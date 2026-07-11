# Product Scope

## What LucidUI Is

LucidUI is a research-oriented UI analysis system that examines a screenshot of a user interface and reports measurable signals about it from two independent perspectives:

1. A **deterministic analysis engine** built on classical computer vision, OCR, and HCI/cognitive-science-inspired proxy metrics, which produces explainable, metric-level output (raw values, normalized signals, thresholds, sources).
2. **UIClip**, a learned vision-language model that produces a global, model-based preference signal, used as an independent evaluator rather than as ground truth.

An LLM interprets the deterministic metric JSON to produce natural-language observations grounded in specific metric evidence. A Comparison Engine then reports where the deterministic interpretation and UIClip agree or diverge. LucidUI never declares a UI objectively good or bad — see the "Flashlight, Not a Judge" principle in [CLAUDE.md](../../CLAUDE.md) and [terminology.md](terminology.md).

## Who It Is For

- Frontend developers who want a quick, explainable read on a screen before or after shipping it.
- UI/UX designers exploring variants and wanting a second, non-authoritative signal.
- Students learning HCI concepts (Hick's Law, Fitts's Law, contrast, visual clutter) against real interfaces.
- Researchers studying the relationship between deterministic UI metrics, learned model evaluators, and human judgment.
- Teams comparing two UI variants (A/B) and wanting a structured, side-by-side signal comparison.

## Initial Workflow

1. Upload a JPG, PNG, or WebP UI screenshot.
2. Optionally describe the interface (free text).
3. Run deterministic analysis (LucidUI metric engine).
4. Interpret the deterministic metrics with an LLM.
5. Evaluate the same screenshot with UIClip.
6. Display agreements and differences between the two evaluators on a results dashboard.

See [docs/architecture/analysis-pipeline.md](../architecture/analysis-pipeline.md) for the technical version of this flow, and [docs/frontend/FRONTEND_GUIDE.md](../frontend/FRONTEND_GUIDE.md) for the planned dashboard.

## LucidUI vs. UIClip

| | LucidUI Metric Engine | UIClip |
|---|---|---|
| Nature | Deterministic, rule-based, classical CV/OCR | Learned vision-language model |
| Output | Metric-level, explainable, sourced | Global preference score + description |
| Reproducibility | Fully reproducible given the same image | Model/version dependent |
| Role | Interpretable signal set | Independent learned signal |
| Ground truth? | No | No |

Both are fallible, both are informative, and neither overrides the other. See [ADR-004](../architecture/decisions/ADR-004-uiclip-independent-evaluator.md).

## Role of the LLM

The LLM does not see the screenshot. It receives only the deterministic metric JSON from the LucidUI engine and produces structured, evidence-linked observations in natural language — essentially translating metric output into readable commentary. It does not evaluate UIClip's output and does not generate a verdict. See [ADR-003](../architecture/decisions/ADR-003-json-only-llm-input.md).

## Initial Product Boundaries

See [non-goals.md](non-goals.md) for the full list of things LucidUI explicitly does not do in its first versions.

## Long-Term Possibilities

- Dataset-level benchmarking correlating LucidUI metrics and UIClip scores against human ratings (Phase 10).
- Historical analysis tracking (Phase 9) to see how a product's screens trend over time.
- A research paper or public write-up on the relationship between deterministic and learned UI evaluation signals.
- Possible support for additional learned evaluators beyond UIClip, following the same "independent evaluator" pattern.

These are directions, not commitments — see [ROADMAP.md](../../ROADMAP.md) for what is actually scheduled.
