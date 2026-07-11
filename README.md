# LucidUI

LucidUI is a research-oriented UI analysis system that compares two independent approaches to evaluating interface screenshots: a deterministic, explainable metric engine and UIClip, a learned vision-language model. An LLM interprets the deterministic metrics, and a Comparison Engine reports where the two evaluators agree or diverge.

## Flashlight, Not a Judge

LucidUI never declares a UI objectively good, bad, correct, or beautiful. It reports measurable signals, proxy metrics, threshold comparisons, and model observations — always with hedged, non-verdict language ("above/below a reference threshold," "potential review area," "proxy signal"). See [docs/product/terminology.md](docs/product/terminology.md) and [CLAUDE.md](CLAUDE.md).

## Planned Pipeline

```text
Image Upload
     |
     v
Validation and In-Memory Decoding
     |
     +----------------------------+
     |                            |
     v                            v
LucidUI Metric Engine       UIClip Evaluator
     |                            |
     v                            v
Deterministic Metric JSON   UIClip Result JSON
     |
     v
LLM Interpretation
     |
     +-------------+
                   |
                   v
           Comparison Engine
                   |
                   v
             Final Report
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full architectural explanation.

## Current Project Status: Phase 4

Phase 0 (documentation and architecture foundation), Phase 1 (FastAPI foundation), Phase 2A (image processing infrastructure), Phase 2B (the deterministic metric engine), Phase 3 (LLM interpretation), and Phase 4 (UIClip adapter foundation) are complete. `POST /api/v1/analyses/single` now runs the full pipeline: validate → decode → `MetricEngine.analyze()` (real legacy metrics, OCR included) → `LLMInterpretationService.interpret()` (real, deterministic-metric-grounded natural-language interpretation) → `UIClipEvaluationService.evaluate()` (independent image + description evaluation) → persist → return a full `AnalysisReport`. `GET /api/v1/analyses/{id}` and `/raw` return real, previously-computed reports, including both the LLM interpretation and the UIClip evaluation.

The LLM is an **interpreter only** — it never computes metrics, never invents evidence, and never receives the uploaded image or any screenshot; only the already-JSON-safe deterministic metric output and the analysis context (`general`/`expert`). It defaults to a deterministic, offline `MockLLMProvider` (no API key needed); setting `LLM_PROVIDER=gemini` plus `GEMINI_API_KEY` switches to a real Google Gemini provider. If the LLM fails or is unavailable for any reason, the deterministic analysis is still returned — `llmInterpretation.status` becomes `unavailable`/`failed` rather than discarding the rest of the report.

UIClip is an **independent learned evaluator** — never ground truth, never merged with or compared against LucidUI's metrics yet. It receives only the decoded screenshot and the submitted (or documented `generic` fallback) description — never deterministic metrics or LLM output. As of Phase 4 only a deterministic, offline `MockUIClipProvider` exists (`UICLIP_PROVIDER=mock`, the default and only implemented value); **no official/real UIClip model is integrated** — see [docs/research/uiclip-integration.md](docs/research/uiclip-integration.md) for the verified findings on official model/weight availability and why real integration is scoped to Phase 5. `uiclip.normalizedQualityScore` is intentionally always `null`: the official UIClip paper computes an uncalibrated CLIP-style dot-product score with no confirmed universal 0-100/0-1 normalization, so none is invented here. `comparison` remains an `unavailable` placeholder — agreement/difference computation is Phase 6.

OCR uses `pytesseract`, which requires the external `tesseract` binary to be installed on the host at runtime (not required for the test suite, which mocks OCR, the LLM provider, and the UIClip provider). See [ROADMAP.md](ROADMAP.md) for the full phased plan. The frontend is still not implemented.

## Planned Features

- Deterministic UI metric analysis (contrast, edge density, element density, Hick's/Fitts's Law estimates, whitespace, alignment, colorfulness, visual balance, and more — see [docs/metrics/metric-catalog.md](docs/metrics/metric-catalog.md)).
- LLM interpretation of deterministic metrics, grounded in metric evidence.
- UIClip evaluation as an independent, learned UI preference signal.
- Agreement/discrepancy comparison between LucidUI and UIClip.
- Single-image analysis and two-image variant comparison.
- A React dashboard visualizing all of the above without re-deriving any scores client-side.

## Privacy Principles

- Raw screenshots are processed locally, inside the backend.
- Uploaded images are not written to disk by default.
- Raw screenshots are never sent to the LLM provider — only deterministic metric JSON is.
- UIClip is planned to run locally, not as a hosted third-party API call.

See [docs/architecture/privacy-model.md](docs/architecture/privacy-model.md) for the full model.

## Local Setup (Backend, Phase 4)

The backend is a FastAPI application under `backend/`. `POST /api/v1/analyses/single` accepts an uploaded image, decodes it, runs the real deterministic metric engine (`app.metrics.MetricEngine`), interprets the result with `app.llm.LLMInterpretationService`, evaluates the image independently with `app.uiclip.UIClipEvaluationService`, persists the resulting report, and returns it. Only a mock UIClip evaluator exists — no official/real model is loaded yet (Phase 5).

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows (cmd/PowerShell)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**External dependency (OCR)**: the metric engine's OCR stage uses `pytesseract`, a thin Python wrapper around the `tesseract` command-line binary. `pip install -r requirements.txt` installs the Python wrapper only — the `tesseract` binary itself must be installed separately on the host (e.g. `brew install tesseract` on macOS, `apt-get install tesseract-ocr` on Debian/Ubuntu) before OCR calls will actually run. It is not required to run the test suite, which mocks `pytesseract.image_to_data`.

**LLM configuration**: `LLM_PROVIDER` defaults to `mock` — a deterministic, offline provider that needs no API key and never makes a network call, so the app and test suite run out of the box. Set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=<your key>` (see `.env.example`) to use a real Google Gemini model instead; if `gemini` is selected without a key, LLM interpretation reports `unavailable` rather than failing the request. Screenshots are never sent to any LLM provider — only deterministic metric JSON and the analysis context.

**UIClip configuration**: `UICLIP_PROVIDER` defaults to `mock` — a deterministic, offline evaluator that needs no model download and never makes a network call. It is currently the *only* implemented value; setting it to anything else gracefully degrades to `uiclip.status = "unavailable"` rather than raising. UIClip receives only the decoded screenshot and the submitted `description` form field (or a documented generic fallback if omitted) — never the deterministic metrics or LLM output.

Once running:

```text
API:      http://localhost:8000
Swagger:  http://localhost:8000/docs
Health:   http://localhost:8000/api/v1/health
```

Run the backend test suite:

```bash
cd backend
python -m pytest
```

## Repository Structure

```text
lucidui/
├── CLAUDE.md              Rules and workflow for Claude Code
├── README.md              This file
├── ROADMAP.md              Phased development plan
├── ARCHITECTURE.md         Architecture overview
│
├── backend/                FastAPI application (Phase 4 — deterministic analysis + LLM interpretation + mock UIClip; no real UIClip model yet)
├── frontend/                (empty — not implemented yet)
├── samples/                 (empty — reserved for sample screenshots)
│
└── docs/
    ├── product/              Product scope, terminology, non-goals
    ├── architecture/          System overview, pipeline, privacy model, ADRs
    ├── metrics/               Metric catalog, scoring, limitations, references
    ├── api/                   API contract, report schema, error codes, examples
    ├── frontend/              Frontend guide, data mapping, UI states, components
    └── research/              Research questions, UIClip integration, evaluation plan
```

## Documentation Links

- [CLAUDE.md](CLAUDE.md) — mandatory rules for future development.
- [ROADMAP.md](ROADMAP.md) — phased plan, Phase 0 through Phase 11.
- [ARCHITECTURE.md](ARCHITECTURE.md) — architecture overview and dependency direction.
- [docs/product/product-scope.md](docs/product/product-scope.md) — what LucidUI is and isn't.
- [docs/metrics/metric-catalog.md](docs/metrics/metric-catalog.md) — every planned metric, with purpose and limitations.
- [docs/api/api-contract.md](docs/api/api-contract.md) — planned API endpoints.
- [docs/api/report-schema.md](docs/api/report-schema.md) — planned analysis report shape.
- [docs/frontend/FRONTEND_GUIDE.md](docs/frontend/FRONTEND_GUIDE.md) — guide for independent frontend development.
- [docs/research/research-questions.md](docs/research/research-questions.md) — open research questions this project is designed to eventually help answer.

## Development Phases

See [ROADMAP.md](ROADMAP.md) for the complete list. In short: Phase 0 (documentation, current) → Phase 1 (FastAPI foundation) → Phase 2 (deterministic metric engine) → Phase 3 (LLM interpretation) → Phase 4–5 (UIClip integration) → Phase 6–7 (comparison and variant analysis) → Phase 8 (developer tools) → Phase 9 (persistence) → Phase 10 (research benchmarking) → Phase 11 (production readiness).

## Status Note

The backend (`backend/`) is runnable. Phase 1 delivered the FastAPI foundation: routing, configuration, structured errors, and an in-memory repository. Phase 2A added real image upload: `POST /api/v1/analyses/single` validates (MIME type, size, corruption) and decodes an uploaded JPEG/PNG/WebP entirely in memory — never written to disk. Phase 2B added `app.metrics.MetricEngine`, a production-facing adapter around the validated legacy deterministic metric engine (`backend/reference/legacy_metric_engine.py`, immutable — see [CLAUDE.md](CLAUDE.md)), wired into the endpoint and covered by regression-equivalence tests. Phase 3 added `app.llm.LLMInterpretationService`: it builds a JSON-only prompt from the deterministic metric result (never the image), calls a configured `LLMProvider` (mock by default, real Gemini when configured), validates the structured response (including a metric-evidence check), and populates `AnalysisReport.llmInterpretation`. Any LLM failure degrades gracefully — the deterministic report is always returned regardless.

Phase 4 added `app.uiclip.UIClipEvaluationService`: it resolves the description source (`user` if submitted, the already-documented `generic` fallback otherwise), calls a configured `UIClipProvider` (mock only, for now) with the decoded image and description, validates the response, and populates `AnalysisReport.uiclip`. UIClip is independent of both LucidUI's metrics and the LLM's output — neither module can see the other's data. Only `MockUIClipProvider` exists; the official UIClip model (arXiv:2404.12500, weights on Hugging Face under `biglab/`, MIT licensed) was researched but not integrated — no verified official inference repository was found, the exact score-normalization procedure is unconfirmed from primary source, and real integration (model loading, sliding-window inference) was already scoped to Phase 5 by [ADR-005](docs/architecture/decisions/ADR-005-mock-providers-before-real-integrations.md) before this phase began. `comparison.agreementLevel` remains `unavailable` — agreement/discrepancy computation is Phase 6 (see [ROADMAP.md](ROADMAP.md)). The frontend (`frontend/`) is still not implemented.
