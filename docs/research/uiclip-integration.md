# UIClip Integration

This document explains the plan for integrating UIClip as LucidUI's independent learned evaluator. See [ADR-004](../architecture/decisions/ADR-004-uiclip-independent-evaluator.md) and [ADR-005](../architecture/decisions/ADR-005-mock-providers-before-real-integrations.md) for the underlying architectural decisions.

## Verified Findings (Phase 4)

The sections below were originally written in Phase 0 as a plan, before the official UIClip source had been independently confirmed. As part of Phase 4, the official sources were researched directly; findings:

- **Paper**: Jason Wu, Yi-Hao Peng, Xin Yue Li, Amanda Swearngin, Jeffrey P. Bigham, Jeffrey Nichols. "UIClip: A Data-driven Model for Assessing User Interface Design." UIST 2024. [arXiv:2404.12500](https://arxiv.org/abs/2404.12500). Official project page: [uimodeling.github.io/uiclip](https://uimodeling.github.io/uiclip/).
- **Model weights**: publicly available on Hugging Face under `biglab/uiclip_jitteredwebsites-2-224-paraphrased` (and related `webpairs`/`humanpairs` checkpoint variants), MIT licensed. Architecture is CLIP B/32-based, loadable via the standard `transformers` library (`CLIPModel`/`CLIPProcessor`).
- **No official, verified, runnable inference repository was found.** The paper states only an intent to release code ("we plan to release all the training code, data, and models") — a commitment, not a confirmed permanent repository. Only the Hugging Face model card exists as a usage reference.
- **Score semantics**: per the paper's own text, the score is "the dot product between the image embedding and the text embedding" — an uncalibrated, CLIP-style similarity/logit value. The paper does **not** describe a softmax/reference-prompt calibration step for the primary reported score, and does not state a documented 0-1 or 0-100 range. (A third-party summary of the Hugging Face model card separately described an optional `NORMALIZE_SCORING` softmax procedure; this could not be independently verified against primary source code and is not relied upon here — see CLAUDE.md "Do not invent behavior.")
- **Input**: a screenshot plus a natural-language description, exactly as already documented below. Official inference applies a sliding-window strategy at 224×224 resolution.
- **Runtime**: requires `torch` and `transformers` — both explicitly excluded from earlier LucidUI phases (see prior phase instructions: "Do not add: torch, transformers ... those belong to later phases"). Not added in Phase 4.

**Conclusion**: real/official UIClip integration is genuinely blocked for Phase 4 — not merely deferred by convention — by (a) no verified official inference implementation to integrate against, (b) an unconfirmed score-normalization procedure, and (c) `torch`/`transformers` not yet being part of this project. This is fully consistent with [ADR-005](../architecture/decisions/ADR-005-mock-providers-before-real-integrations.md), which already scoped real model loading to Phase 5 before this research was done. Phase 4 implements the provider boundary (`app.uiclip.provider.UIClipProvider`) and `MockUIClipProvider` only.

## Why UIClip Is Being Integrated

LucidUI's deterministic metric engine provides explainable, metric-level signals, but it cannot capture holistic, learned notions of UI quality the way a model trained on UI preference data can. UIClip is integrated to provide that second, independent perspective — not to validate or override the deterministic engine.

## UIClip's Role as an Independent Learned Evaluator

UIClip and LucidUI's metric engine are never merged into a single score. They are run independently against the same decoded image and compared afterward by the Comparison Engine (see [docs/architecture/analysis-pipeline.md](../architecture/analysis-pipeline.md)). Neither is ground truth for the other — see [ADR-004](../architecture/decisions/ADR-004-uiclip-independent-evaluator.md).

## Planned Local Execution

UIClip is planned to run locally within the backend's environment (not as a call to an external hosted API), consistent with LucidUI's privacy model — see [docs/architecture/privacy-model.md](../architecture/privacy-model.md). This means the screenshot never has to leave the backend for UIClip evaluation, same as for the deterministic engine.

## Image Plus Natural-Language Description Input

UIClip is expected to take both the image and an optional natural-language description as input. The description improves the relevance of its evaluation. See Description Sources below.

## Description Sources

Per [docs/api/report-schema.md](../api/report-schema.md), a description passed to UIClip has a `descriptionSource`:

- `user` — typed by the person uploading the screenshot.
- `generic` — a placeholder/default string used when no description was provided.
- `generated` — produced by an automated description-generation model. Not to be used until such a model is actually implemented (see [CLAUDE.md](../../CLAUDE.md)).

## Sliding-Window Processing

UIClip integration is expected to use sliding-window processing over the image (evaluating sub-regions in addition to or instead of the whole image at once) as part of its planned inference approach (see [ROADMAP.md](../../ROADMAP.md) Phase 5). Exact windowing strategy is an implementation detail to be finalized in Phase 5, not decided in Phase 0.

## Model Checkpoint Metadata

Every UIClip result must report which model checkpoint/version produced it (`uiclip.modelVersion` in the report schema), so results remain traceable and reproducible across model updates.

## Preference-Score Interpretation

UIClip's output is called a **preference score**, not a quality score or percentage. It reflects the model's learned relative preference given its training data — it must never be presented as a percentage of objective UI quality, and must always be shown alongside its scale and model version. See language guidance in [docs/frontend/FRONTEND_GUIDE.md](../frontend/FRONTEND_GUIDE.md).

## Mock Evaluator First, Real Evaluator Later

Per [ADR-005](../architecture/decisions/ADR-005-mock-providers-before-real-integrations.md), a mock UIClip evaluator (Phase 4, complete — `app.uiclip.mock_provider.MockUIClipProvider`) is built before the real model integration (Phase 5), behind a shared `UIClipProvider` interface (`app.uiclip.provider.UIClipProvider`), so the API contract, pipeline, and frontend do not need to change when the real model is added.

## Failure Isolation

UIClip failures (`unavailable`, `failed`) must not fail the overall analysis. The deterministic metrics and LLM interpretation must still be returned. The overall report `status` is `partial_success` whenever UIClip (or LLM) did not complete — `disabled`, `unavailable`, or `failed` all count — and `completed` only when every requested optional stage actually completed. See [docs/api/report-schema.md](../api/report-schema.md).
