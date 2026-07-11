# Metric Catalog

This catalog documents every metric planned for the LucidUI deterministic analysis engine. Each entry follows a consistent structure: Purpose, Why LucidUI Uses It, Inputs, Outputs, Method, Reference or Scientific Basis, Interpretation, Proxy Status, Known Limitations.

See [scoring-and-normalization.md](scoring-and-normalization.md) for how these combine into a composite score, [known-limitations.md](known-limitations.md) for cross-cutting caveats, and [scientific-references.md](scientific-references.md) for full citations. See [terminology.md](../product/terminology.md) for definitions of "raw metric," "normalized signal," and "proxy metric."

---

## Contrast

**Purpose**: Estimate the visual contrast between text/foreground elements and their background.

**Why LucidUI Uses It**: Contrast is a well-established readability factor with an established external reference (WCAG). It is a natural first signal for a UI analysis tool.

**Inputs**: Decoded image, detected text regions (from OCR) with sampled foreground/background colors.

**Outputs**: Raw contrast ratio (e.g. `4.5:1`) per sampled text region; an aggregate contrast statistic across the image.

**Method**: Compute relative luminance for sampled foreground and background pixel regions per WCAG's relative luminance formula, then derive the contrast ratio between them.

**Reference or Scientific Basis**: WCAG 2.1 AA contrast guidance (reference threshold: 4.5:1 for normal text). See [scientific-references.md](scientific-references.md).

**Interpretation**: Reported as above or below the WCAG 2.1 AA reference threshold — never as "accessible" or "compliant," since this is a screenshot-based estimate, not a full accessibility audit.

**Proxy Status**: Partial proxy. It approximates a subset of what a true accessibility contrast check would verify.

**Known Limitations**: Relies on mean-color sampling of detected regions rather than pixel-exact foreground/background separation; sensitive to anti-aliasing, gradients, and background images behind text. See [known-limitations.md](known-limitations.md).

---

## Edge Density

**Purpose**: Estimate the amount of visual detail/clutter in the interface.

**Why LucidUI Uses It**: Edge density is used in visual-clutter research as a computationally cheap proxy for perceived clutter.

**Inputs**: Decoded image (grayscale).

**Outputs**: Ratio of edge pixels to total pixels (0–1).

**Method**: Canny edge detection, then count edge pixels as a fraction of total image pixels.

**Reference or Scientific Basis**: Rosenholtz, Li, and Nakano's work on measuring visual clutter. See [scientific-references.md](scientific-references.md).

**Interpretation**: Reported as higher or lower edge density relative to other analyzed screens — described as a visual clutter proxy signal, not a clutter verdict.

**Proxy Status**: Proxy. Edge density correlates with, but is not equivalent to, perceived clutter.

**Known Limitations**: Sensitive to image resolution (higher resolution can produce more detected edges) and to the fixed Canny threshold parameters used; not normalized across screen sizes.

---

## Detected Element Count

**Purpose**: Estimate how many distinct visual elements are present in the interface.

**Why LucidUI Uses It**: Serves as an input to element-density and choice-related proxy metrics (e.g. Hick's Law Estimate).

**Inputs**: Decoded image, contour detection output, OCR text box output.

**Outputs**: Integer count of detected elements (contours plus OCR text boxes).

**Method**: Combine contour-based shape detection with OCR-detected text bounding boxes, applying de-duplication heuristics where regions overlap.

**Reference or Scientific Basis**: General computer-vision contour/text-detection techniques; not tied to a single named publication.

**Interpretation**: Reported as a count and as relative element density — never as "number of features" or "number of interactive choices" outright.

**Proxy Status**: Proxy. Not equivalent to the number of interactive choices a user actually faces, since it counts visual regions, not confirmed interactive controls.

**Known Limitations**: OCR can inflate the count by detecting individual words as separate boxes rather than semantic elements; decorative elements are counted the same as functional ones.

---

## Hick's Law Estimate

**Purpose**: Provide a proxy estimate of decision-time complexity based on the number of detected elements.

**Why LucidUI Uses It**: Hick's Law is a well-known HCI model relating choice count to decision time, useful as an interpretable, formula-based signal.

**Inputs**: Detected element count (n).

**Outputs**: An estimated time value `T`, plus the input count `n` and constant `b` used.

**Method**: `T = b × log2(n + 1)`, where `n` is the detected element count and `b` is a fixed constant documented alongside the output.

**Reference or Scientific Basis**: Hick's Law (Hick, 1952). See [scientific-references.md](scientific-references.md).

**Interpretation**: Reported strictly as an estimate derived from a proxy element count — must never be presented as measured or actual human reaction time. Detected element count is only a proxy for the number of choices a real user would face.

**Proxy Status**: Proxy of a proxy — built on the Detected Element Count proxy metric, one further step removed from an actual behavioral measurement.

**Known Limitations**: Inherits all limitations of Detected Element Count; assumes all detected elements represent equally weighted, independent choices, which is not generally true of real UIs.

---

## Small Targets

**Purpose**: Flag detected regions that are smaller than a common minimum touch/click target size.

**Why LucidUI Uses It**: Target size is a well-studied usability factor, especially for touch interfaces.

**Inputs**: Detected element bounding boxes, image DPI/scale assumption.

**Outputs**: Count and list of detected regions below the reference size threshold.

**Method**: Compare each detected element's bounding box dimensions against a 44 × 44 px reference size.

**Reference or Scientific Basis**: Common mobile platform touch-target guidance (e.g. Apple/Google Human Interface Guidelines use ~44–48 px references). See [scientific-references.md](scientific-references.md) for a TODO on precise sourcing.

**Interpretation**: Reported as "below the 44 × 44 px reference size" as a screenshot-based size signal — a potential review area, not a confirmed usability defect.

**Proxy Status**: Proxy. A screenshot-based pixel size signal only.

**Known Limitations**: Cannot confirm whether a detected region is actually clickable/tappable, nor account for actual device pixel density or viewport scale unless explicitly provided.

---

## Fitts's Law Index of Difficulty

**Purpose**: Provide a proxy estimate of pointing-movement difficulty between detected elements.

**Why LucidUI Uses It**: Fitts's Law is a foundational HCI model relating target distance and size to movement difficulty.

**Inputs**: Pairwise distances (D) and target widths (W) between detected elements.

**Outputs**: Index of Difficulty (ID) values per evaluated element pair.

**Method**: `ID = log2(2D / W)`, where `D` is the distance between two points and `W` is the width of the target element.

**Reference or Scientific Basis**: Fitts's Law (Fitts, 1954). See [scientific-references.md](scientific-references.md).

**Interpretation**: Reported as a relative difficulty index between detected elements — an estimate, not a measured interaction time.

**Proxy Status**: Proxy. The actual pointer origin (e.g. current cursor/finger position) and the true next interaction target are unknown from a static screenshot; distances are computed between detected regions as a stand-in.

**Known Limitations**: Assumes a specific movement path between two detected elements, which may not reflect real user behavior; does not account for input modality (mouse vs. touch vs. keyboard navigation).

---

## Estimated Group Count

**Purpose**: Estimate how many visual groupings the detected elements form.

**Why LucidUI Uses It**: Visual grouping relates to perceived organization and information chunking.

**Inputs**: Detected element positions.

**Outputs**: Integer estimated group count, with grouping assignments.

**Method**: Distance-based clustering of detected element positions (e.g. proximity thresholding).

**Reference or Scientific Basis**: Miller's "The Magical Number Seven, Plus or Minus Two" is referenced only as historical context for chunking capacity, not as a target metric. See [scientific-references.md](scientific-references.md).

**Interpretation**: Reported as a group count relative to other analyzed screens. Must not claim that 7 (or 7 ± 2) is an ideal or universal target number of UI groups — Miller's number describes short-term memory chunk capacity in a different experimental context, not UI design guidance.

**Proxy Status**: Proxy. Distance-based clustering approximates, but does not equal, human-perceived grouping (which also depends on color, alignment, and semantic similarity).

**Known Limitations**: Clustering threshold choice significantly affects the resulting group count; does not use color or semantic similarity, only position.

---

## Text Density

**Purpose**: Estimate how much of the interface is occupied by text.

**Why LucidUI Uses It**: Text density is a readily observable, interpretable proxy for information density.

**Inputs**: OCR-detected text bounding boxes, image dimensions.

**Outputs**: Ratio of text bounding-box area to total image area; total detected word count.

**Method**: Sum the area of OCR-detected text bounding boxes and divide by total image area.

**Reference or Scientific Basis**: General OCR-based text-region analysis; not tied to a single named publication.

**Interpretation**: Reported as higher or lower text density relative to other analyzed screens.

**Proxy Status**: Proxy, entirely dependent on OCR detection quality.

**Known Limitations**: OCR dependency — missed or falsely detected text directly skews this metric; does not distinguish body copy from labels, headings, or decorative text.

---

## Font-Size Diversity Proxy

**Purpose**: Estimate typographic variety in the interface.

**Why LucidUI Uses It**: Typographic hierarchy is a recognized readability and design-organization factor.

**Inputs**: OCR-detected text bounding box heights.

**Outputs**: Standard deviation of bounding box heights across detected text regions.

**Method**: Compute the standard deviation of OCR bounding-box heights.

**Reference or Scientific Basis**: General OCR-based typographic analysis; not tied to a single named publication.

**Interpretation**: Reported as higher or lower font-size variance relative to other analyzed screens — described explicitly as a proxy, not a font-size measurement.

**Proxy Status**: Proxy. Bounding-box height is not a direct measurement of font point size.

**Known Limitations**: Affected by line height, letter descenders/ascenders, OCR box-fitting inconsistency, and image resolution/scaling.

---

## Whitespace Ratio

**Purpose**: Estimate how much of the interface is visually "empty" or low-detail space.

**Why LucidUI Uses It**: Whitespace is commonly discussed as a factor in perceived visual clarity.

**Inputs**: Decoded image, local variance map.

**Outputs**: Ratio of low-variance ("flat") image blocks to total blocks.

**Method**: Divide the image into blocks, compute local pixel variance per block, and count blocks below a variance threshold as whitespace-like.

**Reference or Scientific Basis**: General image-variance-based region analysis; not tied to a single named publication.

**Interpretation**: Reported as higher or lower whitespace ratio relative to other analyzed screens.

**Proxy Status**: Proxy. Detects visual flatness, not intentional design whitespace specifically.

**Known Limitations**: Sensitive to flat-color regions and solid-color backgrounds/images that are not actually "whitespace" in the design sense (e.g. a solid-color hero banner).

---

## Alignment Variance

**Purpose**: Estimate how consistently detected elements are positionally aligned.

**Why LucidUI Uses It**: Alignment consistency is commonly associated with perceived visual organization.

**Inputs**: Detected element bounding box positions (x/y edges).

**Outputs**: Variance of element edge positions along shared axes.

**Method**: Compute positional variance of detected element edges (left/right/top/bottom) grouped by proximity to shared axis lines.

**Reference or Scientific Basis**: General geometric/statistical analysis of detected element positions; not tied to a single named publication.

**Interpretation**: Reported as higher or lower alignment variance relative to other analyzed screens.

**Proxy Status**: Proxy. Statistical positional variance, not a grid-system or layout-correctness check.

**Known Limitations**: Does not know the actual underlying grid system used by the designer; intentional asymmetric layouts will register as high variance without being a design flaw.

---

## Colorfulness

**Purpose**: Estimate the overall color intensity/vividness of the interface.

**Why LucidUI Uses It**: Colorfulness is a well-established, reproducible image metric with a published computation method.

**Inputs**: Decoded image (RGB).

**Outputs**: A single colorfulness score.

**Method**: Hasler and Süsstrunk's colorfulness metric, computed from opponent color-space statistics (rg/yb standard deviation and mean).

**Reference or Scientific Basis**: Hasler and Süsstrunk (2003), "Measuring colorfulness in natural images." See [scientific-references.md](scientific-references.md).

**Interpretation**: Reported as higher or lower colorfulness relative to other analyzed screens — describes color intensity, not design quality.

**Proxy Status**: Direct computation of a defined image metric (not itself a proxy for a cognitive construct), but its relevance to UI design quality is not established and should not be implied.

**Known Limitations**: A high or low colorfulness score has no inherent "better" direction for UI design; brand and content-driven color choices can validly produce either.

---

## Visual Balance

**Purpose**: Estimate whether brightness is distributed evenly across the interface.

**Why LucidUI Uses It**: Brightness balance is a simple, reproducible compositional signal.

**Inputs**: Decoded image (luminance channel).

**Outputs**: Left/right luminance difference; top/bottom luminance difference.

**Method**: Split the image into left/right and top/bottom halves, compute mean luminance per half, and report the differences.

**Reference or Scientific Basis**: General image-luminance analysis; not tied to a single named publication.

**Interpretation**: Reported as higher or lower brightness balance relative to other analyzed screens — a brightness-balance proxy signal, not a semantic composition judgment.

**Proxy Status**: Proxy. Measures brightness distribution only, not semantic or compositional balance (subject placement, visual weight, hierarchy).

**Known Limitations**: A single bright or dark image region (e.g. a photo, a dark-mode panel) can dominate this signal regardless of actual layout balance.

---

## Cross-Cutting Notes

- Every metric above must expose its raw value, normalized signal (if applicable), source, threshold (if applicable), proxy status, and known limitations in the metric JSON — see [docs/api/report-schema.md](../api/report-schema.md).
- See [scoring-and-normalization.md](scoring-and-normalization.md) for how these metrics combine into the LucidUI Composite Signal Score.
- See [known-limitations.md](known-limitations.md) for limitations that apply across multiple metrics rather than to one specific metric.
