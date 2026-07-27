# Frontend Guide

The React frontend is developed independently from the backend, against the documented API contract. See [ADR-006](../architecture/decisions/ADR-006-frontend-backend-independence.md) and [mock-development.md](mock-development.md) for how to build without a running backend.

## Frontend Responsibilities

- Upload images (JPG, PNG, WebP), either one (single analysis) or two (variant comparison).
- Collect optional description and context (`general`/`expert`) from the user.
- Send API requests to the LucidUI backend (`POST /api/v1/analyses/single`, `POST /api/v1/analyses/variants`, `GET /api/v1/analyses/{analysisId}`, `GET /api/v1/analyses/{analysisId}/raw` — see [api-contract.md](../api/api-contract.md)).
- Display loading, partial-success, success, and error states (see [ui-states.md](ui-states.md)).
- Visualize backend results — primarily `presentation` (see below), and for variant comparison, `deltas` (see "Variant Comparison Flow" below). `comparison` (singular, inside each `AnalysisReport`) exists in the schema but carries no real LucidUI-vs-UIClip agreement/disagreement data yet (Phase 6 not implemented) — do not build a UI against it as if it were real. This is unrelated to variant `deltas`, which compares two *images*, not the two evaluators.
- Preserve backend values exactly as returned — display, don't transform.
- Never calculate or modify metric scores, composite scores, normalized scores, or display-string formatting client-side — all of that is already done in `presentation` (and, for variant comparison, in `deltas`).
- Never present LucidUI or UIClip output as objective truth — see Language Guidelines below.

## Backend Responsibilities (Not the Frontend's Job)

- Request validation (MIME type, file size, context values).
- Image decoding.
- Deterministic metric computation (LucidUI engine).
- LLM interpretation of metrics.
- UIClip inference.
- Building the ready-to-render `presentation` view (metric-section ordering, display-string formatting, LLM-observation-to-metric linking, fallback text).
- Comparison between LucidUI and UIClip output (not implemented yet — Phase 6).
- Final report generation and versioning.

If a frontend task seems to require computing or re-deriving a score, formatting a raw number for display, or deciding which LLM observation belongs to which metric, that is a sign the request belongs in the backend, not the frontend — flag it rather than implementing it client-side. It most likely already exists in `presentation`.

## Running the Backend Locally

The backend is a real, runnable FastAPI app — see the root [README.md](../../README.md) "Local Setup" for the full setup. Summary:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```text
API:      http://localhost:8000
Swagger:  http://localhost:8000/docs   (interactive, live schema — including PresentationReport)
OpenAPI:  http://localhost:8000/openapi.json
Health:   http://localhost:8000/api/v1/health
```

- **CORS** is wide open in local development (`allow_origins: ["*"]`, no credentials) — no special frontend configuration is needed to call the API from a dev server on a different port/origin.
- **No API key or model download is required to run the full pipeline**: `LLM_PROVIDER` and `UICLIP_PROVIDER` both default to `mock` in `backend/.env.example`, so every request returns a complete, real report shape (just with placeholder LLM/UIClip content) with zero external dependencies. Real providers (`gemini`, `huggingface`) are opt-in via `backend/.env` and change field *values*, never field *shapes* — see [api-contract.md](../api/api-contract.md).
- Alternatively, build against the static example files with no backend running at all — see [mock-development.md](mock-development.md).
- OCR (`pytesseract`) uses the `tesseract` binary when it is available on the host. Without it, `POST /analyses/single` still returns a report, but OCR-dependent metrics use empty OCR data and report no detected text.

## Planned User Flow

```text
Upload
-> Preview and Description
-> Start Analysis
-> Processing
-> Results Dashboard
```

1. **Upload** — user selects or drags a screenshot file.
2. **Preview and Description** — user sees a preview of the selected image and can optionally add a free-text description and pick a context (`general`/`expert`).
3. **Start Analysis** — user submits; the frontend calls `POST /api/v1/analyses/single` (`multipart/form-data`: `image`, optional `context`/`description`/`runLlm`/`runUiclip`).
4. **Processing** — this is a single request/response call, not a polling flow — the backend does not stream sub-stage progress or expose a job-status endpoint. The frontend shows `analyzing_metrics`/`interpreting`/`running_uiclip` purely as frontend-local, elapsed-time-inferred progress states (see [ui-states.md](ui-states.md)) while awaiting the one HTTP response.
5. **Results Dashboard** — the frontend renders `presentation` from the completed (or partially completed) report — see "Presentation Layer" below.

A separate **Compare** flow lets a user upload two screenshots instead of one — see "Variant Comparison Flow" below.

## Presentation Layer (Use This First)

`AnalysisReport.presentation` (see [presentation-schema.md](../api/presentation-schema.md)) is a ready-to-render view already built by the backend from `lucidui`, `llmInterpretation`, and `uiclip` — fixed-order metric sections with pre-formatted display strings, a composite summary, a UIClip summary card, recommendations, limitations, and a closing note.

**The frontend must not compute metric meaning, map fields, generate text, or calculate scores itself. It should render `presentation` directly.** If a dashboard component seems to need to interpret a raw or normalized metric value, resolve which metric an LLM observation belongs to, format a number for display, or judge whether a UIClip score is comparable to LucidUI's — that logic already exists in `presentation` and belongs in the backend, not in frontend code. `lucidui`, `llmInterpretation`, `uiclip`, `comparison`, and `timings` remain available (unchanged) for technical/raw views (e.g. `RawJsonViewer`), but the primary dashboard should be built against `presentation`.

## Dashboard Sections

Built from `presentation` (see "Presentation Layer" above):

1. **Analysis summary** — `presentation.title`, `presentation.summary`, overall `status`, `presentation.closingNote`.
2. **LucidUI metric sections** — `presentation.metricSections[]`, rendered in the given fixed order (7 cards: Contrast, Detected Elements, Grouping, Text Density, Colorfulness, Fitts's Law, Visual Balance — as of `corrected-v4`, the Visual Complexity, Hick's Law, and Whitespace & Alignment cards, and the target-size angle of Elements, were removed as Tier 3/"Problematic," see [docs/metrics/reliability-tiers.md](../metrics/reliability-tiers.md)).
3. **Composite score** — `presentation.composite`, with its fixed non-verdict `explanation`.
4. **UIClip evaluation card** — `presentation.uiclipSummary`, shown as a standalone, independent result — see "LucidUI vs. UIClip" below.
5. **Recommendations and limitations** — `presentation.recommendations[]`, `presentation.limitations[]`.
6. **Technical details** — raw JSON access (`RawJsonViewer`), for the underlying `lucidui`/`llmInterpretation`/`uiclip` sections `presentation` was built from (see [dashboard-data-mapping.md](dashboard-data-mapping.md)'s raw/technical table).

There is currently **no** "LucidUI versus UIClip comparison" section with real agreement/disagreement data — `comparison.agreementLevel` is always `"unavailable"` (Phase 6 not implemented). Do not build one against real data yet.

### LucidUI vs. UIClip: Two Independent Results, Not a Verdict

LucidUI's metric sections and the UIClip summary card are two **independent** evaluations of the same screenshot — one deterministic and explainable, one a learned model's holistic score (see [ADR-004](../architecture/decisions/ADR-004-uiclip-independent-evaluator.md)). The dashboard should let the user see both side by side and draw their own conclusions; it must not synthesize, merge, or imply agreement/disagreement between them — that synthesis doesn't exist yet (Phase 6), and even once it does, per [ADR-004](../architecture/decisions/ADR-004-uiclip-independent-evaluator.md) neither system is ground truth for the other. `presentation.uiclipSummary.comparableToLucidui` is always `false`, with `comparabilityNote` explaining why — always render that note next to the UIClip card rather than placing it beside `presentation.composite` as if the two scores were on the same scale.

### Variant Comparison Flow

A separate entry point (e.g. a "Compare" toggle next to the main single-analysis flow) lets a user upload two screenshots — variant A and variant B — and see both results plus relative deltas, without disturbing the single-analysis dashboard.

1. **Upload A and B** — two dropzones, same client-side MIME/size validation as the single flow (`image/jpeg`/`image/png`/`image/webp`, 20 MB).
2. **Preview and Description** — optionally describe each variant separately (`descriptionA`/`descriptionB`) and pick one shared context (`general`/`expert`) for both.
3. **Start Comparison** — the frontend calls `POST /api/v1/analyses/variants` (`multipart/form-data`: `imageA`, `imageB`, optional `context`/`descriptionA`/`descriptionB`/`runLlm`/`runUiclip`).
4. **Processing** — again a single request/response call (the backend runs both analyses concurrently server-side); show the same frontend-local progress states as the single flow while awaiting the one HTTP response.
5. **Results Dashboard** — render `variantA.presentation` and `variantB.presentation` exactly as the single-analysis dashboard already does (reuse the same components — do not fork the rendering logic), plus a delta view built from `deltas` (see [report-schema.md](../api/report-schema.md#variant-analysis-report-structure)): `deltas.metricDeltas[]` (per-metric `direction`, pre-formatted `rawDisplayA`/`rawDisplayB`), `deltas.compositeScoreDeltaDisplay`, `deltas.uiclipRawScoreDeltaDisplay`. Render all of these verbatim — never recompute a delta or reformat a number client-side.

**Language for deltas**: `deltas.metricDeltas[].direction` is one of `"higher"`, `"lower"`, `"equal"`, `"not_available"` — never render this as "variant A is better/worse than variant B." Color, if used, must indicate direction only (e.g. an up/down arrow), never a verdict — see Language Guidelines below.

See [dashboard-data-mapping.md](dashboard-data-mapping.md) for exact report-field-to-component mapping, and [component-contracts.md](component-contracts.md) for component-level responsibilities.

## Language Guidelines

LucidUI is a flashlight, not a judge — see [CLAUDE.md](../../CLAUDE.md) and [docs/product/terminology.md](../product/terminology.md). All frontend copy must follow this.

**Avoid**:

- "bad design" / "failed design"
- "UIClip says this is better"
- "scientifically proven quality"
- "accessibility passed"

**Prefer**:

- "below the selected reference threshold"
- "potential review area"
- "UIClip's raw model score" (never "preference score" or "quality score" — see `presentation.uiclipSummary.scoreType`, always `"Learned raw model score"`)
- "proxy signal"
- "estimated"
- "detected"
- "model-based observation"

**Color usage**: red and green (or any color coding) must not be used to automatically mean "bad" and "good." Use color to indicate direction relative to a threshold (e.g. above/below), not a verdict. Always pair color with explicit threshold/label text, never color alone.

## Related Documents

- [dashboard-data-mapping.md](dashboard-data-mapping.md)
- [ui-states.md](ui-states.md)
- [component-contracts.md](component-contracts.md)
- [mock-development.md](mock-development.md)
- [docs/api/api-contract.md](../api/api-contract.md)
- [docs/api/report-schema.md](../api/report-schema.md)
- [docs/api/presentation-schema.md](../api/presentation-schema.md)
