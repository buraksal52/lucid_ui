# Known Limitations

This document collects limitations that apply broadly across the LucidUI deterministic metric engine, beyond the per-metric limitations already listed in [metric-catalog.md](metric-catalog.md). It exists so that every consumer of LucidUI's output — the LLM interpretation stage, the frontend, and researchers — has a single place to understand what the numbers do and do not mean.

## Measurement Limitations

- **Mean-color contrast sampling**: contrast is computed from sampled mean foreground/background colors around detected text regions, not pixel-exact text-glyph vs. background separation.
- **OCR word-level element inflation**: OCR frequently detects individual words as separate boxes, inflating detected element and text density counts relative to semantic UI elements.
- **No resolution normalization**: metrics like edge density and detected element count are sensitive to the screenshot's pixel resolution; two screenshots of the same UI at different resolutions/DPI can produce different raw values.
- **Fixed Canny thresholds**: edge detection uses fixed threshold parameters rather than per-image adaptive thresholds, which can under- or over-detect edges depending on image characteristics.
- **Light-background assumptions**: some heuristics (e.g. whitespace detection) are tuned with common light-UI-background assumptions in mind and may behave differently on dark-mode or unusually themed interfaces.

## Implementation Limitations

- **Single shared OCR pass**: as of Phase 2B-1, `app.metrics.MetricEngine` runs Tesseract OCR exactly once per analysis and shares the resulting word/box data across contrast, element detection, and text density. This is an intentional performance choice (see [ROADMAP.md](../../ROADMAP.md) Phase 2B-1), but it also means a single OCR miss or false detection propagates into all three of those metrics simultaneously for that analysis, rather than affecting them independently.

## Scope Limitations

- **Screenshot-only limitations**: LucidUI never has access to the live DOM, CSS, or application state — only a static raster image.
- **No DOM or interaction semantics**: LucidUI cannot know which detected regions are actually clickable, focusable, or interactive; it can only report visual/geometric properties.
- **Proxy metrics**: nearly every metric in the catalog is an approximation of a cognitive-science or HCI construct (Hick's Law, Fitts's Law, Miller's grouping heuristic), not a direct behavioral measurement — see each metric's Proxy Status in [metric-catalog.md](metric-catalog.md).
- **Screenshot crop and framing effects**: partial screenshots, scrolled views, or cropped captures can materially change element counts, density, and balance metrics without the underlying UI actually changing.
- **Font rendering and anti-aliasing effects**: how text and edges render (browser, OS font rendering, anti-aliasing, screen scaling) can shift edge-density, contrast, and font-size-diversity readings independent of actual design differences.

## Cross-System Limitations

- **UIClip training-data dependence**: UIClip's output reflects patterns in its training data and is not a neutral or universal standard — see [docs/research/uiclip-integration.md](../research/uiclip-integration.md).
- **LLM interpretation dependence on input metrics**: the LLM interpretation stage can only be as accurate as the deterministic metric JSON it receives; it has no independent visual verification since it never sees the raw image (see [ADR-003](../architecture/decisions/ADR-003-json-only-llm-input.md)).

## How These Limitations Should Be Used

- In documentation and frontend copy: to justify hedged, non-verdict language (see [docs/frontend/FRONTEND_GUIDE.md](../frontend/FRONTEND_GUIDE.md) language guidelines).
- In research work: as caveats that must be disclosed alongside any correlation or benchmarking result (see [docs/research/evaluation-plan.md](../research/evaluation-plan.md)).
- In future implementation work: as a checklist to revisit before claiming a metric has been "fixed" or "improved" — most limitations here are inherent to screenshot-based analysis and are not fully solvable, only reducible.
