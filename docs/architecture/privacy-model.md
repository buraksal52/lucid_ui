# Privacy Model

LucidUI's privacy rules are mandatory and apply to every phase of implementation. See [CLAUDE.md](../../CLAUDE.md) for the enforced rules.

## Principles

- **Raw screenshots are processed locally, inside the backend process.** Decoding, computer vision, and OCR all run in-process, on the machine running the backend.
- **Uploaded images are not written to disk by default.** Files are validated and decoded directly from the uploaded bytes in memory. Any future opt-in persistence (e.g. for debugging or dataset building) must be explicit, off by default, and documented before implementation.
- **Raw screenshots are never sent to the LLM provider.** The LLM interpretation stage receives only the deterministic metric JSON produced by the LucidUI metric engine — numbers, labels, and thresholds, not pixels. See [ADR-003](decisions/ADR-003-json-only-llm-input.md).
- **UIClip is planned to run locally**, not as a hosted third-party API. This keeps the image itself from ever leaving the backend's local environment, even for the learned-model evaluation path. See [docs/research/uiclip-integration.md](../research/uiclip-integration.md).

## Local Processing vs. External API Usage

| Component | Data involved | Where it runs | Leaves the backend? |
|---|---|---|---|
| Image validation & decoding | Raw image bytes | Local, in-memory | No |
| LucidUI metric engine (CV/OCR) | Raw image bytes | Local, in-memory | No |
| UIClip evaluator | Raw image bytes, description text | Local (planned) | No |
| LLM interpretation | Deterministic metric JSON only | External API call (e.g. Anthropic) | Yes — JSON only, never the image |
| Persistence (Phase 9+) | Metric JSON, report metadata | Local database | No raw images stored by default |

## Consequences for Future Phases

- Any new backend feature that touches the uploaded image must confirm it does not write the file to disk and does not forward image bytes to an external API.
- If a future phase introduces optional disk persistence or cloud storage of images, it must be a separate, explicitly instructed change with its own documentation update — not a silent side effect of another feature.
- The frontend must never be asked to upload images directly to a third-party service; all uploads go through the LucidUI backend.
