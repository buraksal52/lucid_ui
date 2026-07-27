# LucidUI

LucidUI looks at a screenshot of a user interface and reports what it measures — contrast, text density, element counts, and more — without declaring the design "good" or "bad." It also runs a second, independent AI model (UIClip) on the same screenshot, and an LLM explains the numbers in plain language. Everything is shown side by side so a human can decide what it means.

## Why "Flashlight, Not a Judge"

LucidUI never says a UI is objectively good, bad, ugly, or correct. It only reports things like "this text is below the recommended contrast threshold" or "this screen has an estimated N visual groupings." Think of it as a flashlight that points at things worth looking at — not a judge that hands down a verdict. See [CLAUDE.md](CLAUDE.md) for the full set of rules this project follows.

## How a Screenshot Flows Through the System

```text
1. You upload a screenshot
2. LucidUI measures it directly           UIClip (an independent AI model)
   (contrast, element counts...)          scores it, separately
              |                                      |
              v                                      v
      Deterministic metrics                    UIClip's own score
              |
              v
      An LLM explains the metrics in plain language
              |
              v
        You get one combined report
```

The deterministic metrics and UIClip never see each other's output while they're computed — they run independently, so neither one can bias the other. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical breakdown.

## What Works Today

- **Upload one screenshot** (`POST /api/v1/analyses/single`) and get back a full report: measurements, an LLM explanation, and an independent UIClip score.
- **Upload two screenshots to compare** (`POST /api/v1/analyses/variants`) — useful for "which version of this screen is better in which specific ways" — both are analyzed independently and the differences are highlighted.
- **Look up a past report** (`GET /api/v1/analyses/{id}`).
- **A React dashboard** (`frontend/`) that displays all of the above — upload, view a single report, or compare two screenshots side by side.

## What's Deliberately Not There Yet

- **A side-by-side "do LucidUI and UIClip agree?" comparison.** Both scores are shown, but nothing yet calculates whether they agree or point out where they diverge — no agreement/disagreement logic has been built.
- **Saving reports to a real database.** Reports currently live in memory and disappear on restart.
- **Production hardening** — Docker, rate limiting, deployment docs.

See [ROADMAP.md](ROADMAP.md) for the detailed, phase-by-phase plan (note: a couple of its checklist items are ahead of what's actually wired up yet — when in doubt, this README and the code are the source of truth).

## The Three Independent Pieces

1. **The metric engine** — plain computer vision and OCR (contrast, element counts, grouping, text density, and more). No AI model involved; every number is explainable and traceable back to the pixels. See [docs/metrics/metric-catalog.md](docs/metrics/metric-catalog.md) for what each one measures, and [docs/metrics/reliability-tiers.md](docs/metrics/reliability-tiers.md) for how much to trust each one — some are solid, some are approximate, and the least-defensible ones (edge density, Hick's Law, small targets, whitespace/alignment) were removed entirely as of `corrected-v4`.
2. **UIClip** — a separately trained AI model (not built by this project) that scores a screenshot on its own. It's an opinion to compare against, never treated as the "correct" answer. Defaults to a lightweight offline stand-in; the real model can be turned on (see Setup below).
3. **The LLM interpretation layer** — reads only the metric engine's numbers (never the screenshot itself) and explains them in plain language. It can only talk about what the numbers actually say — it's not allowed to invent findings.

## Privacy

- Screenshots are processed in memory and are never written to disk by default.
- The LLM never sees your screenshot — only the computed numbers.
- UIClip runs locally rather than being sent to a third-party API.

Full details: [docs/architecture/privacy-model.md](docs/architecture/privacy-model.md).

## Running It Locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

By default, both the LLM step and UIClip step run in offline "mock" mode — no API key, no model download, no network calls, so everything works out of the box. Copy `backend/.env.example` to `backend/.env` to turn on the real providers:

- **Real LLM explanations**: set `LLM_PROVIDER=gemini` and add a `GEMINI_API_KEY`.
- **Real UIClip model**: set `UICLIP_PROVIDER=huggingface` (downloads the official model from Hugging Face on first use).
- **OCR** (needed for text-related metrics): install the `tesseract` command-line tool separately (`brew install tesseract` on macOS, `apt-get install tesseract-ocr` on Debian/Ubuntu). If it's missing, analysis still works — text metrics just come back empty instead of failing the whole request.

Once running:

```text
API:      http://localhost:8000
Swagger:  http://localhost:8000/docs
Health:   http://localhost:8000/api/v1/health
```

Run the tests:

```bash
cd backend
python -m pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend running at `http://localhost:8000`. It's built independently against the documented API contract — see [docs/frontend/FRONTEND_GUIDE.md](docs/frontend/FRONTEND_GUIDE.md).

## Repository Layout

```text
lucidui/
├── CLAUDE.md       Rules this project follows during development
├── README.md       This file
├── ROADMAP.md      Phase-by-phase plan
├── ARCHITECTURE.md Full architecture explanation
│
├── backend/        FastAPI application — metrics, LLM, UIClip, API
├── frontend/        React dashboard
├── samples/          Reserved for sample screenshots
│
└── docs/
    ├── product/        What LucidUI is and isn't, terminology
    ├── architecture/    System design, privacy model, decision records
    ├── metrics/         Every metric explained, plus how reliable each one is
    ├── api/             API contract and report format
    ├── frontend/        Guide for frontend development
    └── research/        Open research questions, evaluation plans
```

## Where to Read More

- [docs/product/product-scope.md](docs/product/product-scope.md) — what LucidUI is and isn't.
- [docs/metrics/metric-catalog.md](docs/metrics/metric-catalog.md) — every metric, explained.
- [docs/metrics/reliability-tiers.md](docs/metrics/reliability-tiers.md) — which metrics to trust, and which to take with a grain of salt.
- [docs/api/api-contract.md](docs/api/api-contract.md) — the API endpoints.
- [docs/api/report-schema.md](docs/api/report-schema.md) — the shape of a full analysis report.
- [docs/frontend/FRONTEND_GUIDE.md](docs/frontend/FRONTEND_GUIDE.md) — building against the API without needing the backend running.
- [ROADMAP.md](ROADMAP.md) — the detailed phase-by-phase plan.
