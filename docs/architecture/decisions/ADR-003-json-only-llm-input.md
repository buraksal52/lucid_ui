# ADR-003: LLM Receives Deterministic Metric JSON Only

## Status

Accepted

## Context

LucidUI uses an LLM to interpret the output of its deterministic metric engine in natural language. The LLM could theoretically be given the raw screenshot (as many multimodal LLMs support image input), or it could be given only the structured metric data the engine already computed.

## Decision

The LLM interpretation stage receives only the deterministic metric JSON (raw values, normalized signals, composite score, thresholds) produced by the LucidUI metric engine. It never receives the raw screenshot image.

## Rationale

- **Privacy**: raw screenshots may contain sensitive or unreleased UI. Restricting the LLM call to numeric/structured data avoids sending image content to an external API provider. See [privacy-model.md](../privacy-model.md).
- **Explainability**: forcing the LLM to reason over named, sourced metrics (not raw pixels) keeps its output traceable to specific evidence, which is required for the "metric evidence" field in LLM observations. See [docs/api/report-schema.md](../../api/report-schema.md).
- **Independence from UIClip**: keeping the LLM's input scoped to LucidUI's own metrics (not the image, not UIClip's output) preserves LucidUI and UIClip as independent evaluators that are compared, not merged. See [ADR-004](ADR-004-uiclip-independent-evaluator.md).

## Consequences

- The LLM provider interface accepts a metric JSON payload, not an image payload.
- If a future phase wants image-grounded LLM interpretation, that is a distinct, explicitly-scoped decision requiring its own ADR and privacy review — it is not an incremental extension of this stage.
- LLM observations must cite which metric(s) they are based on (metric evidence), since the LLM has no independent visual access to verify claims.
