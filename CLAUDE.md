# CLAUDE.md

Instructions for Claude Code when working on the LucidUI repository. Read this file before starting any task.

## Project Identity

- LucidUI analyzes UI screenshots using a deterministic, explainable metric engine (classical computer vision, OCR, and HCI/cognitive-science-inspired proxy metrics).
- LucidUI compares its deterministic metrics with UIClip, a learned vision-language model used as an **independent evaluator**, not as ground truth.
- An LLM interprets deterministic metric JSON only. It never receives raw screenshots.
- The React frontend is developed independently from the backend and consumes only the documented API contract.
- See [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [ROADMAP.md](ROADMAP.md) for full context.

## Product Positioning: Flashlight, Not a Judge

LucidUI never claims a UI is objectively good, bad, correct, incorrect, beautiful, or ugly. It reports measurable signals, proxy metrics, threshold comparisons, model observations, agreements, and discrepancies. Use language such as "higher/lower," "above/below a reference threshold," "potential review area," "estimated," "detected," and "proxy signal." Never use verdict language. See [docs/product/terminology.md](docs/product/terminology.md) and [docs/frontend/FRONTEND_GUIDE.md](docs/frontend/FRONTEND_GUIDE.md).

## Mandatory Rules

- Do not modify validated legacy metric formulas unless explicitly instructed.
- Do not send raw images to an LLM.
- Do not write uploaded images to disk by default.
- Do not treat proxy metrics as direct cognitive measurements.
- Do not treat UIClip as ground truth.
- Do not calculate correlation from a single screenshot.
- Do not put business logic inside FastAPI route functions. Routes handle HTTP concerns only; services and pipelines hold logic.
- Do not modify the frontend unless a task explicitly targets the frontend.
- Do not continue to a new roadmap phase without explicit instruction.
- Use Python type hints everywhere in backend code.
- Use structured JSON outputs for all API responses and LLM outputs.
- Add tests for every backend feature.
- Keep APIs backward-compatible whenever possible; bump `schemaVersion` when contracts change.
- Update relevant documentation when contracts change.

## Development Workflow

For every future task:

1. Read `CLAUDE.md`.
2. Read `ROADMAP.md`.
3. Read the relevant architecture and API documents (`ARCHITECTURE.md`, `docs/architecture/`, `docs/api/`).
4. Implement only the requested phase — do not pull in later-phase work.
5. Run relevant tests.
6. Report created and modified files.
7. Report unresolved risks.
8. Stop and wait for the next task.

## Current Status

Phase 0 (Documentation and Architecture Foundation) is complete. No backend or frontend implementation exists yet. Do not begin Phase 1 unless explicitly instructed.
