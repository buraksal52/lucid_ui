# CLAUDE.md

Instructions for Claude Code when working on the LucidUI repository.

Always read this document before starting any implementation.

---

# Project Identity

LucidUI is a research-oriented UI analysis platform.

It analyzes UI screenshots using:

- deterministic computer vision
- OCR
- explainable HCI-inspired proxy metrics

LucidUI compares those deterministic metrics with **UIClip**, a learned vision-language model acting as an **independent evaluator**, never as ground truth.

An LLM interprets deterministic metric JSON only.

Raw screenshots must never be sent to an LLM.

The React frontend is developed independently and communicates only through the documented API contracts.

Project documentation:

- README.md
- ROADMAP.md
- ARCHITECTURE.md
- docs/

---

# Product Philosophy

## Flashlight, Not a Judge

LucidUI does **not** determine whether a design is objectively good or bad.

It reports:

- measurable signals
- proxy metrics
- threshold comparisons
- observations
- agreements
- discrepancies
- review areas

Prefer wording such as:

- detected
- estimated
- above reference threshold
- below reference threshold
- proxy signal
- higher
- lower
- potential review area

Avoid wording such as:

- bad UI
- wrong design
- ugly
- scientifically proven
- objectively better

---

# Architecture Rules

The dependency direction is strict.

```
API
→ Services
→ Pipelines
→ Domain Interfaces
→ Adapters
```

Never create reverse dependencies.

The following modules must remain independent:

- metrics
- llm
- uiclip
- repositories

The metric engine must never import the LLM layer.

The UIClip adapter must never import deterministic metric logic.

Repositories must never depend on FastAPI.

Routes must only handle HTTP concerns.

Business logic belongs in services and pipelines.

---

# Legacy Metric Engine

The deterministic metric engine is considered validated scientific logic.

Do **not** modify:

- mathematical formulas
- thresholds
- heuristics
- weighting rules
- output semantics

unless explicitly instructed.

Allowed:

- modularization
- wrappers
- dependency injection
- documentation
- testing
- code organization

Behavior must remain identical.

---

# LLM Rules

LLMs are interpreters.

They must never:

- invent metrics
- contradict deterministic measurements
- fabricate evidence
- infer information not present in the metric JSON

Every recommendation must be traceable to one or more deterministic metrics.

Measurement does not imply optimization direction. A metric having a high or low value is never, by itself, a reason to recommend changing it — see docs/metrics/interpretation-taxonomy.md for which metrics may support a recommendation (Actionable), may be surfaced for cautious review only (Diagnostic), or must never independently generate a prescriptive or quality-judgment claim (Descriptive), and `backend/app/llm/interpretation_guard.py` for the deterministic enforcement of this rule.

LLMs receive JSON only.

Raw screenshots must never be sent to an LLM.

---

# UIClip Rules

UIClip is an independent learned evaluator.

It is not:

- ground truth
- objective quality
- scientific proof

UIClip and LucidUI are complementary systems.

They may agree.

They may disagree.

Both outputs should be shown.

---

# Image Processing Rules

Uploaded images must:

- remain in memory
- never be written to disk by default
- never be logged
- never be exposed to external services unless explicitly configured

The same uploaded bytes should be reused to generate:

- OpenCV image
- Pillow image

---

# API Rules

Public API schemas are contracts.

Do not rename:

- endpoints
- JSON fields
- enum values

unless explicitly instructed.

Backward compatibility has priority.

When breaking changes are required:

- bump schemaVersion
- update documentation

---

# Metric Rules

Every metric should expose:

- raw value
- normalized value
- interpretation
- limitations
- threshold (when applicable)

Never discard raw values.

Never expose normalized values without preserving the originals.

---

# Coding Rules

Use:

- Python type hints
- Pydantic models
- dependency injection
- composition over inheritance
- explicit code over magic

Avoid:

- unnecessary abstractions
- premature optimization
- overly clever implementations

Do not introduce design patterns unless they clearly reduce future complexity.

---

# Testing Rules

Every backend feature must include:

- success tests
- validation tests
- failure tests

Bug fixes should include regression tests whenever practical.

Tests must not require:

- external APIs
- internet access
- GPU
- UIClip
- OCR
- LLM providers

unless explicitly requested.

---

# Logging Rules

Never log:

- uploaded image bytes
- API keys
- secrets
- sensitive user data

Log:

- application lifecycle
- requests
- analysis creation
- recoverable failures
- unexpected exceptions

---

# Documentation Rules

Documentation is part of the implementation.

Whenever public behavior changes, update:

- README.md
- ROADMAP.md
- API documentation
- architecture documentation

before considering the task complete.

---

# Development Workflow

For every task:

1. Read CLAUDE.md.
2. Read ROADMAP.md.
3. Read relevant documentation.
4. Implement only the requested phase.
5. Run relevant tests.
6. Report modified files.
7. Report remaining risks.
8. Stop.

Never continue into the next roadmap phase unless explicitly instructed.

---

# When Uncertain

Do not guess.

Do not invent behavior.

Prefer asking for clarification over implementing assumptions.

---

# Definition of Success

A task is complete only when:

- requested functionality works
- tests pass
- documentation is updated
- architecture rules are respected
- API contracts remain consistent
- no unrelated code has been modified