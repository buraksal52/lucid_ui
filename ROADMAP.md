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

### Phase 2B — Deterministic Metric Engine (not started)

- [ ] Legacy metric adapter
- [ ] JSON-safe serialization
- [ ] Weighted signal score
- [ ] Tests

## Phase 3 — LLM Interpretation Layer

- [ ] Provider interface
- [ ] Mock provider
- [ ] Anthropic provider
- [ ] Structured output
- [ ] Retry
- [ ] Fallback
- [ ] Metric evidence validation
- [ ] Tests

## Phase 4 — UIClip Adapter Foundation

- [ ] Evaluator interface
- [ ] Mock evaluator
- [ ] Disabled state
- [ ] Unavailable state
- [ ] Model metadata
- [ ] Description sources
- [ ] Tests

## Phase 5 — Real UIClip Integration

- [ ] Model loading
- [ ] Device selection
- [ ] Image preprocessing
- [ ] Sliding-window inference
- [ ] Preference score
- [ ] Inference timing
- [ ] Tests

## Phase 6 — LucidUI and UIClip Comparison

- [ ] Shared findings
- [ ] LucidUI-only findings
- [ ] UIClip-only findings
- [ ] Score difference
- [ ] Agreement level
- [ ] Tests

## Phase 7 — Variant Comparison

- [ ] Image A and image B
- [ ] Concurrent analysis
- [ ] Independent reports
- [ ] Relative deltas
- [ ] Tests

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
