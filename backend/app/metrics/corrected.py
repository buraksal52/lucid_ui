"""Corrected deterministic metric implementations (engine versions "corrected-v1"
through "corrected-v3").

`backend/reference/legacy_metric_engine.py` is left completely untouched per
CLAUDE.md ("Legacy Metric Engine... immutable unless explicitly instructed")
— it remains importable as a frozen historical/audit-trail baseline
(`metricEngineVersion: "legacy-v1"`). This module holds new implementations
for the metrics a source-code + manual ground-truth audit found to be
structurally weak or mislabelled. Prior versions of a fixed function are
kept in place (not deleted) when superseded, the same way this module keeps
the legacy module untouched — `analyze_contrast_v2` (corrected-v1) and
`analyze_contrast_v3` (corrected-v2) are both kept for reference even though
`MetricEngine` is wired to `analyze_contrast_v4` (corrected-v3) as of the
third contrast pass below. Every function here preserves the exact JSON
field *names* already in the API contract (see docs/api/report-schema.md) —
only computation changes, plus a small number of new, additive fields.

Two functions the audit verified as mathematically correct are reused
unchanged from the legacy module rather than reimplemented:
`relative_luminance` (not called directly here) and `contrast_ratio`.

Audit findings this module addresses, one function per fix:

1. `analyze_contrast_v2` — mean-of-bounding-box sampling collapsed
   black-on-white text to ~1.2:1 (true value ~21:1). Fixed via per-region
   Otsu ink/paper separation.
2. `analyze_elements_v2` — small-target flag fired on ordinary OCR text
   line-height (93-100% positive rate observed). Fixed by restricting the
   small-target tally to contour-sourced elements only.
3. `analyze_elements_v2` (same function) — a software keyboard contributed
   162/185 "elements" on one audited screenshot, corrupting Hick's Law by
   >2x. Fixed via a disclosed repeating-grid exclusion feeding a new
   `filteredElementCount` that Hick's Law now uses.
4. `analyze_groups_v2` — single-linkage union-find chained whole dense
   regions into 1-2 clusters. Fixed via complete-linkage-style clustering
   (bounds cluster diameter, not just nearest-pair distance).
5. `analyze_whitespace_alignment_v2` — one global blended x/y variance
   couldn't credit multiple valid alignment axes. Fixed via a new
   `alignedElementRatio` (shared-edge clustering), alongside the old value.
6. `analyze_fitts_full_v2` — nearest-neighbor distances computed over the
   same contaminated element list as #3. Fixed by only considering
   contour-sourced ("control-like") elements.
7. `analyze_whitespace_alignment_v2` (same function) — a flat *saturated*
   color region counted as whitespace. Fixed by requiring both low variance
   and high mean brightness.
8. `analyze_text_density_v2` — font-size-diversity via std-dev is
   outlier-sensitive. Fixed via median absolute deviation.
9. `analyze_hue_diversity` — new, additive signal (hue-histogram entropy)
   placed in `additionalSignals` alongside the unchanged `colorfulnessScore`,
   since the audit found colorfulness's formula correct but its name
   invites a "hue variety" reading the formula does not measure.

Post-audit follow-up fixes (independent re-verification of #3/#6 above):

10. `_detect_repeating_grid_indices` — the original #3 fix flagged any
    single dense *row* of >= 8 near-uniform-size elements as system chrome,
    which false-positived on ordinary single-row UI (bottom nav bars,
    toolbars, filter-chip rows, icon rows). Fixed by requiring an actual
    multi-row, multi-column, tightly-packed 2D grid (row count, column
    count, and normalized horizontal/vertical gap ratios all gated
    together) — a single row, however uniform or dense, never qualifies.
11. `analyze_elements_v2` — the #3 grid-exclusion filter was only ever
    threaded into `filteredElementCount` (Hick's Law); the list handed to
    Fitts's Law (#6's "control-like elements") was never filtered by it, so
    the exact keyboard/grid contamination #3 fixed for Hick's Law still
    fully corrupted Fitts's Law's nearest-neighbor distances. Fixed by
    computing one shared `eligible_interactive_elements` list (contour-only,
    grid-excluded, non-degenerate) that both metrics now consume, so a
    grid-exclusion fix can never silently apply to only one of them.
12. `_extract_contour_elements` — a real screenshot with a solid-color
    full-bleed background behind a white card (a modal-style screen)
    reported zero contour elements, zero small targets, and no Fitts's/
    Hick's Law data, because `cv2.RETR_EXTERNAL` never returns a foreground
    island nested inside a hole of a bigger shape (here, the background
    thresholds as one image-spanning blob, and everything on the card is a
    hole-nested island). Fixed via `cv2.RETR_CCOMP` (re-promotes hole-nested
    islands back to the top level, without full `RETR_TREE`'s unbounded
    recursion into individual letter strokes) plus three explicit filtering
    layers, each disclosed via a new additive field rather than silently
    dropped: (a) CCOMP's own hierarchy marks every *hole* (interior
    background-colored negative space — a button's light interior, a
    letter's counter) with a non -1 parent index, and holes are excluded
    outright — without this, revealing nested content also floods the
    count with the negative space of every shape that already has its own
    outer contour (`holeContourExcludedCount`); (b) the full-bleed
    background contour itself is classified out (`backgroundContourExcludedCount`);
    (c) remaining near-identical nested duplicates — the same physical edge
    detected twice via nested threshold crossings — are deduplicated by
    containment + IoU + area ratio (`duplicateNestedContourExcludedCount`).
13. `_classify_interactive_targets` — once #12 correctly stopped discarding
    nested elements, a real screenshot showed a large/bold heading letter
    ("C" of "Congratulations!") being counted as a second interactive
    target alongside the screen's one real button, corrupting Hick's Law
    (an extra "choice") and Fitts's Law (a nearest-neighbor distance
    between a button and a heading letter — spatially real, HCI-meaningless).
    `contourBasedCount` still counts every visual contour; a new
    `interactiveTargets` list — shared by Hick's Law, Fitts's Law, and
    `smallTargetsBelow44px` — additionally excludes any contour
    substantially coincident with OCR-detected text ink and not
    meaningfully larger than that text (`textGlyphContourExcludedCount`).
    A contour whose matched OCR text sits inside a much-larger contour is
    kept (a labeled button). A contour with no OCR correlate at all (an
    icon, a checkbox, an un-OCR'd button) is never touched by this and is
    kept regardless of size. `analyze_fitts_full_v2` also no longer reports
    an ID for a single target (`status: "not_applicable"` instead of
    silently returning `elementsConsidered: 0`).
    Known, deliberately out-of-scope limitation: this fix depends on OCR
    successfully reading the coincident text; a decorative/logo glyph OCR
    reads at very low confidence (filtered out before it ever reaches the
    classifier) still remains an interactive target. Documented, not fixed,
    this round.
14. `_detect_keyboard_region` — a real screenshot with an on-screen iOS
    keyboard still counted ~160 keyboard-related contours as interactive
    targets (`repeatingGridExcludedCount: 0`): the existing repeating-grid
    detector (finding #10) is geometry-only and assumes uniform key-box
    rectangles, but a keyboard's key *fill* is light and never thresholds
    as a contour — only the irregular, loosely-spaced letter ink and
    per-key separator lines do, which that detector's density/uniformity
    thresholds don't recognize. Rather than add yet another geometric
    threshold (equally brittle to the next layout/font/scale), a
    purpose-built detector combines six independent signals (row count,
    width coverage, bottom position, QWERTY-sequence OCR match, a narrow
    low-collision keyboard keyword list, single-character OCR ratio) into
    one weighted confidence score. Geometric signals alone are capped
    below the detection threshold, so position/density/width can never by
    themselves produce a confident detection — some textual corroboration
    is always required. A mid-confidence result is `degraded` (uncertain):
    nothing is excluded, but `metricsStatus`/`warning` disclose the
    ambiguity rather than silently resolving it either way. Contours
    inside a *confidently* detected keyboard region are excluded from
    `interactiveTargets` (and therefore Hick's/Fitts's Law and
    `smallTargetsBelow44px`) via `keyboardExcludedTargetCount`, disclosed
    alongside `keyboardDetected`/`keyboardDetectionConfidence`/
    `keyboardRegionBbox`/`systemUiRegion`/`systemUiExcludedCount`.
    `contourBasedCount` is untouched — the keyboard's key ink is still a
    real visual contour, it is just never an interactive target.

15. Tier 3 ("Problematic") metric removal — an explicit, user-instructed
    pass (not an audit fix) per docs/metrics/reliability-tiers.md: for
    research-paper defensibility, every metric classified Tier 3 there was
    removed from the engine/API entirely, not just excluded from reporting.
    Removed: `hicksLawEstimateMs`/`hicksLawBConstantMs` and
    `smallTargetsBelow44px` from `analyze_elements_v2`'s output (the
    computations themselves are deleted, not just hidden); the standalone
    `repeatingGridExcludedCount` disclosure field (the underlying
    `_detect_repeating_grid_indices` filtering is kept — it still improves
    `interactiveTargets`/Fitts's Law, neither of which is Tier 3);
    `analyze_whitespace_alignment_v2` (`whitespaceRatio`,
    `alignmentVariance`, `alignedElementRatio` were all Tier 3) — the
    function is left defined below, unused, for the same audit-trail reason
    every prior superseded version is kept; `analyze_clutter` (`edgeDensity`,
    Tier 3) is no longer called from `MetricEngine` (it lives in, and is
    untouched in, the immutable legacy module). The composite score's
    `clutter`/`elementSize`/`groupCount` components are dropped accordingly
    — see `WEIGHTS_V2`/`normalize_metrics_v2`/`weighted_score_v2` below,
    which replace (not modify) the legacy module's `WEIGHTS`/
    `normalize_metrics`/`weighted_score`, following this module's usual
    "add a new version, never edit the legacy file" pattern. `contrast_ratio`/
    `relative_luminance`/`normalize()` are still reused unchanged from the
    legacy module — none of those are Tier 3.

Composite score weights/normalization bounds and the colorfulness formula
itself were explicitly out of scope for the audit passes (Fixes 1-14) —
see docs/metrics/scoring-and-normalization.md. Fix 15 is the one
exception, per explicit user instruction (Tier 3 removal), not an audit
finding.
"""

from typing import Any

import cv2
import numpy as np

from reference.legacy_metric_engine import contrast_ratio, normalize

# ---- Repeating-grid / system-chrome detection (Fix 3, revised — see the
# "Fix 3b" section below for the full rationale) ----
_GRID_MIN_COLUMNS = 5  # min elements in a single row for that row to be a grid-row candidate
_GRID_MIN_ROWS = 3  # min vertically-stacked grid-row candidates to call it an actual 2D grid
_GRID_MIN_TOTAL_ELEMENTS = _GRID_MIN_ROWS * _GRID_MIN_COLUMNS  # sufficiently high element count
_GRID_HEIGHT_CV_THRESHOLD = 0.15  # per-row element height uniformity (coefficient of variation)
_GRID_WIDTH_CV_THRESHOLD = 0.35  # per-row element width uniformity
_GRID_ROW_BAND_Y_TOLERANCE_RATIO = 0.6  # y-banding tolerance, relative to element height
_GRID_ROW_BAND_Y_TOLERANCE_MIN_PX = 6
_GRID_MAX_HORIZONTAL_GAP_RATIO = 0.6  # (gap between row neighbors) / median row element width
_GRID_MAX_VERTICAL_GAP_RATIO = 0.6  # (gap between stacked rows) / median element height


# ---------- Fix 1: Contrast (Otsu ink/paper separation) ----------
def analyze_contrast_v2(img: np.ndarray, ocr_data: dict) -> dict[str, Any]:
    ratios: list[float] = []
    skipped = 0
    h, w = img.shape[:2]
    n_boxes = len(ocr_data["text"])
    pad = 3

    for i in range(n_boxes):
        if int(ocr_data["conf"][i]) < 60 or not ocr_data["text"][i].strip():
            continue
        x, y, bw, bh = (ocr_data["left"][i], ocr_data["top"][i], ocr_data["width"][i], ocr_data["height"][i])
        y0, y1 = max(0, y - pad), min(h, y + bh + pad)
        x0, x1 = max(0, x - pad), min(w, x + bw + pad)
        region = img[y0:y1, x0:x1]
        if region.size == 0:
            skipped += 1
            continue

        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        if float(gray.std()) < 5.0:
            # No real bimodal ink/paper split — usually an OCR false
            # positive on a near-flat region. Skip rather than fabricate.
            skipped += 1
            continue

        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mask_flat = mask.reshape(-1).astype(bool)
        pixels = region.reshape(-1, 3)
        group_a, group_b = pixels[mask_flat], pixels[~mask_flat]
        if len(group_a) == 0 or len(group_b) == 0:
            skipped += 1
            continue

        # The smaller-area cluster is the ink/text (glyphs cover less area
        # than their background in ordinary typography, regardless of
        # whether the UI is light-on-dark or dark-on-light).
        text_px, bg_px = (group_a, group_b) if len(group_a) <= len(group_b) else (group_b, group_a)
        text_color = text_px.mean(axis=0)[::-1]  # BGR -> RGB
        bg_color = bg_px.mean(axis=0)[::-1]

        ratio = contrast_ratio(text_color.tolist(), bg_color.tolist())
        ratios.append(round(ratio, 2))

    avg_ratio = round(float(np.mean(ratios)), 2) if ratios else None
    below_aa = sum(1 for r in ratios if r < 4.5)
    return {
        "averageContrastRatio": avg_ratio,
        "regionsAnalyzed": len(ratios),
        "regionsSkipped": skipped,
        "regionsBelowAAThreshold": below_aa,
        "source": (
            "WCAG 2.1 AA (4.5:1 normal text); ink/paper separated per text region via "
            "Otsu thresholding rather than a flat box mean (corrected-v1)"
        ),
    }


# ---------- Fix 1b (corrected-v2): Contrast Sampling V3 — small anti-aliased text ----------
#
# A per-region diagnostic run against a real screenshot found `analyze_contrast_v2`
# still understated contrast on small, regular-weight text: taking the mean of
# the *entire* Otsu ink cluster works well for large/bold glyphs (mostly solid
# ink pixels) but is dragged toward gray for small text, where most ink-side
# pixels are anti-aliased edge blends rather than a solid ink core. Real
# dark-gray-on-white body text (RGB ~102,102,102, true ratio ~5.5:1) was
# measured at ~3.5-4.0:1 and wrongly flagged as failing AA.
#
# V3 keeps the same Otsu split (which cluster is "ink" vs "background" is
# unchanged) and the same WCAG formulas, and only changes how a color is
# estimated *from* each cluster:
#   - polarity (dark-on-light vs light-on-dark) is read from the two
#     clusters' relative luminance;
#   - the foreground color comes from only the most extreme
#     `_CORE_PERCENTILE`% of the ink cluster, by luminance (darkest for dark
#     text, lightest for light text) — a set of pixels, never a single
#     min/max pixel — reduced to a per-channel median (robust to a stray
#     noise/compression-artifact/shadow pixel inside that set);
#   - the background color comes from only the background-cluster pixels
#     connected to the crop border, excluding background-colored pixels
#     enclosed inside a glyph (e.g. the inside of an "o");
#   - a region is `uncertain` (no ratio reported, never fabricated, never
#     counted as a confirmed AA violation) whenever the ink cluster or its
#     core-pixel sample is too small to be a stable estimate.

_CORE_PERCENTILE = 15  # top/bottom % of the ink cluster, by luminance, used for the color estimate
_MIN_INK_CLUSTER_PIXELS = 10  # below this, the ink cluster itself is too small to trust
_MIN_CORE_PIXELS = 5  # below this, the core-percentile sample is too small to trust
_CONFIDENT_CORE_PIXELS = 20  # core-pixel count at which `confidence` saturates to 1.0


def _border_connected_mask(mask: np.ndarray) -> np.ndarray:
    """The subset of `mask` (a boolean array) whose connected component
    touches the array's border — used to keep only background pixels that
    are actually contiguous with the surrounding background, not a
    background-colored region enclosed inside a glyph (e.g. the inside of
    an "o" or "e")."""
    num_labels, labels = cv2.connectedComponents(mask.astype(np.uint8))
    if num_labels <= 1:
        return np.zeros_like(mask, dtype=bool)
    border_pixel_labels = np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
    border_labels = set(border_pixel_labels.tolist())
    border_labels.discard(0)  # label 0 = pixels outside `mask` entirely, not a component to keep
    if not border_labels:
        return np.zeros_like(mask, dtype=bool)
    return np.isin(labels, list(border_labels)) & mask


def _uncertain_region(text: str, bbox: tuple[int, int, int, int], ocr_confidence: int, reason: str, **extra: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "text": text,
        "bbox": bbox,
        "ocrConfidence": ocr_confidence,
        "status": "uncertain",
        "reason": reason,
        "ratio": None,
        "aa": None,
        "confidence": 0.0,
    }
    row.update(extra)
    return row


def analyze_contrast_v3(img: np.ndarray, ocr_data: dict) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Returns `(aggregate, regions)` — `aggregate` is the same JSON shape as
    `analyze_contrast_v2` plus a new `regionsUncertain` count; `regions` is
    the full per-region diagnostic list (not part of the JSON contract,
    available for reports/tests/debugging)."""
    ratios: list[float] = []
    regions: list[dict[str, Any]] = []
    skipped_flat = 0
    uncertain_count = 0
    h, w = img.shape[:2]
    n_boxes = len(ocr_data["text"])
    pad = 3

    for i in range(n_boxes):
        text = ocr_data["text"][i]
        conf = int(ocr_data["conf"][i])
        if conf < 60 or not text.strip():
            continue
        x, y, bw, bh = (ocr_data["left"][i], ocr_data["top"][i], ocr_data["width"][i], ocr_data["height"][i])
        bbox = (x, y, bw, bh)
        y0, y1 = max(0, y - pad), min(h, y + bh + pad)
        x0, x1 = max(0, x - pad), min(w, x + bw + pad)
        region = img[y0:y1, x0:x1]
        if region.size == 0:
            skipped_flat += 1
            continue

        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        if float(gray.std()) < 5.0:
            skipped_flat += 1
            regions.append(_uncertain_region(text, bbox, conf, reason="flat_region"))
            continue

        otsu_threshold, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mask_bool = mask.astype(bool)
        # Same "smaller cluster = ink" rule as V2 — unchanged.
        ink_mask = mask_bool if mask_bool.sum() <= (~mask_bool).sum() else ~mask_bool
        bg_mask = ~ink_mask
        ink_size = int(ink_mask.sum())

        if ink_size < _MIN_INK_CLUSTER_PIXELS:
            uncertain_count += 1
            regions.append(
                _uncertain_region(
                    text, bbox, conf, reason="ink_cluster_too_small",
                    otsuThreshold=round(float(otsu_threshold), 1), inkClusterSize=ink_size,
                )
            )
            continue

        ink_gray = gray[ink_mask]
        bg_gray = gray[bg_mask]
        polarity = "dark_on_light" if float(ink_gray.mean()) < float(bg_gray.mean()) else "light_on_dark"

        # Core pixels: the most extreme `_CORE_PERCENTILE`% of the ink
        # cluster by luminance — a set, never a single min/max pixel.
        if polarity == "dark_on_light":
            core_threshold = np.percentile(ink_gray, _CORE_PERCENTILE)
            core_mask = ink_mask & (gray <= core_threshold)
        else:
            core_threshold = np.percentile(ink_gray, 100 - _CORE_PERCENTILE)
            core_mask = ink_mask & (gray >= core_threshold)

        core_pixels = region[core_mask]
        core_count = len(core_pixels)

        if core_count < _MIN_CORE_PIXELS:
            uncertain_count += 1
            regions.append(
                _uncertain_region(
                    text, bbox, conf, reason="core_sample_too_small",
                    otsuThreshold=round(float(otsu_threshold), 1), polarity=polarity,
                    inkClusterSize=ink_size, corePixelCount=core_count,
                )
            )
            continue

        # Robust per-channel median of the core sample — never a single pixel.
        foreground_rgb = np.median(core_pixels, axis=0)[::-1]  # BGR -> RGB

        # Background: only background-cluster pixels connected to the crop
        # border, from the original RGB image.
        border_bg_mask = _border_connected_mask(bg_mask)
        if not np.any(border_bg_mask):
            border_bg_mask = bg_mask
        background_rgb = region[border_bg_mask].mean(axis=0)[::-1]

        ratio = round(contrast_ratio(foreground_rgb.tolist(), background_rgb.tolist()), 2)
        ratios.append(ratio)
        confidence = round(min(1.0, core_count / _CONFIDENT_CORE_PIXELS), 2)

        regions.append(
            {
                "text": text,
                "bbox": bbox,
                "ocrConfidence": conf,
                "otsuThreshold": round(float(otsu_threshold), 1),
                "polarity": polarity,
                "inkClusterSize": ink_size,
                "corePixelPercentile": _CORE_PERCENTILE,
                "corePixelCount": core_count,
                "foregroundRgb": tuple(round(float(c), 1) for c in foreground_rgb),
                "backgroundRgb": tuple(round(float(c), 1) for c in background_rgb),
                "ratio": ratio,
                "confidence": confidence,
                "status": "valid",
                "aa": "pass" if ratio >= 4.5 else "fail",
            }
        )

    avg_ratio = round(float(np.mean(ratios)), 2) if ratios else None
    below_aa = sum(1 for r in ratios if r < 4.5)
    aggregate = {
        "averageContrastRatio": avg_ratio,
        "regionsAnalyzed": len(ratios),
        "regionsSkipped": skipped_flat,
        "regionsUncertain": uncertain_count,
        "regionsBelowAAThreshold": below_aa,
        "source": (
            "WCAG 2.1 AA (4.5:1 normal text); Otsu ink/paper separation, foreground estimated "
            "from the darkest/lightest 15% core of the ink cluster via a per-channel median "
            "(robust to anti-aliased edge pixels dominating small text), background from "
            "border-connected background pixels only; unstable regions reported as uncertain, "
            "never fabricated (corrected-v2, contrast sampling v3)"
        ),
    }
    return aggregate, regions


# ---------- Fix 1c (corrected-v3): Dual-estimate contrast — confirmed vs. borderline ----------
#
# A per-region cross-check against three independent whole-region methods
# (Otsu-cluster mean, percentile-decile, k-means) found V3's core-percentile
# estimate measurably higher than all three on small anti-aliased paragraph
# text — internal consistency across V3's own runs is not evidence that V3
# is *accurate* relative to a genuinely different estimation approach, and
# the gap is large enough to flip the WCAG AA classification.
#
# Rather than picking a side, V4 computes two foreground estimates from the
# same ink cluster and the same (border-connected) background:
#   - `core`: V3's estimate — the per-channel median of only the darkest/
#     lightest 15% of the ink cluster;
#   - `conservative`: the per-channel median of the ENTIRE ink cluster — a
#     robust statistic (median, not mean), but one that still reflects
#     whichever pixel population dominates the cluster, which for small
#     anti-aliased text is the diluted edge-blend majority, not the ink
#     core.
# A region is a *confirmed* pass/fail only when both estimates agree on
# which side of 4.5:1 they land. When they disagree, the region is
# `uncertain` / `aaResult: "borderline"` — both ratios and the resulting
# range are reported, a single ratio is never fabricated, and the region is
# never counted as either a confirmed pass or a confirmed violation.

_AA_THRESHOLD = 4.5


def _unresolved_region_v4(text: str, bbox: tuple[int, int, int, int], ocr_confidence: int, reason: str, **extra: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "text": text,
        "bbox": bbox,
        "ocrConfidence": ocr_confidence,
        "status": "uncertain",
        "reason": reason,
        "ratio": None,
        "range": None,
        "aaResult": None,
        "confidence": 0.0,
    }
    row.update(extra)
    return row


def analyze_contrast_v4(img: np.ndarray, ocr_data: dict) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Returns `(aggregate, regions)`. `aggregate` matches `analyze_contrast_v3`'s
    shape plus `regionsBorderline`; `averageContrastRatio`/`regionsAnalyzed`/
    `regionsBelowAAThreshold` only ever reflect *confirmed* (both-estimates-
    agree) regions — borderline and insufficient-sample regions contribute
    to neither. `regions` is the full per-region diagnostic list (not part
    of the JSON contract, available for reports/tests/debugging)."""
    confirmed_ratios: list[float] = []
    regions: list[dict[str, Any]] = []
    skipped_flat = 0
    uncertain_count = 0
    borderline_count = 0
    h, w = img.shape[:2]
    n_boxes = len(ocr_data["text"])
    pad = 3

    for i in range(n_boxes):
        text = ocr_data["text"][i]
        conf = int(ocr_data["conf"][i])
        if conf < 60 or not text.strip():
            continue
        x, y, bw, bh = (ocr_data["left"][i], ocr_data["top"][i], ocr_data["width"][i], ocr_data["height"][i])
        bbox = (x, y, bw, bh)
        y0, y1 = max(0, y - pad), min(h, y + bh + pad)
        x0, x1 = max(0, x - pad), min(w, x + bw + pad)
        region = img[y0:y1, x0:x1]
        if region.size == 0:
            skipped_flat += 1
            continue

        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        if float(gray.std()) < 5.0:
            skipped_flat += 1
            regions.append(_unresolved_region_v4(text, bbox, conf, reason="flat_region"))
            continue

        otsu_threshold, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mask_bool = mask.astype(bool)
        ink_mask = mask_bool if mask_bool.sum() <= (~mask_bool).sum() else ~mask_bool
        bg_mask = ~ink_mask
        ink_size = int(ink_mask.sum())

        if ink_size < _MIN_INK_CLUSTER_PIXELS:
            uncertain_count += 1
            regions.append(
                _unresolved_region_v4(
                    text, bbox, conf, reason="ink_cluster_too_small",
                    otsuThreshold=round(float(otsu_threshold), 1), inkClusterSize=ink_size,
                )
            )
            continue

        ink_gray = gray[ink_mask]
        bg_gray = gray[bg_mask]
        polarity = "dark_on_light" if float(ink_gray.mean()) < float(bg_gray.mean()) else "light_on_dark"

        if polarity == "dark_on_light":
            core_threshold = np.percentile(ink_gray, _CORE_PERCENTILE)
            core_mask = ink_mask & (gray <= core_threshold)
        else:
            core_threshold = np.percentile(ink_gray, 100 - _CORE_PERCENTILE)
            core_mask = ink_mask & (gray >= core_threshold)

        core_pixels = region[core_mask]
        core_count = len(core_pixels)

        if core_count < _MIN_CORE_PIXELS:
            uncertain_count += 1
            regions.append(
                _unresolved_region_v4(
                    text, bbox, conf, reason="core_sample_too_small",
                    otsuThreshold=round(float(otsu_threshold), 1), polarity=polarity,
                    inkClusterSize=ink_size, corePixelCount=core_count,
                )
            )
            continue

        # Two foreground estimates from the SAME ink cluster and the SAME
        # background — only the reduction statistic (and how much of the
        # cluster it's computed over) differs.
        core_fg = np.median(core_pixels, axis=0)[::-1]  # BGR -> RGB
        conservative_fg = np.median(region[ink_mask], axis=0)[::-1]

        border_bg_mask = _border_connected_mask(bg_mask)
        if not np.any(border_bg_mask):
            border_bg_mask = bg_mask
        background_rgb = region[border_bg_mask].mean(axis=0)[::-1]

        core_ratio = round(contrast_ratio(core_fg.tolist(), background_rgb.tolist()), 2)
        conservative_ratio = round(contrast_ratio(conservative_fg.tolist(), background_rgb.tolist()), 2)
        core_pass = core_ratio >= _AA_THRESHOLD
        conservative_pass = conservative_ratio >= _AA_THRESHOLD
        confidence = round(min(1.0, core_count / _CONFIDENT_CORE_PIXELS), 2)

        base_fields = {
            "text": text,
            "bbox": bbox,
            "ocrConfidence": conf,
            "otsuThreshold": round(float(otsu_threshold), 1),
            "polarity": polarity,
            "inkClusterSize": ink_size,
            "corePixelPercentile": _CORE_PERCENTILE,
            "corePixelCount": core_count,
            "coreForegroundRgb": tuple(round(float(c), 1) for c in core_fg),
            "conservativeForegroundRgb": tuple(round(float(c), 1) for c in conservative_fg),
            "backgroundRgb": tuple(round(float(c), 1) for c in background_rgb),
            "coreRatio": core_ratio,
            "conservativeRatio": conservative_ratio,
            "confidence": confidence,
        }

        if core_pass == conservative_pass:
            confirmed_ratios.append(core_ratio)
            regions.append(
                {
                    **base_fields,
                    "ratio": core_ratio,
                    "range": None,
                    "status": "valid",
                    "aaResult": "pass" if core_pass else "fail",
                }
            )
        else:
            borderline_count += 1
            low, high = sorted([core_ratio, conservative_ratio])
            regions.append(
                {
                    **base_fields,
                    "ratio": None,
                    "range": [low, high],
                    "status": "uncertain",
                    "reason": "estimate_disagreement",
                    "aaResult": "borderline",
                }
            )

    avg_ratio = round(float(np.mean(confirmed_ratios)), 2) if confirmed_ratios else None
    below_aa = sum(1 for r in confirmed_ratios if r < _AA_THRESHOLD)
    aggregate = {
        "averageContrastRatio": avg_ratio,
        "regionsAnalyzed": len(confirmed_ratios),
        "regionsSkipped": skipped_flat,
        "regionsUncertain": uncertain_count,
        "regionsBorderline": borderline_count,
        "regionsBelowAAThreshold": below_aa,
        "source": (
            "WCAG 2.1 AA (4.5:1 normal text); dual foreground estimate per ink cluster — a core "
            "estimate (darkest/lightest 15% of the ink cluster, per-channel median) and a "
            "conservative estimate (per-channel median of the entire ink cluster); a region is a "
            "confirmed pass/fail only when both agree, otherwise reported borderline with both "
            "ratios and the resulting range — never fabricated or forced to a single value "
            "(corrected-v3, contrast sampling v4)"
        ),
    }
    return aggregate, regions


# ---------- Fix 2c (post-audit follow-up): full-bleed background blind spot ----------
#
# An independent re-verification against a real screenshot (a solid-color
# modal: a green full-bleed background behind a white card with a button and
# a text link) found `detectedElementCount`/`filteredElementCount`/
# `smallTargetsBelow44px` all reporting **zero**, and Fitts's/Hick's Law both
# reporting no data — not because the screen has no controls, but because
# `cv2.findContours(..., cv2.RETR_EXTERNAL, ...)` only returns the outermost
# boundary of each *top-level* connected foreground component. On a screen
# like this, the full-bleed background thresholds as ONE giant foreground
# blob spanning the entire image; the white card is a *hole* in that blob;
# every real control inside the card (the button, the link) is a foreground
# island nested inside that hole — and RETR_EXTERNAL never returns anything
# nested inside a hole. Every element on the card silently vanishes.
#
# Fixed via `cv2.RETR_CCOMP`, which returns a 2-level hierarchy (external
# boundaries + hole boundaries) and — per OpenCV's own documented CCOMP
# semantics — re-promotes any foreground island sitting inside a hole back
# to the top (external) level, so the card's contents become visible
# without the unbounded recursion of full `RETR_TREE` (which would also
# recurse into individual anti-aliased letter strokes/counters and explode
# the element count with duplicate ink fragments).
#
# Switching retrieval modes alone is not sufficient: CCOMP also (a) still
# returns the full-bleed background blob itself as a bogus "element"
# candidate, and (b) can return near-duplicate contours for the same
# physical edge — an anti-aliased/gradient edge sometimes crosses the
# binary threshold twice a few pixels apart, or a large button's "hole"
# (its interior, minus a small label) has almost the same bounding box as
# the button's own outer contour. `_extract_contour_elements` below handles
# both, disclosed via `backgroundContourExcludedCount` and
# `duplicateNestedContourExcludedCount` rather than silently dropped:
#   1. a contour is classified as `background`, not an element candidate,
#      if its bounding box spans (almost) the entire image;
#   2. remaining contours are deduplicated by containment + IoU + area
#      ratio: a child contour whose bbox nearly coincides with its parent's
#      (high IoU, high area ratio) is the same physical edge detected
#      twice and is dropped in favor of the outer (larger) one; a child
#      that is meaningfully smaller than its parent (an icon inside a
#      button, a checkbox glyph, a letter's inner counter) is kept as its
#      own distinct candidate, same as before.
# OCR-sourced text boxes are untouched by any of this — they are added
# separately below and were never contour candidates to begin with.
_BACKGROUND_AREA_RATIO = 0.55  # bbox area / image area at/above which a contour is classified as the full-bleed background
_BACKGROUND_EDGE_TOUCH_PX = 2  # a contour edge within this many px of the image border counts as "touching" that border
_DUPLICATE_IOU_THRESHOLD = 0.75  # child/parent bbox IoU at/above which they're treated as the same physical edge detected twice
_DUPLICATE_AREA_RATIO_THRESHOLD = 0.7  # child bbox area / parent bbox area at/above which a contained contour is a duplicate, not a distinct nested feature

# Fix D.1 (independent-audit follow-up): dark full-bleed background swallows
# real light-colored controls. `_extract_contour_elements` thresholds on a
# single fixed polarity (`gray < 200` = foreground, i.e. "dark ink on light
# background"). A DARK full-bleed background is still foreground under that
# same threshold (its pixels are also < 200), so `_is_background_contour`
# correctly classifies it as background and drops it -- but any light-colored
# control sitting directly on it (a button, a checkbox) is, by construction,
# a CCOMP "hole" of that background contour (background-colored interior
# negative space, from the threshold's point of view), and the hole-exclusion
# rule a few lines below drops every hole unconditionally, on the assumption
# that a hole is always empty interior space (a letter's counter, a button's
# subtle highlight). For an ordinary light-mode screen that assumption holds;
# for a dark full-bleed background it does not -- the "hole" often *is* the
# real, tappable content.
# The fix only reconsiders holes whose immediate parent contour was (a)
# classified as the background by `_is_background_contour` (geometry: full
# area coverage or edge-to-edge span) AND (b) confirmed dark by directly
# sampling that contour's own pixels (mean < `_DARK_BACKGROUND_MEAN_THRESHOLD`,
# the same 200 cutoff used everywhere else in this module). This is
# deliberately narrow: an ordinary hole inside a normal-sized dark button or
# glyph (never classified as "background") is untouched and still dropped
# exactly as before -- only the specific full-bleed/edge-spanning dark
# background case is affected, so a light theme's behavior is unchanged (no
# contour is ever geometrically classified as "background" there in the
# first place, since a light background is never foreground under this
# threshold to begin with). A recovered hole still passes through the same
# background/size-floor/size-ceiling checks as any other candidate, so a
# recovered "hole" that is itself just a large light container (not a real
# control) is still correctly dropped.
_DARK_BACKGROUND_MEAN_THRESHOLD = 200


def _is_background_contour(bbox: tuple[int, int, int, int], img_shape: tuple[int, ...]) -> bool:
    x, y, cw, ch = bbox
    img_h, img_w = img_shape[:2]
    if img_w <= 0 or img_h <= 0:
        return False
    if (cw * ch) / (img_w * img_h) >= _BACKGROUND_AREA_RATIO:
        return True
    # A full-bleed background can also be a thin/irregular shape (e.g. a
    # frame) with modest raw area but that still spans every edge of the
    # image -- area alone would miss it.
    touches_left = x <= _BACKGROUND_EDGE_TOUCH_PX
    touches_top = y <= _BACKGROUND_EDGE_TOUCH_PX
    touches_right = (x + cw) >= (img_w - _BACKGROUND_EDGE_TOUCH_PX)
    touches_bottom = (y + ch) >= (img_h - _BACKGROUND_EDGE_TOUCH_PX)
    return touches_left and touches_top and touches_right and touches_bottom


def _bbox_iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix0, iy0 = max(ax, bx), max(ay, by)
    ix1, iy1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter == 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _bbox_contains(parent: tuple[int, int, int, int], child: tuple[int, int, int, int], tolerance: int = 2) -> bool:
    px, py, pw, ph = parent
    cx, cy, cw, ch = child
    return (
        cx >= px - tolerance
        and cy >= py - tolerance
        and cx + cw <= px + pw + tolerance
        and cy + ch <= py + ph + tolerance
    )


def _dedupe_nested_contours(candidates: list[dict]) -> list[dict]:
    """`candidates`: dicts with `bbox` (x, y, w, h) and `area`. Processes
    largest-area-first; drops a contour whose bbox is contained in an
    already-kept, larger contour AND is a near-duplicate of that parent's
    edge (high IoU + high area ratio) — the same physical shape detected
    twice via nested threshold crossings. A contained contour that is
    meaningfully smaller than its parent is kept as a distinct element."""
    ordered = sorted(candidates, key=lambda c: c["area"], reverse=True)
    kept: list[dict] = []
    for cand in ordered:
        is_duplicate = False
        for parent in kept:
            if parent["area"] <= 0 or not _bbox_contains(parent["bbox"], cand["bbox"]):
                continue
            area_ratio = cand["area"] / parent["area"]
            if area_ratio >= _DUPLICATE_AREA_RATIO_THRESHOLD and _bbox_iou(parent["bbox"], cand["bbox"]) >= _DUPLICATE_IOU_THRESHOLD:
                is_duplicate = True
                break
        if not is_duplicate:
            kept.append(cand)
    return kept


def _region_mean_gray(gray: np.ndarray, contour: np.ndarray) -> float | None:
    """Mean grayscale value of the pixels enclosed by `contour` (filled),
    used to tell a genuinely dark background contour from a light one —
    see Fix D.1."""
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, thickness=-1)
    region = gray[mask.astype(bool)]
    if region.size == 0:
        return None
    return float(np.mean(region))


def _extract_contour_elements(img: np.ndarray) -> tuple[list[dict], dict[str, int]]:
    """Returns `(elements, debug_counts)`. Uses `cv2.RETR_CCOMP` (not
    `cv2.RETR_EXTERNAL`) so foreground islands nested inside a hole of a
    larger shape are still found, then applies two layers of filtering
    before anything is treated as an element candidate — see the "Fix 2c"
    module comment above for the full rationale:

    1. Hierarchy-based hole exclusion. `RETR_CCOMP`'s hierarchy marks every
       contour's `parent` index: a contour with `parent == -1` is a genuine
       foreground shape (either truly top-level, like the background, or a
       foreground island re-promoted from inside a hole, like a button
       sitting on a card); a contour with `parent != -1` is a *hole* —
       interior background-colored negative space enclosed by a shape (the
       light interior of a button, the light gap inside a card's border,
       the counter of a letter like 'o' or 'e'). Holes are never element
       candidates; without this, revealing nested content via CCOMP also
       floods `contourBasedCount` with the interior negative space of every
       shape that already has its own outer contour, silently inflating
       every downstream count.

       Fix D.1 exception: a hole whose immediate parent is a *dark*
       full-bleed background contour (classified below) is not empty
       interior space — it is real, light-colored foreground content (e.g.
       a button or checkbox sitting directly on a dark screen) that this
       single-polarity threshold would otherwise never see. Such holes are
       recovered as ordinary candidates, subject to every filter below
       exactly like any other contour, rather than dropped unconditionally.
       A hole whose parent is any other (non-background, e.g. an ordinary
       button or glyph) contour is untouched and still dropped as before —
       this keeps the exception narrow and light-theme behavior unchanged.
    2. Of the remaining (non-hole, or Fix-D.1-recovered) contours: the
       full-bleed background is classified out, then near-identical nested
       duplicates (the same physical edge detected twice via nested
       threshold crossings) are deduplicated by containment + IoU + area
       ratio.

    `debug_counts` is a diagnostic breakdown (not part of the JSON contract
    on its own, but surfaced into `elements_meta` as additive disclosure
    fields)."""
    h, w = img.shape[:2]
    img_area = h * w
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    raw_contours, hierarchy = cv2.findContours(thresh, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    parents = hierarchy[0][:, 3] if hierarchy is not None and len(raw_contours) else []

    # Fix D.1, pass 1: identify which top-level contours are a DARK
    # full-bleed background — only their direct-child holes get the
    # hole-recovery exception below. A light background is never a
    # top-level foreground contour under this threshold to begin with (its
    # pixels are >= 200), so this set is always empty for an ordinary
    # light-mode screen, and the exception never fires there.
    dark_background_indices: set[int] = set()
    for i, c in enumerate(raw_contours):
        if parents[i] != -1:
            continue
        x, y, cw, ch = cv2.boundingRect(c)
        if not _is_background_contour((x, y, cw, ch), img.shape):
            continue
        mean_gray = _region_mean_gray(gray, c)
        if mean_gray is not None and mean_gray < _DARK_BACKGROUND_MEAN_THRESHOLD:
            dark_background_indices.add(i)

    candidates: list[dict] = []
    hole_dropped = 0
    background_dropped = 0
    size_floor_dropped = 0
    size_ceiling_dropped = 0
    recovered_from_dark_background = 0
    for i, c in enumerate(raw_contours):
        is_recovered_hole = False
        if parents[i] != -1:
            if parents[i] not in dark_background_indices:
                hole_dropped += 1
                continue
            is_recovered_hole = True

        x, y, cw, ch = cv2.boundingRect(c)
        bbox = (x, y, cw, ch)
        area = cw * ch
        if _is_background_contour(bbox, img.shape):
            background_dropped += 1
            continue
        if area < 20 * 20:
            size_floor_dropped += 1
            continue
        if area > 0.30 * img_area:
            size_ceiling_dropped += 1
            continue
        candidates.append({"x": x, "y": y, "w": cw, "h": ch, "source": "contour", "area": area, "bbox": bbox})
        if is_recovered_hole:
            recovered_from_dark_background += 1

    deduped = _dedupe_nested_contours(candidates)
    duplicate_dropped = len(candidates) - len(deduped)

    elements = [{"x": e["x"], "y": e["y"], "w": e["w"], "h": e["h"], "source": "contour"} for e in deduped]
    debug_counts = {
        "rawContourCount": len(raw_contours),
        "holeContourExcludedCount": hole_dropped,
        "backgroundContourExcludedCount": background_dropped,
        "duplicateNestedContourExcludedCount": duplicate_dropped,
        "sizeFloorDropped": size_floor_dropped,
        "sizeCeilingDropped": size_ceiling_dropped,
        "darkBackgroundDetected": bool(dark_background_indices),
        "recoveredFromDarkBackgroundCount": recovered_from_dark_background,
    }
    return elements, debug_counts


# ---------- Fixes 2 & 3: Elements (contour-only small targets, grid exclusion) ----------
#
# Fix 3b (post-audit follow-up): an independent re-verification found the
# original Fix 3 (a single dense *row* of >= 8 near-uniform-size elements =
# "repeating grid") produced false positives on perfectly ordinary UI: a
# bottom navigation bar, a toolbar, a filter-chip row, or any single-row
# group of >= 8 similarly-sized icons is indistinguishable from that rule's
# definition of "system chrome" and got silently excluded. A real on-screen
# keyboard is not just "one uniform row" — it is a multi-row, multi-column,
# tightly-packed 2D grid. The detector below requires ALL of:
#   - enough elements overall (row_count * column_count floor);
#   - each candidate row has enough columns (`_GRID_MIN_COLUMNS`);
#   - uniform element size within each row (height/width coefficient of
#     variation, same statistic as before);
#   - tightly-packed horizontal spacing within each row, measured as a
#     *normalized* ratio (gap / median element width) rather than an
#     absolute pixel gap, so it scales with element size;
#   - at least `_GRID_MIN_ROWS` such candidate rows stacked with a small,
#     normalized vertical gap between them (gap / median element height).
# A single row — however uniform or tightly packed — never qualifies on its
# own, since `_GRID_MIN_ROWS` requires multiple stacked rows before anything
# is excluded. A multi-row but *sparse* grid (e.g. a home-screen icon grid
# with generous spacing) also does not qualify, since it fails the gap-ratio
# checks despite satisfying row/column counts.
def _row_band_contour_indices(elements: list[dict], indices: list[int]) -> list[list[int]]:
    """Groups `indices` (all contour-sourced) into horizontal row bands by
    vertical-center proximity, top to bottom."""
    if not indices:
        return []
    ordered = sorted(indices, key=lambda i: elements[i]["y"] + elements[i]["h"] / 2)
    bands: list[list[int]] = [[ordered[0]]]
    for prev_i, i in zip(ordered, ordered[1:]):
        prev_cy = elements[prev_i]["y"] + elements[prev_i]["h"] / 2
        cy = elements[i]["y"] + elements[i]["h"] / 2
        ref_h = elements[prev_i]["h"]
        tolerance = max(ref_h * _GRID_ROW_BAND_Y_TOLERANCE_RATIO, _GRID_ROW_BAND_Y_TOLERANCE_MIN_PX)
        if (cy - prev_cy) > tolerance:
            bands.append([i])
        else:
            bands[-1].append(i)
    return bands


def _is_uniform_size_row(elements: list[dict], row: list[int]) -> bool:
    heights = np.array([elements[i]["h"] for i in row], dtype=float)
    widths = np.array([elements[i]["w"] for i in row], dtype=float)
    if heights.mean() == 0 or widths.mean() == 0:
        return False
    height_cv = heights.std() / heights.mean()
    width_cv = widths.std() / widths.mean()
    return height_cv < _GRID_HEIGHT_CV_THRESHOLD and width_cv < _GRID_WIDTH_CV_THRESHOLD


def _row_horizontal_gap_ratio(elements: list[dict], row: list[int]) -> float | None:
    """Median (gap between horizontally-adjacent elements) / median element
    width, for `row` sorted left to right. Small -> tightly packed (e.g. a
    keyboard row); large -> spread out (e.g. a bottom nav bar or toolbar)."""
    ordered = sorted(row, key=lambda i: elements[i]["x"])
    widths = np.array([elements[i]["w"] for i in ordered], dtype=float)
    median_width = float(np.median(widths))
    if median_width <= 0:
        return None
    gaps = [
        elements[i]["x"] - (elements[prev_i]["x"] + elements[prev_i]["w"])
        for prev_i, i in zip(ordered, ordered[1:])
    ]
    return float(np.median(gaps)) / median_width


def _detect_repeating_grid_indices(elements: list[dict]) -> set[int]:
    """Flags a tightly-packed, multi-row, multi-column band of near-uniform
    contour elements (e.g. an on-screen system keyboard) as repeating system
    chrome, disclosed via `repeatingGridExcludedCount` rather than silently
    dropped. A single row never qualifies, regardless of size uniformity or
    horizontal density — see the module comment above for the rationale."""
    contour_idx = [i for i, e in enumerate(elements) if e["source"] == "contour"]
    if len(contour_idx) < _GRID_MIN_TOTAL_ELEMENTS:
        return set()

    rows = _row_band_contour_indices(elements, contour_idx)

    row_candidates: list[list[int]] = []
    for row in rows:
        if len(row) < _GRID_MIN_COLUMNS:
            continue
        if not _is_uniform_size_row(elements, row):
            continue
        gap_ratio = _row_horizontal_gap_ratio(elements, row)
        if gap_ratio is None or gap_ratio > _GRID_MAX_HORIZONTAL_GAP_RATIO:
            continue
        row_candidates.append(row)

    if len(row_candidates) < _GRID_MIN_ROWS:
        return set()

    # Stack vertically-adjacent row candidates (rows are already top-to-
    # bottom ordered; using each row's actual y-extent rather than list
    # adjacency correctly breaks the stack across any skipped non-candidate
    # row in between).
    excluded: set[int] = set()
    stack: list[list[int]] = [row_candidates[0]]

    def _flush(s: list[list[int]]) -> None:
        if len(s) >= _GRID_MIN_ROWS:
            for r in s:
                excluded.update(r)

    for prev_row, row in zip(row_candidates, row_candidates[1:]):
        prev_bottom = max(elements[i]["y"] + elements[i]["h"] for i in prev_row)
        top = min(elements[i]["y"] for i in row)
        combined_heights = [elements[i]["h"] for i in prev_row + row]
        median_height = float(np.median(combined_heights))
        vertical_gap_ratio = max(0.0, top - prev_bottom) / median_height if median_height > 0 else float("inf")
        if vertical_gap_ratio <= _GRID_MAX_VERTICAL_GAP_RATIO:
            stack.append(row)
        else:
            _flush(stack)
            stack = [row]
    _flush(stack)

    return excluded


# ---------- Fix 2d (post-audit follow-up): text-glyph contours vs. interactive targets ----------
#
# A re-verification of the Fix 2c background/hole fix against a real
# screenshot (a solid-color modal with a "Click Me" button and a
# "Congratulations!" heading) found that the fix, having correctly stopped
# discarding nested elements, now surfaced a *different* problem: a large,
# bold heading letter ("C") is just as much a ">=20x20px dark contour" as a
# real button is, and both were being treated as "control-like" interactive
# targets — corrupting Hick's Law (`filteredElementCount`/`hicksLawEstimateMs`
# counted the heading letter as a second "choice") and Fitts's Law (which
# computed a nearest-neighbor distance between the button and the heading
# letter — a spatial relationship with no HCI meaning, since the letter is
# not a tap target).
#
# `contourBasedCount` still reports every *visual* contour (unchanged
# meaning). A new, stricter `interactiveTargets` list — used by Hick's Law,
# Fitts's Law, and `smallTargetsBelow44px` — excludes any contour that is
# substantially coincident with OCR-detected text ink and not meaningfully
# larger than that text: the contour more or less *is* the glyph, not a
# container around it. A contour whose OCR-matched text sits inside a
# *much larger* contour is kept (a labeled button: the button fill is a
# real target, its label is not evidence against that). A contour with no
# OCR correlate at all — an icon, a checkbox, an un-OCR'd button — is never
# touched by this and is kept regardless of size (checkboxes and icon-only
# buttons must not be swept away just for being small; that is a separate,
# already-disclosed signal via `smallTargetsBelow44px`, not a reason for
# exclusion).
_TEXT_GLYPH_OCR_OVERLAP_RATIO = 0.6  # overlap-area / smaller-shape-area at/above which a contour and an OCR box are considered the same ink
_LABELED_CONTROL_MIN_SIZE_RATIO = 1.8  # contour area / matched-OCR-box area at/above which the contour is a container (labeled button), not glyph ink


def _ocr_word_boxes(ocr_data: dict) -> list[tuple[int, int, int, int]]:
    boxes: list[tuple[int, int, int, int]] = []
    n_boxes = len(ocr_data["text"])
    for i in range(n_boxes):
        if int(ocr_data["conf"][i]) < 60 or not ocr_data["text"][i].strip():
            continue
        boxes.append((ocr_data["left"][i], ocr_data["top"][i], ocr_data["width"][i], ocr_data["height"][i]))
    return boxes


def _overlap_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix0, iy0 = max(ax, bx), max(ay, by)
    ix1, iy1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    return max(0, ix1 - ix0) * max(0, iy1 - iy0)


def _classify_interactive_targets(
    contour_elements: list[dict], ocr_data: dict
) -> tuple[list[dict], list[dict[str, Any]]]:
    """Returns `(interactive_targets, excluded_debug)`. `excluded_debug` is a
    per-contour diagnostic list (`{"bbox", "reason"}`) — not part of the
    JSON contract, available for tests/reporting, analogous to
    `analyze_contrast_v4`'s `regions`."""
    ocr_boxes = _ocr_word_boxes(ocr_data)
    kept: list[dict] = []
    excluded_debug: list[dict[str, Any]] = []
    for e in contour_elements:
        bbox = (e["x"], e["y"], e["w"], e["h"])
        area = e["w"] * e["h"]
        is_glyph = False
        for ob in ocr_boxes:
            ob_area = ob[2] * ob[3]
            if ob_area <= 0 or area <= 0:
                continue
            overlap = _overlap_area(bbox, ob)
            if overlap <= 0:
                continue
            smaller_area = min(area, ob_area)
            if overlap / smaller_area >= _TEXT_GLYPH_OCR_OVERLAP_RATIO and area < _LABELED_CONTROL_MIN_SIZE_RATIO * ob_area:
                is_glyph = True
                break
        if is_glyph:
            excluded_debug.append({"bbox": bbox, "reason": "text_glyph_ocr_match"})
        else:
            kept.append(e)
    return kept, excluded_debug


# ---------- Fix 2e (post-audit follow-up): system-keyboard region detection ----------
#
# A re-verification against a real screenshot with an on-screen iOS keyboard
# found ~160 keyboard-related contours still counted as interactive targets
# (`repeatingGridExcludedCount: 0`) — the existing repeating-grid detector
# (Fix 3b) is a *geometric* heuristic (uniform element size, tight row/column
# spacing) that assumes a grid's contours look like clean, uniform key-box
# rectangles. A real keyboard's key *fill* is light (white/light-gray) and
# never thresholds as a dark contour; only the darker letter *ink* and thin
# per-key separator lines do, and those are irregular in size and spaced
# much more loosely (relative to their own width) than the geometric
# detector's density thresholds expect — patching that detector with yet
# another geometric threshold was deliberately avoided (per the fix
# request) since it would remain exactly as brittle to the next keyboard
# layout, font, or scale.
#
# `_detect_keyboard_region` is a purpose-built, independent detector that
# only ever answers "is there a system keyboard here", combining SIX
# signals, no one of which is trusted alone:
#   - row_count: 3-6 dense horizontal bands of small contour/OCR boxes
#     (each band must ALSO individually span most of the screen width —
#     this is what actually distinguishes a keyboard row from a dense but
#     narrow text line/link, e.g. "Forgot your password?", that happens to
#     sit close enough in y to an adjacent real keyboard row to otherwise
#     look like just another dense band);
#   - width_coverage: the overall region spans most of the screen width;
#   - position: the region sits in the bottom part of the screen;
#   - qwerty_sequence: OCR text matches a QWERTY/ASDF/ZXCV row-letter
#     sequence (substring match either direction, so Tesseract merging an
#     entire row into one token, e.g. "QWERTY", still matches);
#   - keyword: OCR text matches a narrow, low-collision keyboard-specific
#     vocabulary (space/shift/123/qwerty only — "go"/"done"/"next"/
#     "search"/"send"/"join" were deliberately excluded: they are real
#     iOS return-key labels too, but collide far too often with ordinary
#     app button/tab text, e.g. a "Search" tab or a "Send" button, to be
#     reliable keyboard evidence on their own);
#   - single_char_ratio: a high fraction of OCR tokens in the region are
#     exactly one character (a numeric keypad's digits, in particular).
# A candidate row-band must ALSO pass a size-uniformity check (the same
# height/width coefficient-of-variation statistic `_detect_repeating_grid_indices`
# uses) before it counts as a row at all — a real screenshot (a "Preferences
# & Account" list with chip-remove "x"/"+" icons and chevrons) showed that
# width coverage and density alone still let a content-heavy, bottom-
# anchored list of *mixed*-size elements (long text labels next to small
# icons) masquerade as row-like; a keyboard row's keys are one consistent
# size; an ordinary list row mixing a label and an icon is not.
# The three geometric signals (row/width/position) are capped at 0.45 of
# the total weight — deliberately below the 0.55 "detected" threshold — so
# pure geometry, with zero textual corroboration, can never alone produce a
# confident keyboard detection; some QWERTY/keyword/single-char textual
# evidence is always required to cross that line. Note the per-bin
# uniformity gate above is what keeps a purely-geometric false positive
# (e.g. the "Preferences & Account" list) from ever reaching `row_count >
# 0` in the first place — its rows fail uniformity outright, so it never
# reaches even the geometric ceiling. Below 0.55 but at/above 0.40, the
# result is `degraded` (uncertain) rather than a confident yes or no:
# nothing is excluded, but the ambiguity is disclosed via
# `metricsStatus`/`warning` rather than silently resolved either way.
_KEYBOARD_SEARCH_BAND_RATIO = 0.45  # bottom fraction of the image searched for a keyboard
_KEYBOARD_ROW_BIN_HEIGHT_RATIO = 0.02  # row-density histogram bin height, relative to image height
_KEYBOARD_ROW_MIN_ELEMENTS = 4  # min contour/OCR elements in a bin for it to count as "dense"
_KEYBOARD_MIN_ROW_CLUSTERS = 3
_KEYBOARD_MAX_ROW_CLUSTERS = 6
_KEYBOARD_MIN_WIDTH_COVERAGE_RATIO = 0.75  # overall region width / image width, for a full width_signal
_KEYBOARD_ROW_WIDTH_COVERAGE_MIN = 0.65  # a candidate row-band must itself span this much of the width to count as a row (not a narrow text line)
_KEYBOARD_ROW_HEIGHT_CV_MAX = 0.15  # a candidate row-band's element heights must be this uniform (same statistic/threshold as the grid detector)
_KEYBOARD_ROW_WIDTH_CV_MAX = 0.40  # a candidate row-band's element widths must be this uniform -- slightly looser than the grid detector's 0.35, since letters (vs. keys) vary a bit more
_KEYBOARD_CONFIDENCE_DETECTED_THRESHOLD = 0.55
_KEYBOARD_CONFIDENCE_DEGRADED_THRESHOLD = 0.40
_KEYBOARD_ROW_LETTER_SEQUENCES = ("qwertyuiop", "asdfghjkl", "zxcvbnm")
_KEYBOARD_KEYWORDS = frozenset({"space", "shift", "123", "qwerty"})

_NO_KEYBOARD_RESULT: dict[str, Any] = {
    "detected": False,
    "confidence": 0.0,
    "bbox": None,
    "status": "none",
    "rowCount": 0,
    "widthCoverage": 0.0,
    "signals": {},
}


def _keyboard_search_candidates(elements: list[dict], ocr_data: dict, img_shape: tuple[int, ...]) -> tuple[
    list[tuple[int, int, int, int]], list[tuple[int, int, int, int]], list[tuple[str, tuple[int, int, int, int]]]
]:
    """Returns `(all_candidates, contour_candidates, ocr_words_in_band)`.
    `contour_candidates` is a subset used specifically for the row
    size-uniformity check — mixing in OCR word boxes there is wrong: OCR
    frequently merges an entire keyboard row's letters into one wide token
    (e.g. Tesseract reading "QWERTY" as a single ~1000px-wide box), which
    would swamp the variance against individual ~40px letter-ink contours
    and make every real keyboard row look non-uniform. Density, width-
    coverage, and position all still use `all_candidates` (both sources)."""
    img_h = img_shape[0]
    search_top = img_h * (1 - _KEYBOARD_SEARCH_BAND_RATIO)
    all_candidates: list[tuple[int, int, int, int]] = []
    contour_candidates: list[tuple[int, int, int, int]] = []
    for e in elements:
        cy = e["y"] + e["h"] / 2
        if cy >= search_top:
            bbox = (e["x"], e["y"], e["w"], e["h"])
            all_candidates.append(bbox)
            if e["source"] == "contour":
                contour_candidates.append(bbox)

    ocr_words_in_band: list[tuple[str, tuple[int, int, int, int]]] = []
    n_boxes = len(ocr_data["text"])
    for i in range(n_boxes):
        text = ocr_data["text"][i].strip()
        if not text:
            continue
        y, h_ = ocr_data["top"][i], ocr_data["height"][i]
        if (y + h_ / 2) >= search_top:
            bbox = (ocr_data["left"][i], y, ocr_data["width"][i], h_)
            ocr_words_in_band.append((text, bbox))
            all_candidates.append(bbox)  # OCR words also feed the row-density histogram
    return all_candidates, contour_candidates, ocr_words_in_band


def _detect_keyboard_region(elements: list[dict], ocr_data: dict, img_shape: tuple[int, ...]) -> dict[str, Any]:
    """Returns a dict describing whether a system keyboard was found in the
    bottom portion of the image — see the module comment above for the
    six-signal scoring rationale. Never raises; an empty/ambiguous result
    degrades gracefully to `status: "none"`."""
    img_h, img_w = img_shape[:2]
    candidates, contour_candidates, ocr_words_in_band = _keyboard_search_candidates(elements, ocr_data, img_shape)
    if not candidates:
        return dict(_NO_KEYBOARD_RESULT)

    bin_height = max(4, int(img_h * _KEYBOARD_ROW_BIN_HEIGHT_RATIO))
    bin_counts: dict[int, int] = {}
    for (x, y, w, h) in candidates:
        b = int((y + h / 2) // bin_height)
        bin_counts[b] = bin_counts.get(b, 0) + 1

    def _bin_range(b: int) -> tuple[float, float]:
        return b * bin_height, (b + 1) * bin_height

    def _bin_width_coverage(b: int) -> float:
        bin_lo, bin_hi = _bin_range(b)
        members = [c for c in candidates if bin_lo <= (c[1] + c[3] / 2) < bin_hi]
        if not members or img_w <= 0:
            return 0.0
        lo = min(c[0] for c in members)
        hi = max(c[0] + c[2] for c in members)
        return (hi - lo) / img_w

    def _bin_is_uniform(b: int) -> bool:
        # Deliberately contour-only: OCR frequently merges an entire
        # keyboard row into one wide token (e.g. "QWERTY" as a single
        # ~1000px-wide box), which would swamp the variance against
        # individual ~40px letter-ink contours and make every real
        # keyboard row look non-uniform if OCR boxes were included here.
        bin_lo, bin_hi = _bin_range(b)
        members = [c for c in contour_candidates if bin_lo <= (c[1] + c[3] / 2) < bin_hi]
        if len(members) < 2:
            return False
        heights = np.array([c[3] for c in members], dtype=float)
        widths = np.array([c[2] for c in members], dtype=float)
        if heights.mean() == 0 or widths.mean() == 0:
            return False
        return (heights.std() / heights.mean()) < _KEYBOARD_ROW_HEIGHT_CV_MAX and (
            widths.std() / widths.mean()
        ) < _KEYBOARD_ROW_WIDTH_CV_MAX

    # A candidate row-bin must ALSO span most of the screen width on its own
    # (distinguishes a keyboard row from a dense-but-narrow text line/link
    # that happens to sit close enough in y to a real keyboard row) AND
    # have reasonably uniform CONTOUR element sizes (distinguishes a
    # keyboard row -- keys are one consistent size -- from an ordinary
    # content list row that mixes a long text label with a small icon, e.g.
    # a settings row or a chip with a remove "x"). This is checked per
    # individual bin, before merging: a real keyboard row's letter-ink band
    # and its separator-line band immediately below it are two adjacent but
    # structurally different bins (very different element sizes between
    # them), and re-checking uniformity on the merged pair would wrongly
    # fail a genuine keyboard row.
    dense_bins = sorted(b for b, c in bin_counts.items() if c >= _KEYBOARD_ROW_MIN_ELEMENTS)
    valid_bins = [b for b in dense_bins if _bin_width_coverage(b) >= _KEYBOARD_ROW_WIDTH_COVERAGE_MIN and _bin_is_uniform(b)]

    row_clusters: list[list[int]] = []
    for b in valid_bins:
        if row_clusters and b - row_clusters[-1][-1] <= 1:
            row_clusters[-1].append(b)
        else:
            row_clusters.append([b])
    row_count = len(row_clusters)
    if not row_clusters:
        return dict(_NO_KEYBOARD_RESULT)

    if _KEYBOARD_MIN_ROW_CLUSTERS <= row_count <= _KEYBOARD_MAX_ROW_CLUSTERS:
        row_count_signal = 1.0
    elif row_count in (2, _KEYBOARD_MAX_ROW_CLUSTERS + 1, _KEYBOARD_MAX_ROW_CLUSTERS + 2):
        row_count_signal = 0.5
    else:
        row_count_signal = 0.0

    all_bins = [b for cluster in row_clusters for b in cluster]
    region_top = min(all_bins) * bin_height
    region_bottom = min((max(all_bins) + 1) * bin_height, img_h)
    region_elements = [c for c in candidates if region_top <= (c[1] + c[3] / 2) < region_bottom]

    xs0 = [c[0] for c in region_elements]
    xs1 = [c[0] + c[2] for c in region_elements]
    region_left, region_right = min(xs0), max(xs1)
    width_coverage = (region_right - region_left) / img_w if img_w else 0.0
    width_signal = min(1.0, width_coverage / _KEYBOARD_MIN_WIDTH_COVERAGE_RATIO) if width_coverage > 0 else 0.0

    position_signal = 1.0 if region_bottom >= img_h * 0.9 else max(0.0, (region_bottom / img_h - 0.5) * 2)

    words_lower = [w.lower() for w, _ in ocr_words_in_band]
    qwerty_hits = sum(
        1 for w in words_lower if len(w) >= 3 and any(w in row or row in w for row in _KEYBOARD_ROW_LETTER_SEQUENCES)
    )
    qwerty_signal = min(1.0, float(qwerty_hits))
    keyword_hits = sum(1 for w in words_lower if w in _KEYBOARD_KEYWORDS)
    keyword_signal = min(1.0, keyword_hits / 2.0)
    single_char_words = sum(1 for w in words_lower if len(w) == 1)
    single_char_ratio = single_char_words / len(words_lower) if words_lower else 0.0
    single_char_signal = min(1.0, single_char_ratio / 0.5)

    # Geometric signals (row/width/position) sum to 0.45, deliberately below
    # the 0.55 "detected" threshold, so pure geometry with zero textual
    # corroboration can never alone produce a confident detection.
    confidence = round(
        0.20 * row_count_signal
        + 0.15 * width_signal
        + 0.10 * position_signal
        + 0.20 * qwerty_signal
        + 0.20 * keyword_signal
        + 0.15 * single_char_signal,
        3,
    )
    if confidence >= _KEYBOARD_CONFIDENCE_DETECTED_THRESHOLD:
        status = "detected"
    elif confidence >= _KEYBOARD_CONFIDENCE_DEGRADED_THRESHOLD:
        status = "degraded"
    else:
        status = "none"

    # Once a keyboard is *confidently* detected from its reliable, uniform
    # letter rows, extend the exclusion bbox down to the bottom of the
    # search band. A keyboard's control row (space bar/123/Go) and its
    # emoji/mic row are, by design, NOT size-uniform with the letter keys
    # around them (a space bar is deliberately much wider), so they often
    # fail the same per-bin uniformity gate that correctly rejects ordinary
    # content rows (Fix 2e's false-positive fix) -- without this extension
    # those trailing rows would leak back into interactiveTargets despite
    # sitting inside an already-confirmed keyboard. This only ever widens
    # the excluded region for an already-`detected` result; it never
    # changes `confidence`/`status`, and never fires for `degraded`/`none`.
    if status == "detected":
        region_bottom = img_h

    return {
        "detected": status == "detected",
        "confidence": confidence,
        "bbox": (region_left, region_top, region_right - region_left, region_bottom - region_top),
        "status": status,
        "rowCount": row_count,
        "widthCoverage": round(width_coverage, 3),
        "signals": {
            "rowCountSignal": row_count_signal,
            "widthSignal": round(width_signal, 3),
            "positionSignal": round(position_signal, 3),
            "qwertySignal": qwerty_signal,
            "keywordSignal": keyword_signal,
            "singleCharSignal": round(single_char_signal, 3),
        },
    }


def _bbox_center_inside(bbox: tuple[int, int, int, int], region: tuple[float, float, float, float]) -> bool:
    x, y, w, h = bbox
    rx, ry, rw, rh = region
    cx, cy = x + w / 2, y + h / 2
    return rx <= cx <= rx + rw and ry <= cy <= ry + rh


def analyze_elements_v2(img: np.ndarray, ocr_data: dict) -> tuple[dict[str, Any], list[dict], list[dict]]:
    h, w = img.shape[:2]
    img_area = h * w

    contour_elements, contour_debug = _extract_contour_elements(img)
    elements: list[dict] = list(contour_elements)
    contour_count = len(elements)

    ocr_element_count = 0
    n_boxes = len(ocr_data["text"])
    for i in range(n_boxes):
        if int(ocr_data["conf"][i]) < 60 or not ocr_data["text"][i].strip():
            continue
        bw, bh = ocr_data["width"][i], ocr_data["height"][i]
        bx, by = ocr_data["left"][i], ocr_data["top"][i]
        area = bw * bh
        if area < 20 * 20 or area > 0.30 * img_area:
            continue
        elements.append({"x": bx, "y": by, "w": bw, "h": bh, "source": "ocr"})
        ocr_element_count += 1
        # Corrected: an OCR text-line box is not a tap-target candidate.
        # Ordinary text line-height is almost always <44px, so counting
        # these here made "small target" fire on virtually every text line
        # regardless of whether it was ever a control.

    n = len(elements)
    grid_excluded = _detect_repeating_grid_indices(elements)
    keyboard_result = _detect_keyboard_region(elements, ocr_data, img.shape)
    keyboard_bbox = keyboard_result["bbox"] if keyboard_result["status"] == "detected" else None

    # Fix 3b (shared interactive-element universe): Fitts's Law and Hick's
    # Law both reason about "how many interactive controls are on screen" —
    # they previously applied the grid exclusion inconsistently (Hick's Law
    # used it, Fitts's Law's control-like list did not, so a keyboard/grid
    # band the audit explicitly flagged as system chrome for Hick's Law
    # still fully contaminated Fitts's Law's nearest-neighbor distances).
    # This first pass is contour-sourced only (never OCR text boxes, which
    # are not tap-target candidates), excluding repeating-grid system
    # chrome, excluding degenerate zero-area contour noise, and — Fix 2e —
    # excluding contours inside a *confidently* detected system-keyboard
    # region (a `degraded`/uncertain detection excludes nothing; see the
    # module comment above `_detect_keyboard_region`). `visualContours`
    # (`elements`/`contourBasedCount`) is untouched either way — the
    # keyboard's key ink is still a real visual contour, it just isn't an
    # interactive target.
    keyboard_excluded_count = 0
    grid_filtered_contours: list[dict] = []
    for i, e in enumerate(elements):
        if e["source"] != "contour" or i in grid_excluded or e["w"] <= 0 or e["h"] <= 0:
            continue
        if keyboard_bbox is not None and _bbox_center_inside((e["x"], e["y"], e["w"], e["h"]), keyboard_bbox):
            keyboard_excluded_count += 1
            continue
        grid_filtered_contours.append(e)

    # Fix 2d (text-glyph contours vs. interactive targets): a large/bold
    # heading letter is just as much a ">=20x20px dark contour" as a real
    # button, and was being counted as a second "interactive target"
    # alongside it (see the module comment above `_classify_interactive_targets`).
    # `interactiveTargets` is the final, shared list Hick's Law, Fitts's
    # Law, and `smallTargetsBelow44px` all consume, so a contour that looks
    # like a button gets one consistent answer everywhere.
    interactive_targets, glyph_excluded_debug = _classify_interactive_targets(grid_filtered_contours, ocr_data)
    filtered_n = len(interactive_targets)

    system_ui_excluded_count = len(grid_excluded) + keyboard_excluded_count

    # Fix D.1 (independent-audit follow-up): silent-zero guard. Even with
    # the dark-background hole-recovery fix in `_extract_contour_elements`,
    # a screen could still legitimately end up with zero interactive
    # targets after filtering (a genuinely empty screen, content too small
    # to pass the size floor, content that is OCR-only, ...). Rather than
    # let `interactiveTargetCount == 0` present as indistinguishable from
    # "nothing is here" in exactly the case this fix targets, flag it
    # whenever ALL of the following hold: a large, dark, single-color
    # background was actually detected (`darkBackgroundDetected`), the
    # image had other visual structure beyond that flat background
    # (`rawContourCount > 1` — otherwise a genuinely empty dark screen would
    # be wrongly flagged), and zero interactive targets survived filtering
    # regardless. This does not fabricate a target; it downgrades
    # `metricsStatus` and adds a `warning` so `smallTargetsBelow44px` /
    # `hicksLawEstimateMs` / the composite score's `elementSize` component
    # are not silently trusted as "clean" for this analysis.
    dark_background_zero_target = (
        contour_debug["darkBackgroundDetected"]
        and contour_debug["rawContourCount"] > 1
        and filtered_n == 0
    )

    warnings: list[str] = []
    if keyboard_result["status"] == "degraded":
        warnings.append(
            "possible system keyboard may inflate interaction metrics "
            f"(confidence {keyboard_result['confidence']}, below the detection threshold)"
        )
    if dark_background_zero_target:
        warnings.append(
            "a large, dark, single-color background was detected with additional visual "
            "content on top of it, but zero interactive targets survived filtering — "
            "interactiveTargetCount and downstream Fitts's Law data may be silently "
            "reporting a clean result for a detection gap rather than a genuinely empty screen"
        )
    metrics_status = "degraded" if warnings else "ok"
    warning = "; ".join(warnings) if warnings else None

    elements_meta = {
        "detectedElementCount": n,
        "contourBasedCount": contour_count,
        "ocrBasedCount": ocr_element_count,
        "filteredElementCount": filtered_n,
        "interactiveTargetCount": filtered_n,
        "holeContourExcludedCount": contour_debug["holeContourExcludedCount"],
        "backgroundContourExcludedCount": contour_debug["backgroundContourExcludedCount"],
        "duplicateNestedContourExcludedCount": contour_debug["duplicateNestedContourExcludedCount"],
        "darkBackgroundDetected": contour_debug["darkBackgroundDetected"],
        "recoveredFromDarkBackgroundCount": contour_debug["recoveredFromDarkBackgroundCount"],
        "textGlyphContourExcludedCount": len(glyph_excluded_debug),
        "keyboardDetected": keyboard_result["status"] == "detected",
        "keyboardDetectionConfidence": keyboard_result["confidence"],
        "keyboardRegionBbox": keyboard_bbox,
        "keyboardExcludedTargetCount": keyboard_excluded_count,
        "systemUiRegion": (
            {"type": "keyboard", "bbox": keyboard_bbox, "confidence": keyboard_result["confidence"]}
            if keyboard_bbox is not None
            else None
        ),
        "systemUiExcludedCount": system_ui_excluded_count,
        "metricsStatus": metrics_status,
        "warning": warning,
        "isProxyMetric": True,
        "source": (
            "interactiveTargetCount (== filteredElementCount) is contour-sourced elements "
            "only, excluding OCR text boxes, repeating-grid system chrome (e.g. an on-screen "
            "keyboard), contours substantially coincident with OCR text ink disclosed via "
            "textGlyphContourExcludedCount, and contours inside a confidently detected "
            "system-keyboard region disclosed via keyboardExcludedTargetCount/systemUiRegion — "
            "keyboard detection combines row/width/position geometry with QWERTY-sequence, "
            "keyword, and single-character OCR signals, never geometry alone; an uncertain "
            "(`degraded`) detection excludes nothing and is disclosed via "
            "metricsStatus/warning instead); contour detection uses RETR_CCOMP so controls "
            "nested inside a full-bleed background's card are still found (RETR_EXTERNAL "
            "misses them entirely); interior holes, the background itself, and near-duplicate "
            "nested edges are excluded and disclosed via holeContourExcludedCount/"
            "backgroundContourExcludedCount/duplicateNestedContourExcludedCount; "
            "interactiveTargets is the identical list shared with Fitts's Law (corrected-v8) "
            "so a fix to one can never silently fail to apply to the other. The repeating-grid "
            "detector's geometric thresholds (row/column count floors, size-uniformity and "
            "gap-ratio cutoffs) and the keyboard detector's signal weights were tuned against a "
            "small internal set of real screenshots, not a systematic or statistically powered "
            "validation study, and may not generalize to unseen layouts. Fix D.1: a hole whose "
            "immediate parent is a dark, full-bleed background contour is recovered as a real "
            "element candidate instead of being dropped as empty interior space, disclosed via "
            "darkBackgroundDetected/recoveredFromDarkBackgroundCount — light-theme contour "
            "detection (the background is never itself foreground under this threshold) is "
            "unaffected. If a dark background is detected with other visual content present but "
            "interactiveTargetCount is still 0, metricsStatus degrades to 'degraded' with a "
            "warning rather than silently presenting a detection gap as a clean, empty screen. "
            "hicksLawEstimateMs/hicksLawBConstantMs/smallTargetsBelow44px/"
            "repeatingGridExcludedCount were removed as of corrected-v8 (Tier 3 / Problematic "
            "per docs/metrics/reliability-tiers.md); the underlying repeating-grid filtering "
            "itself is retained since it still improves interactiveTargets/Fitts's Law quality."
        ),
    }
    return elements_meta, elements, interactive_targets


# ---------- Fix 4: Grouping (complete-linkage clustering) ----------
def analyze_groups_v2(elements: list[dict], img_shape: tuple[int, ...]) -> dict[str, Any]:
    if not elements:
        return {
            "estimatedGroupCount": 0,
            "isProxyMetric": True,
            "source": "Miller's Law (7+-2), Miller (1956); complete-linkage clustering (corrected-v1)",
        }

    h, w = img_shape[:2]
    img_diag = np.hypot(h, w)
    centroids = np.array([(e["x"] + e["w"] / 2, e["y"] + e["h"] / 2) for e in elements], dtype=float)
    n = len(centroids)
    threshold = img_diag * 0.08  # same constant as the legacy single-linkage threshold

    diff = centroids[:, None, :] - centroids[None, :, :]
    dist_matrix = np.hypot(diff[..., 0], diff[..., 1])

    # Complete-linkage agglomerative clustering: at each step, merge the two
    # clusters whose *maximum* pairwise distance is smallest, stopping once
    # that distance exceeds `threshold`. This bounds each cluster's diameter
    # — unlike single-linkage/union-find, which only requires one close pair
    # and so lets a long dense row of elements chain into a single cluster.
    clusters: list[list[int]] = [[i] for i in range(n)]
    while len(clusters) > 1:
        best_dist = None
        best_pair = None
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                d = float(dist_matrix[np.ix_(clusters[i], clusters[j])].max())
                if best_dist is None or d < best_dist:
                    best_dist, best_pair = d, (i, j)
        if best_dist is None or best_dist > threshold:
            break
        i, j = best_pair
        merged = clusters[i] + clusters[j]
        clusters = [c for k, c in enumerate(clusters) if k not in (i, j)]
        clusters.append(merged)

    return {
        "estimatedGroupCount": len(clusters),
        "isProxyMetric": True,
        "source": (
            "Miller's Law (7+-2), Miller (1956); complete-linkage clustering bounds each "
            "cluster's diameter to resist the chaining effect of single-linkage (corrected-v1)"
        ),
    }


# ---------- Fixes 5 & 7: Whitespace (brightness-gated) & Alignment (per-axis) ----------
def analyze_whitespace_alignment_v2(img: np.ndarray, elements: list[dict]) -> dict[str, Any]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    block = 20
    low_variance_light_blocks = 0
    total_blocks = 0

    for y in range(0, h - block, block):
        for x in range(0, w - block, block):
            cell = gray[y : y + block, x : x + block]
            total_blocks += 1
            # Corrected: a block counts as whitespace-like only if it is
            # BOTH flat (low variance) AND light (mean > 200/255) — a flat
            # saturated color (e.g. a solid brand-color background) is flat
            # but is not whitespace.
            if np.var(cell) < 100 and np.mean(cell) > 200:
                low_variance_light_blocks += 1

    whitespace_ratio = low_variance_light_blocks / total_blocks if total_blocks else 0

    alignment_variance = None
    aligned_ratio = None
    if len(elements) >= 2:
        xs = [e["x"] for e in elements]
        ys = [e["y"] for e in elements]
        x_align = np.std(xs) / w
        y_align = np.std(ys) / h
        alignment_variance = round(float((x_align + y_align) / 2), 4)

        # Corrected: credit any element that shares a left (x) or top (y)
        # edge with at least one other element, within an 8px tolerance —
        # so multiple independently-valid alignment axes (e.g. a
        # left-aligned column and a separately right-aligned column) can
        # both be recognized, instead of collapsing everything into one
        # global blended variance.
        tolerance = 8
        aligned_flags = [False] * len(elements)
        for i in range(len(elements)):
            for j in range(len(elements)):
                if i == j:
                    continue
                if abs(xs[i] - xs[j]) <= tolerance or abs(ys[i] - ys[j]) <= tolerance:
                    aligned_flags[i] = True
                    break
        aligned_ratio = round(sum(aligned_flags) / len(elements), 4)

    return {
        "whitespaceRatio": round(whitespace_ratio, 4),
        "alignmentVariance": alignment_variance,
        "alignedElementRatio": aligned_ratio,
        "source": (
            "Whitespace requires both low local variance and mean brightness > 200/255, so a "
            "flat saturated color no longer counts as whitespace; alignedElementRatio = share "
            "of elements whose left or top edge is within 8px of another element's, crediting "
            "multiple independent alignment axes (corrected-v1). The variance/brightness "
            "thresholds (100, 200/255) and the 8px alignment-edge tolerance were tuned against "
            "a small internal set of real screenshots, not a systematic or statistically "
            "powered validation study, and are not derived from the image being analyzed — "
            "they may under- or over-detect on layouts/themes unlike that set (e.g. dark-mode "
            "UIs, unusually large/small grid units)."
        ),
    }


# ---------- Fix 6: Fitts's Law (interactive targets only) ----------
def analyze_fitts_full_v2(elements: list[dict]) -> dict[str, Any]:
    # Fix 2d: a nearest-neighbor Index of Difficulty is a distance between
    # TWO targets -- with fewer than two interactive targets on screen there
    # is no pair to measure, so no ID is computed, ever. `elementsConsidered`
    # still reports how many interactive targets were actually considered
    # (0 or 1), not conflated with "an ID was computed for them".
    if len(elements) < 2:
        return {
            "averageIndexOfDifficulty": None,
            "elementsConsidered": len(elements),
            "status": "not_applicable",
            "reason": "at least two interactive targets are required for a nearest-neighbor Fitts estimate",
            "isProxyMetric": True,
            "source": (
                "Fitts's Law (ID = log2(2D/W)), Fitts (1954); interactive targets only "
                "(contour-sourced, excluding OCR text boxes and text-glyph contours) (corrected-v2)"
            ),
        }

    centroids = [(e["x"] + e["w"] / 2, e["y"] + e["h"] / 2) for e in elements]
    ids = []
    for i, (cx, cy) in enumerate(centroids):
        dists = [np.hypot(cx - ox, cy - oy) for j, (ox, oy) in enumerate(centroids) if j != i]
        nearest_d = min(dists)
        target_w = max(1, min(elements[i]["w"], elements[i]["h"]))
        if nearest_d <= 0:
            continue
        ids.append(np.log2((2 * nearest_d) / target_w))

    avg_id = round(float(np.mean(ids)), 2) if ids else None
    return {
        "averageIndexOfDifficulty": avg_id,
        "elementsConsidered": len(elements),
        "status": "computed",
        "isProxyMetric": True,
        "source": (
            "Fitts's Law (ID = log2(2D/W)), Fitts (1954); interactive targets only "
            "(contour-sourced, excluding OCR text boxes and text-glyph contours) (corrected-v2)"
        ),
    }


# ---------- Fix 8: Text density (MAD-based font diversity) ----------
#
# Fix 8b (post-audit follow-up): both `textDensityRatio` and
# `fontSizeDiversityProxy` are entirely downstream of Tesseract OCR output —
# a missed or misread word skews both directly — but nothing in the output
# previously disclosed how much OCR confidence the specific analyzed image
# actually produced, so this dependency was undocumented risk rather than a
# measured one. `averageOcrConfidence` (mean Tesseract confidence, 0-100,
# over the words actually counted) and `lowConfidenceWordsExcluded` (words
# dropped for confidence < 60, same threshold already used to build both
# metrics) make that dependency visible per-analysis rather than only in
# prose documentation, so a consumer (or a research correlation study) can
# gauge or filter by how much a given result should be trusted. Neither
# `textDensityRatio` nor `fontSizeDiversityProxy`'s computation changes.
def analyze_text_density_v2(img: np.ndarray, ocr_data: dict) -> dict[str, Any]:
    h, w = img.shape[:2]
    total_area = h * w
    text_area = 0
    heights: list[int] = []
    confidences: list[int] = []
    low_confidence_excluded = 0
    n_boxes = len(ocr_data["text"])
    for i in range(n_boxes):
        if not ocr_data["text"][i].strip():
            continue
        conf = int(ocr_data["conf"][i])
        if conf < 60:
            low_confidence_excluded += 1
            continue
        text_area += ocr_data["width"][i] * ocr_data["height"][i]
        heights.append(ocr_data["height"][i])
        confidences.append(conf)

    density = text_area / total_area if total_area else 0

    if len(heights) > 1:
        arr = np.array(heights, dtype=float)
        median = np.median(arr)
        font_diversity = round(float(np.median(np.abs(arr - median))), 2)
    else:
        font_diversity = 0.0

    average_ocr_confidence = round(float(np.mean(confidences)), 1) if confidences else None

    return {
        "textDensityRatio": round(density, 4),
        "fontSizeDiversityProxy": font_diversity,
        "wordsDetected": len(heights),
        "averageOcrConfidence": average_ocr_confidence,
        "lowConfidenceWordsExcluded": low_confidence_excluded,
        "source": (
            "Text density = OCR bounding-box area / image area; fontSizeDiversityProxy = "
            "median absolute deviation of OCR box heights, more outlier-resistant than "
            "std-dev (corrected-v1). Both metrics are entirely dependent on Tesseract OCR "
            "output quality and this dependency is not independently error-measured; "
            "averageOcrConfidence (mean Tesseract confidence over counted words) and "
            "lowConfidenceWordsExcluded (words dropped below confidence 60, excluded "
            "outright, never down-weighted) disclose that dependency per-analysis "
            "(corrected-v2)."
        ),
    }


# ---------- Fix 9: Hue diversity (new, additive signal) ----------
def analyze_hue_diversity(img: np.ndarray) -> dict[str, Any]:
    """Supplementary signal placed in `additionalSignals` alongside the
    unchanged `colorfulnessScore`. Colorfulness (Hasler & Suesstrunk) is a
    correct, un-modified formula, but it measures saturated-area coverage,
    not how many distinct hues are present — the audit found a single flat
    saturated-color screen outscoring a visibly multi-hue screen on
    colorfulness alone. This is the complementary "how many different hues"
    signal, not a replacement."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0].astype(np.float64)
    sat = hsv[:, :, 1].astype(np.float64)

    # Near-gray/white/black pixels have an unstable, near-meaningless hue
    # angle, so only sufficiently-saturated pixels are considered.
    mask = sat > 40
    if not np.any(mask):
        return {
            "hueDiversityIndex": 0.0,
            "saturatedPixelRatio": 0.0,
            "source": (
                "Shannon entropy of the hue histogram over sufficiently-saturated pixels, "
                "normalized to 0-1; additive signal alongside colorfulnessScore, does not "
                "replace it (corrected-v1)"
            ),
        }

    hist, _ = np.histogram(hue[mask], bins=36, range=(0, 180))
    probs = hist / hist.sum()
    probs = probs[probs > 0]
    entropy = float(-np.sum(probs * np.log2(probs)))
    max_entropy = float(np.log2(36))

    return {
        "hueDiversityIndex": round(entropy / max_entropy, 4),
        "saturatedPixelRatio": round(float(np.mean(mask)), 4),
        "source": (
            "Shannon entropy of the hue histogram over sufficiently-saturated pixels, "
            "normalized to 0-1; additive signal alongside colorfulnessScore, does not "
            "replace it (corrected-v1)"
        ),
    }


# ---------- Fix 15: composite score after Tier 3 removal ----------
#
# `backend/reference/legacy_metric_engine.py`'s `WEIGHTS`/`normalize_metrics`/
# `weighted_score` are left completely untouched (immutable, per CLAUDE.md)
# and simply become unused, exactly like its other already-superseded
# functions (`analyze_contrast`, `analyze_elements`, ...). `clutter`
# (edgeDensity), `elementSize` (smallTargetsBelow44px), and `groupCount`
# (`normalize_group_count` — itself flagged as an internal inconsistency in
# docs/metrics/reliability-tiers.md) are all Tier 3 and are dropped from the
# composite score entirely, leaving only `contrast` and `textDensity`
# (both Tier 1/2). Their relative weight is preserved by proportionally
# rescaling the legacy weights of just those two components back up to 1.0,
# per context:
#   general:  contrast 0.25/(0.25+0.20) = 0.5556, textDensity 0.4444
#   expert:   contrast 0.25/(0.25+0.10) = 0.7143, textDensity 0.2857
# `normalize()` (the generic 0-100 linear rescale helper) is reused
# unchanged from the legacy module — it is a correct, general-purpose
# utility, not itself a Tier 3 item.
WEIGHTS_V2 = {
    "general": {"contrast": 0.5556, "textDensity": 0.4444},
    "expert": {"contrast": 0.7143, "textDensity": 0.2857},
}


def normalize_metrics_v2(raw: dict[str, Any]) -> dict[str, float | None]:
    return {
        "contrast": normalize(raw["contrast"]["averageContrastRatio"] or 1, 1, 7),
        "textDensity": normalize(raw["textDensity"]["textDensityRatio"], 0.02, 0.30, invert=True),
    }


def weighted_score_v2(normalized: dict[str, float | None], context: str) -> float:
    weights = WEIGHTS_V2.get(context, WEIGHTS_V2["general"])
    total = sum((normalized.get(k) or 0) * w for k, w in weights.items())
    return round(total, 1)
