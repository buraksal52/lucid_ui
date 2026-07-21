# Metric Catalog

This catalog documents every metric planned for the LucidUI deterministic analysis engine. Each entry follows a consistent structure: Purpose, Why LucidUI Uses It, Inputs, Outputs, Method, Reference or Scientific Basis, Interpretation, Proxy Status, Known Limitations.

See [scoring-and-normalization.md](scoring-and-normalization.md) for how these combine into a composite score, [known-limitations.md](known-limitations.md) for cross-cutting caveats, and [scientific-references.md](scientific-references.md) for full citations. See [terminology.md](../product/terminology.md) for definitions of "raw metric," "normalized signal," and "proxy metric."

---

## Contrast

**Purpose**: Estimate the visual contrast between text/foreground elements and their background.

**Why LucidUI Uses It**: Contrast is a well-established readability factor with an established external reference (WCAG). It is a natural first signal for a UI analysis tool.

**Inputs**: Decoded image, detected text regions (from OCR) with sampled foreground/background colors.

**Outputs**: Raw contrast ratio (e.g. `4.5:1`) per sampled text region, or a `[low, high]` range for regions where estimates disagree; an aggregate contrast statistic across the image (`averageContrastRatio`, `regionsAnalyzed`, `regionsSkipped`, `regionsUncertain`, `regionsBorderline`, `regionsBelowAAThreshold`).

**Method** (`corrected-v1`, superseded): For each OCR text region, pad slightly (3px) and Otsu-threshold (Otsu, 1979) the grayscale sub-region into two pixel clusters; the smaller-area cluster is treated as ink/text, the larger as paper/background (this holds regardless of whether the UI is dark-on-light or light-on-dark, since glyphs occupy less area than their surrounding background in ordinary typography). `corrected-v1` took the flat mean color of each entire cluster. Prior to `corrected-v1`, both "foreground" and "background" were the mean color of two heavily-overlapping regions, which a source-code + manual ground-truth audit found understated real contrast by roughly 2×–17× (e.g. a black-on-white heading, true ratio 21:1, reported as ~1.2:1).

**Method, Contrast Sampling V3** (`corrected-v2`, superseded): a follow-up per-region diagnostic run found `corrected-v1`'s flat cluster mean still understated contrast specifically on *small, regular-weight* text — for a small glyph, most ink-cluster pixels are anti-aliased edge blends rather than solid ink, so the cluster mean is pulled toward gray even though Otsu's threshold selection itself is correct. V3 estimated foreground from only the darkest/lightest 15% of the ink cluster (a per-channel median, never a single pixel) and background from only border-connected background pixels.

**Method, Contrast Sampling V4 — dual estimate** (`corrected-v3`, current): a cross-check against three independent whole-region methods (Otsu-cluster mean, percentile-decile, k-means) found V3's core-percentile estimate measurably *higher* than all three specifically on small anti-aliased paragraph text — internal consistency across V3's own runs was not evidence V3 was more accurate, and the gap was large enough to flip the WCAG AA classification (real dark-gray body text: whole-region methods converged near 3.6–4.75, V3 near 5.5–5.6). Rather than picking a side, V4 computes **two** foreground estimates from the same ink cluster and the same border-connected background:
- **core estimate**: V3's method — per-channel median of the darkest/lightest 15% of the ink cluster;
- **conservative estimate**: per-channel median of the *entire* ink cluster (a robust statistic — median, not mean — but one that still reflects whichever pixel population dominates the cluster, the diluted anti-aliased majority for small text).

A region is a **confirmed** pass/fail only when both estimates land on the same side of 4.5:1. When they disagree, the region is reported `status: "uncertain"`, `aaResult: "borderline"`, with both ratios (`coreRatio`, `conservativeRatio`) and the resulting `range` — never collapsed into one fabricated number, and never counted toward `regionsBelowAAThreshold` or any confirmed-pass count. Polarity detection and the border-connected background estimate are unchanged from V3.

**Reference or Scientific Basis**: WCAG 2.1 AA contrast guidance (reference threshold: 4.5:1 for normal text); Otsu (1979) for ink/paper separation. See [scientific-references.md](scientific-references.md).

**Interpretation**: Reported as above or below the WCAG 2.1 AA reference threshold only when confirmed — never as "accessible" or "compliant," since this is a screenshot-based estimate, not a full accessibility audit. `borderline` and `uncertain` regions are excluded from both the pass and fail counts, not treated as either.

**Proxy Status**: Partial proxy. It approximates a subset of what a true accessibility contrast check would verify.

**Known Limitations**: Otsu separation still assumes a text region is meaningfully bimodal (ink vs. paper) — text over a busy photo or gradient can still produce a noisy split; such regions are skipped (near-zero variance) or fall through to `uncertain` if the resulting ink/core sample is too small. A `borderline` classification means the two estimation strategies disagree, not that the true answer is unknowable — resolving it further would require information this pipeline doesn't have (e.g. the original design/CSS color value). The 15% core percentile, the 10px/5px minimum-sample thresholds, and the 8px alignment-style tolerances elsewhere in `corrected-v3` are fixed constants, not derived from the analyzed image. See [known-limitations.md](known-limitations.md).

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

**Method**: Combine contour-based shape detection with OCR-detected text bounding boxes, applying de-duplication heuristics where regions overlap. `detectedElementCount`/`contourBasedCount`/`ocrBasedCount` are unchanged in `corrected-v1`. **New in `corrected-v1`**: a disclosed heuristic (`filteredElementCount`, `repeatingGridExcludedCount`) additionally detects dense horizontal bands of ≥8 near-uniform-size contour elements (e.g. an on-screen system keyboard) as repeating system chrome and excludes them from the count used by [Hick's Law](#hicks-law-estimate) — a source-code + manual audit found a keyboard contributing 162 of 185 "elements" on one real screenshot, corrupting that downstream estimate by more than 2×. `detectedElementCount` itself is left unchanged for continuity.

**Reference or Scientific Basis**: General computer-vision contour/text-detection techniques; not tied to a single named publication.

**Interpretation**: Reported as a count and as relative element density — never as "number of features" or "number of interactive choices" outright.

**Proxy Status**: Proxy. Not equivalent to the number of interactive choices a user actually faces, since it counts visual regions, not confirmed interactive controls.

**Known Limitations**: OCR can inflate the count by detecting individual words as separate boxes rather than semantic elements; decorative elements are counted the same as functional ones. The `corrected-v1` repeating-grid exclusion is a heuristic (uniform-height/width band detection) tuned against a small validation set — it can miss non-keyboard repeating grids or, rarely, exclude a genuinely dense app-content row.

---

## Hick's Law Estimate

**Purpose**: Provide a proxy estimate of decision-time complexity based on the number of detected elements.

**Why LucidUI Uses It**: Hick's Law is a well-known HCI model relating choice count to decision time, useful as an interpretable, formula-based signal.

**Inputs**: Filtered detected element count (n) — as of `corrected-v1`, `detectedElementCount` minus any repeating-grid system-chrome exclusion (see [Detected Element Count](#detected-element-count)), not the raw count.

**Outputs**: An estimated time value `T`, plus the input count `n` and constant `b` used.

**Method**: `T = b × log2(n + 1)`, where `n` is the filtered detected element count and `b` is a fixed constant (150ms), exposed as its own field (`hicksLawBConstantMs`).

**Reference or Scientific Basis**: Hick's Law (Hick, 1952). See [scientific-references.md](scientific-references.md) — **`b=150ms` itself is an assumed/illustrative constant, not a value derived from Hick's original publication or any other cited empirical source**; Hick (1952) reports information-theoretic bits, not a single universal milliseconds-per-bit constant for arbitrary UIs.

**Interpretation**: Reported strictly as an estimate derived from a proxy element count — must never be presented as measured or actual human reaction time. Detected element count is only a proxy for the number of choices a real user would face. `hicksLawEstimateMs` should be treated as an uncalibrated relative estimate (useful for comparing screens against each other), not a predicted decision time in real milliseconds, because of the `b` caveat above.

**Proxy Status**: Proxy of a proxy — built on the Detected Element Count proxy metric, one further step removed from an actual behavioral measurement. No empirical correlation between this estimate (or its inputs) and real human decision time has been established — see [docs/research/evaluation-plan.md](../research/evaluation-plan.md) for the (not-yet-executed) plan to test this.

**Known Limitations**: Inherits all limitations of Detected Element Count; assumes all detected elements represent equally weighted, independent choices, which is not generally true of real UIs; the `b` constant is unsourced (see above). The repeating-grid exclusion's geometric thresholds (row/column count floors, size-uniformity and gap-ratio cutoffs) were tuned against a small internal set of real screenshots, not a systematic or statistically powered validation study — also disclosed directly in the `elements.source` JSON field, not only here.

---

## Small Targets

**Purpose**: Flag detected regions that are smaller than a common minimum touch/click target size.

**Why LucidUI Uses It**: Target size is a well-studied usability factor, especially for touch interfaces.

**Inputs**: Detected element bounding boxes, image DPI/scale assumption.

**Outputs**: Count and list of detected regions below the reference size threshold.

**Method**: Compare each detected element's bounding box dimensions against a 44 × 44 px reference size. **As of `corrected-v1`, only contour-sourced elements are checked** — OCR text-line bounding boxes are excluded from this tally entirely. A source-code + manual audit found ordinary text line-height is almost always under 44px, so counting OCR text boxes here made this flag fire on 93–100% of elements across every audited screenshot, regardless of whether any of them was ever a tap-target candidate.

**Reference or Scientific Basis**: Common mobile platform touch-target guidance (e.g. Apple/Google Human Interface Guidelines use ~44–48 px references). See [scientific-references.md](scientific-references.md) for a TODO on precise sourcing.

**Interpretation**: Reported as "below the 44 × 44 px reference size" as a screenshot-based size signal — a potential review area, not a confirmed usability defect.

**Proxy Status**: Proxy. A screenshot-based pixel size signal only.

**Known Limitations**: Cannot confirm whether a detected region is actually clickable/tappable, nor account for actual device pixel density or viewport scale unless explicitly provided — the 44px comparison is against raw screenshot pixels, not CSS/device-independent points, so it is only meaningful by coincidence unless the capture was taken at 1× scale. `corrected-v1` narrows the check to contour-sourced elements, which removes the text-line-height false-positive source but does not add device-pixel-ratio awareness.

---

## Fitts's Law Index of Difficulty

**Purpose**: Provide a proxy estimate of pointing-movement difficulty between detected elements.

**Why LucidUI Uses It**: Fitts's Law is a foundational HCI model relating target distance and size to movement difficulty.

**Inputs**: Pairwise distances (D) and target widths (W) between detected elements. **As of `corrected-v1`, only contour-sourced ("control-like") elements are considered** — OCR text boxes are excluded, since the same element-list contamination affecting [Detected Element Count](#detected-element-count) (e.g. a system keyboard) previously fed directly into this nearest-neighbor distance graph too.

**Outputs**: Index of Difficulty (ID) values per evaluated element pair.

**Method**: `ID = log2(2D / W)`, where `D` is the distance between two points and `W` is the width of the target element.

**Reference or Scientific Basis**: Fitts's Law (Fitts, 1954). See [scientific-references.md](scientific-references.md).

**Interpretation**: Reported as a relative difficulty index between detected elements — an estimate, not a measured interaction time.

**Proxy Status**: Proxy. The actual pointer origin (e.g. current cursor/finger position) and the true next interaction target are unknown from a static screenshot; distances are computed between detected regions as a stand-in.

**Known Limitations**: Assumes a specific movement path between two detected elements, which may not reflect real user behavior; does not account for input modality (mouse vs. touch vs. keyboard navigation). Restricting to contour-sourced elements (`corrected-v1`) reduces text/keyboard contamination but does not resolve the fundamental lack of a real pointer origin.

---

## Estimated Group Count

**Purpose**: Estimate how many visual groupings the detected elements form.

**Why LucidUI Uses It**: Visual grouping relates to perceived organization and information chunking.

**Inputs**: Detected element positions.

**Outputs**: Integer estimated group count, with grouping assignments.

**Method** (`corrected-v1`): Complete-linkage agglomerative clustering of detected element centroids — at each step, the two clusters with the smallest *maximum* pairwise distance are merged, stopping once that distance exceeds a threshold (same distance constant as the prior single-linkage version: 8% of the image diagonal). This bounds each cluster's diameter. Previously (`legacy-v1`), single-linkage/union-find only required one close pair to merge two clusters, which a source-code + manual audit found let a single dense region (e.g. a long list or a keyboard) chain into just 1–3 clusters regardless of visual card/section boundaries.

**Reference or Scientific Basis**: Miller's "The Magical Number Seven, Plus or Minus Two" is referenced only as historical context for chunking capacity, not as a target metric. See [scientific-references.md](scientific-references.md).

**Interpretation**: Reported as a group count relative to other analyzed screens. Must not claim that 7 (or 7 ± 2) is an ideal or universal target number of UI groups — Miller's number describes short-term memory chunk capacity in a different experimental context, not UI design guidance.

**Proxy Status**: Proxy. Distance-based clustering approximates, but does not equal, human-perceived grouping (which also depends on color, alignment, and semantic similarity).

**Known Limitations**: Clustering threshold choice significantly affects the resulting group count; does not use color or semantic similarity, only position. Complete-linkage (`corrected-v1`) resists chaining better than single-linkage but is more computationally expensive and can still under- or over-split relative to human-perceived sections.

---

## Text Density

**Purpose**: Estimate how much of the interface is occupied by text.

**Why LucidUI Uses It**: Text density is a readily observable, interpretable proxy for information density.

**Inputs**: OCR-detected text bounding boxes, image dimensions.

**Outputs**: Ratio of text bounding-box area to total image area; total detected word count; `averageOcrConfidence` (mean Tesseract confidence, 0–100, over the words counted) and `lowConfidenceWordsExcluded` (words dropped for OCR confidence < 60, the same threshold used to build this metric).

**Method**: Sum the area of OCR-detected text bounding boxes and divide by total image area. **New (`corrected-v2`)**: `averageOcrConfidence`/`lowConfidenceWordsExcluded` disclose, per analysis, how much Tesseract confidence backed the words this metric was built from — this dependency previously existed but was not independently measured or exposed in the output.

**Reference or Scientific Basis**: General OCR-based text-region analysis; not tied to a single named publication.

**Interpretation**: Reported as higher or lower text density relative to other analyzed screens. A low `averageOcrConfidence` or a high `lowConfidenceWordsExcluded` on a given analysis is a signal that `textDensityRatio`/`fontSizeDiversityProxy` for that specific image should be trusted less than one with high confidence — a research correlation study should consider filtering or stratifying by this rather than treating all analyses as equally reliable.

**Proxy Status**: Proxy, entirely dependent on OCR detection quality.

**Known Limitations**: OCR dependency — missed or falsely detected text directly skews this metric; does not distinguish body copy from labels, headings, or decorative text. `averageOcrConfidence`/`lowConfidenceWordsExcluded` disclose Tesseract's own confidence but do not correct for it — a confidently-misread word (e.g. one character misclassified as another) is not detected by this signal.

---

## Font-Size Diversity Proxy

**Purpose**: Estimate typographic variety in the interface.

**Why LucidUI Uses It**: Typographic hierarchy is a recognized readability and design-organization factor.

**Inputs**: OCR-detected text bounding box heights.

**Outputs**: Median absolute deviation (MAD) of bounding box heights across detected text regions.

**Method** (`corrected-v1`): Compute the median absolute deviation of OCR bounding-box heights — `median(|height_i - median(heights)|)` — rather than standard deviation, since a single OCR misdetection (e.g. one line merged with a neighboring icon into an oversized box) can otherwise dominate a std-dev-based figure.

**Reference or Scientific Basis**: General OCR-based typographic analysis; not tied to a single named publication.

**Interpretation**: Reported as higher or lower font-size variance relative to other analyzed screens — described explicitly as a proxy, not a font-size measurement.

**Proxy Status**: Proxy. Bounding-box height is not a direct measurement of font point size.

**Known Limitations**: Affected by line height, letter descenders/ascenders, OCR box-fitting inconsistency, and image resolution/scaling. MAD (`corrected-v1`) is more outlier-resistant than the prior std-dev but is still a box-height statistic, not a font-size measurement. Shares `averageOcrConfidence`/`lowConfidenceWordsExcluded` with [Text Density](#text-density) (same `textDensity` output object, same underlying OCR words) — see that entry for how to use those fields.

---

## Whitespace Ratio

**Purpose**: Estimate how much of the interface is visually "empty" or low-detail space.

**Why LucidUI Uses It**: Whitespace is commonly discussed as a factor in perceived visual clarity.

**Inputs**: Decoded image, local variance map.

**Outputs**: Ratio of low-variance, light ("flat and bright") image blocks to total blocks.

**Method** (`corrected-v1`): Divide the image into blocks, compute local pixel variance and mean brightness per block, and count a block as whitespace-like only when it is **both** low-variance (`< 100`) **and** light (`mean > 200/255`). Previously (`legacy-v1`), only the variance check applied, so a flat *saturated* color region — e.g. a solid brand-color background — counted identically to literal white space; a source-code + manual audit found this materially inflated the ratio on a solid-green screen.

**Reference or Scientific Basis**: General image-variance-based region analysis; not tied to a single named publication.

**Interpretation**: Reported as higher or lower whitespace ratio relative to other analyzed screens.

**Proxy Status**: Proxy. Detects visual flatness *and* lightness, not intentional design whitespace specifically.

**Known Limitations**: Still sensitive to flat, light-colored backgrounds/images that are not actually "whitespace" in the design sense (e.g. a very light-gray hero banner just above the 200/255 threshold); the brightness gate (`corrected-v1`) removes the saturated-color false-positive case but does not attempt to detect design intent.

---

## Alignment Variance

**Purpose**: Estimate how consistently detected elements are positionally aligned.

**Why LucidUI Uses It**: Alignment consistency is commonly associated with perceived visual organization.

**Inputs**: Detected element bounding box positions (x/y edges).

**Outputs**: `alignmentVariance` — a single global blended variance of element x/y positions (unchanged, kept for continuity). **New in `corrected-v1`**: `alignedElementRatio` — the fraction of elements whose left (x) or top (y) edge is within 8px of another element's edge.

**Method**: `alignmentVariance` computes `(std(x positions)/width + std(y positions)/height) / 2` over all detected elements combined — a single blended figure that cannot credit multiple independently-valid alignment axes (e.g. a left-aligned column and a separately right-aligned column both registering as "aligned," rather than washing each other out in one global number). `alignedElementRatio` (`corrected-v1`) instead checks, per element, whether it shares an edge with at least one other element, and reports the share of elements that do.

**Reference or Scientific Basis**: General geometric/statistical analysis of detected element positions; not tied to a single named publication.

**Interpretation**: Reported as higher or lower alignment variance/ratio relative to other analyzed screens.

**Proxy Status**: Proxy. Statistical positional variance/proximity, not a grid-system or layout-correctness check.

**Known Limitations**: Does not know the actual underlying grid system used by the designer; intentional asymmetric layouts will register as high variance without being a design flaw. `alignedElementRatio`'s 8px tolerance is a fixed constant, not derived from the analyzed UI's actual grid unit.

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

**Known Limitations**: A high or low colorfulness score has no inherent "better" direction for UI design; brand and content-driven color choices can validly produce either. A source-code + manual audit found this formula rewards the *area* covered by saturated color over hue *variety* — a screen filled with one flat saturated color can outscore a screen with several distinct hues at lower saturation. The formula itself is unchanged (correct as published); see [Hue Diversity](#hue-diversity) for a complementary signal that targets hue variety specifically.

---

## Hue Diversity

**Purpose**: Estimate how many distinct hues are present in the interface, as a complement to [Colorfulness](#colorfulness)'s saturation-intensity measure.

**Why LucidUI Uses It**: The audit above found colorfulness's name invites a "how varied are the colors" reading that its formula does not actually measure (it can be dominated by one large saturated region). This metric targets that specific question instead, without altering the validated colorfulness formula.

**Inputs**: Decoded image (HSV hue/saturation channels).

**Outputs**: `hueDiversityIndex` (0–1, Shannon entropy of the hue histogram, normalized), `saturatedPixelRatio` (fraction of pixels with enough saturation to have a meaningful hue).

**Method**: Convert to HSV; keep only pixels with saturation > 40 (near-gray/white/black pixels have an unstable hue angle); bin the remaining hues into 36 bins and compute the Shannon entropy of that histogram, normalized by the maximum possible entropy (`log2(36)`). A single dominant hue yields a low index; many roughly-equally-represented hues yield a high index.

**Reference or Scientific Basis**: Shannon entropy (information theory), applied to a hue histogram; not a named published UI/vision metric.

**Interpretation**: Reported as higher or lower hue variety relative to other analyzed screens — a color-variety proxy signal, not a design-quality judgment. Introduced in engine version `corrected-v1`.

**Proxy Status**: Proxy. Additive alongside `colorfulnessScore`, never a replacement for it — the two answer different questions ("how saturated/intense" vs. "how many distinct hues").

**Known Limitations**: The saturation cutoff (40) and bin count (36) are fixed constants, not derived from the analyzed image; very small saturated regions can still shift the histogram disproportionately relative to their visual prominence.

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
