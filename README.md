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

## Current Project Status: Phase 2A

Phase 0 (documentation and architecture foundation) and Phase 1 (FastAPI foundation) are complete. Phase 2A (image processing infrastructure) is also complete: `POST /api/v1/analyses/single` now accepts a real `multipart/form-data` image upload (JPEG, PNG, or WebP, max 20 MB), validates and decodes it entirely in memory (never written to disk), and returns a temporary "accepted" response with the decoded image's metadata. No deterministic metric, LLM, or UIClip stage runs yet — those land in Phase 2B onward. See [ROADMAP.md](ROADMAP.md) for the full phased plan. The frontend is still not implemented.

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

## Local Setup (Backend, Phase 2A)

The backend is a FastAPI application under `backend/`. As of Phase 2A, `POST /api/v1/analyses/single` accepts and decodes a real uploaded image, but does not yet run any analysis — no metric, LLM, or UIClip stage exists yet (Phase 2B onward).

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows (cmd/PowerShell)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

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
├── backend/                FastAPI application (Phase 2A — image upload and validation only)
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

The backend (`backend/`) is runnable. Phase 1 delivered the FastAPI foundation: routing, configuration, structured errors, and an in-memory repository. Phase 2A added real image upload: `POST /api/v1/analyses/single` now validates (MIME type, size, corruption) and decodes an uploaded JPEG/PNG/WebP entirely in memory — never written to disk — and returns its metadata (width, height, format, aspect ratio, orientation, file size). It does not yet perform real deterministic-metric analysis, real LLM interpretation, or real UIClip inference — those land in later phases (see [ROADMAP.md](ROADMAP.md)). The frontend (`frontend/`) is still not implemented.
