# ROADMAP

This roadmap defines the phased development plan for LucidUI. Each phase must be completed and explicitly approved before the next begins, per [CLAUDE.md](CLAUDE.md).

## Phase 0 — Documentation and Architecture Foundation

- [x] Repository structure
- [x] Product scope
- [x] Architecture rules
- [x] Metric documentation
- [x] API contract
- [x] Frontend guide
- [x] Research plan

## Phase 1 — FastAPI Foundation

- [x] FastAPI application
- [x] Configuration
- [x] Health endpoint
- [x] CORS
- [x] Global JSON error handling
- [x] Initial Pydantic schemas
- [x] In-memory repository
- [x] Mock single-analysis response
- [x] Tests

## Phase 2 — Image Upload and Deterministic Metric Engine

### Phase 2A — Image Processing Infrastructure (complete)

- [x] MIME validation
- [x] 20 MB file limit
- [x] In-memory decoding
- [x] Image metadata
- [x] Tests

### Phase 2B — Deterministic Metric Engine (complete)

#### Phase 2B-1 — Legacy Metric Engine Adapter (complete)

- [x] Legacy metric adapter (`app.metrics.MetricEngine`, callable from Python; not yet wired into the API)
- [x] JSON-safe serialization
- [x] Weighted signal score
- [x] Tests (including legacy regression-equivalence)

#### Phase 2B-2 — API Integration (complete)

- [x] Connect `MetricEngine` to `POST /api/v1/analyses/single` (via `AnalysisService`, injected through `get_metric_engine()`)
- [x] Persist deterministic metric reports (`AnalysisRepository.save()`, exercised for the first time)
- [x] Update the endpoint's success response to the full report shape (`AnalysisReport`, replacing Phase 2A's temporary `AnalysisAcceptedResponse`)

## Phase 3 — LLM Interpretation Layer (first version complete)

- [x] Provider interface (`app.llm.provider.LLMProvider`)
- [x] Mock provider (`app.llm.mock_provider.MockLLMProvider`, default, no API key required)
- [x] Gemini provider (`app.llm.gemini_provider.GeminiLLMProvider`, via the official `google-genai` SDK — chosen over Anthropic for this phase)
- [x] Structured output (Gemini's native JSON schema constraint on `LLMStructuredOutput`, plus Pydantic validation in `LLMInterpretationService`)
- [ ] Retry (not implemented — a single provider call per analysis; failures degrade to `unavailable`/`failed` rather than retrying)
- [ ] Fallback (not implemented — no automatic secondary-provider chain; `LLMStatus.FALLBACK` remains defined but unused)
- [x] Metric evidence validation (basic/structural: every observation must cite at least one metric path; not deep JSON-path resolution against `lucidui`)
- [x] Tests (`backend/tests/test_llm_interpretation.py`, all failure paths, no real network call)

## Phase 4 — UIClip Adapter Foundation (complete)

- [x] Evaluator interface (`app.uiclip.provider.UIClipProvider`)
- [x] Mock evaluator (`app.uiclip.mock_provider.MockUIClipProvider`, default and only implemented provider)
- [x] Disabled state (`runUiclip=false` → `uiclip.status = "disabled"`, `uiclipMs = 0`, no provider call)
- [x] Unavailable state (no/misconfigured provider → `uiclip.status = "unavailable"`, deterministic analysis and LLM interpretation still returned)
- [x] Model metadata (`uiclip.modelVersion`, e.g. `"mock-uiclip-v1"`)
- [x] Description sources (`user` when submitted, documented `generic` fallback when missing/blank — never invented ad hoc)
- [x] Tests (`backend/tests/test_uiclip_evaluation.py`, `backend/tests/test_single_analysis.py`, `backend/tests/test_report_retrieval.py`)
- [x] Official UIClip execution options verified (paper, HF weights, license — see docs/research/uiclip-integration.md); real model integration confirmed blocked/out of scope for this phase, deferred to Phase 5 per ADR-005 (unchanged from the original plan)

## Presentation Report Layer (additive, phase-independent)

- [x] `AnalysisReport.presentation` — a ready-to-render view over `lucidui`/`llmInterpretation`/`uiclip`, additive and backward-compatible (`app/schemas/presentation.py`, `app/presentation/report_builder.py`)
- [x] Fixed-order, ready-to-render metric sections (contrast, visual complexity, elements & target size, Hick's Law, grouping, text density, whitespace & alignment, colorfulness, Fitts's Law, visual balance)
- [x] LLM observation → metric section evidence matching, with a deterministic fallback when no observation matches
- [x] Composite and UIClip summary cards, both explicitly non-verdict
- [x] Tests (`backend/tests/test_presentation_report_builder.py`, `backend/tests/test_presentation_api.py`)

This does not compute any new metric, re-run `MetricEngine`, re-call Gemini, or re-call UIClip — see [docs/api/presentation-schema.md](docs/api/presentation-schema.md). It does not advance Phase 5 (real UIClip integration) or Phase 6 (comparison), both still scoped as below.

## Phase 5 — Real UIClip Integration

- [x] Model loading
- [x] Device selection
- [x] Image preprocessing
- [x] Sliding-window inference
- [x] Preference score
- [x] Inference timing
- [x] Tests

## Phase 6 — LucidUI and UIClip Comparison

- [x] Shared findings
- [x] LucidUI-only findings
- [x] UIClip-only findings
- [x] Score difference
- [x] Agreement level
- [x] Tests

## Phase 7 — Variant Comparison

- [x] Image A and image B (`POST /api/v1/analyses/variants`, multipart `imageA`/`imageB`)
- [x] Concurrent analysis (`VariantAnalysisService.create_variant_analysis` — `asyncio.gather`/`asyncio.to_thread` over two unmodified `AnalysisService.create_single_analysis` calls)
- [x] Independent reports (`variantA`/`variantB`, each a full, independently-persisted `AnalysisReport` — also retrievable via the existing `GET /analyses/{analysisId}`)
- [x] Relative deltas (`deltas` — pure `app.presentation.variant_delta_builder.build_variant_deltas`, variant B minus variant A, non-verdict `higher`/`lower`/`equal`/`not_available` direction)
- [x] Tests (`backend/tests/test_variant_analysis.py`, `backend/tests/test_variant_delta_builder.py`)

## Phase 8 — Backend Developer Tools

- [ ] CLI
- [ ] Benchmark folder runner
- [ ] Streamlit internal dashboard
- [ ] JSON export

## Phase 9 — Persistence

- [ ] Repository interface
- [ ] PostgreSQL or Supabase adapter
- [ ] Analysis history
- [ ] Version metadata
- [ ] No raw-image storage by default

## Phase 10 — Research Benchmarking

- [ ] Dataset runner
- [ ] Human ratings
- [ ] Pearson correlation
- [ ] Spearman correlation
- [ ] Confidence intervals
- [ ] CSV and JSON export

## Phase 11 — Production Readiness

- [ ] Docker
- [ ] Logging
- [ ] Request IDs
- [ ] Rate limiting
- [ ] Timeouts
- [ ] Secure CORS
- [ ] CI
- [ ] Deployment documentation
