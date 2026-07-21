"""Tests for the corrected metric implementations in `app.metrics.corrected`.

Each test targets one of the nine audit findings the module fixes (see its
module docstring). Synthetic images/OCR data only — no real screenshots, no
Tesseract binary, no network, per CLAUDE.md Testing Rules.
"""

import cv2
import numpy as np
import pytest

from app.metrics.corrected import (
    _bbox_iou,
    _classify_interactive_targets,
    _dedupe_nested_contours,
    _detect_keyboard_region,
    _detect_repeating_grid_indices,
    _is_background_contour,
    analyze_contrast_v2,
    analyze_elements_v2,
    analyze_fitts_full_v2,
    analyze_groups_v2,
    analyze_hue_diversity,
    analyze_text_density_v2,
    analyze_whitespace_alignment_v2,
)


def _empty_ocr() -> dict:
    return {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}


def _solid_image(height: int, width: int, bgr: tuple[int, int, int]) -> np.ndarray:
    return np.full((height, width, 3), bgr, dtype=np.uint8)


# ---------- Fix 1: contrast (Otsu ink/paper separation) ----------


def test_black_text_on_white_reports_near_maximal_contrast() -> None:
    """Ground truth from the audit: black-on-white text was reported as
    ~1.2:1 by the old mean-of-box method; the true ratio is 21:1."""
    img = _solid_image(60, 200, (255, 255, 255))
    img[20:40, 20:180] = (0, 0, 0)  # a black "glyph block" inside the box
    ocr_data = {
        "text": ["Sign"],
        "conf": [96],
        "left": [10],
        "top": [10],
        "width": [180],
        "height": [40],
    }
    result = analyze_contrast_v2(img, ocr_data)
    assert result["regionsAnalyzed"] == 1
    assert result["averageContrastRatio"] >= 15.0
    assert result["regionsBelowAAThreshold"] == 0


def test_flat_region_is_skipped_not_fabricated() -> None:
    """An OCR box over a perfectly uniform region has no real ink/paper
    split — Otsu is meaningless there, so it must be skipped, not guessed."""
    img = _solid_image(60, 200, (200, 200, 200))
    ocr_data = {
        "text": ["ghost"],
        "conf": [61],
        "left": [10],
        "top": [10],
        "width": [50],
        "height": [20],
    }
    result = analyze_contrast_v2(img, ocr_data)
    assert result["regionsAnalyzed"] == 0
    assert result["regionsSkipped"] == 1
    assert result["averageContrastRatio"] is None


def test_low_confidence_regions_are_ignored() -> None:
    img = _solid_image(60, 200, (255, 255, 255))
    ocr_data = {
        "text": ["noise"],
        "conf": [10],
        "left": [10],
        "top": [10],
        "width": [50],
        "height": [20],
    }
    result = analyze_contrast_v2(img, ocr_data)
    assert result["regionsAnalyzed"] == 0
    assert result["regionsSkipped"] == 0


# ---------- Fixes 2 & 3: elements (contour-only small targets, grid exclusion) ----------


def test_ocr_text_boxes_never_count_as_small_targets() -> None:
    """A blank (no-contour) image with one small confident OCR word: the
    word box is <44px on both axes, but must not be flagged small — it was
    never a tap-target candidate."""
    img = _solid_image(200, 200, (255, 255, 255))
    ocr_data = {
        "text": ["ok"],
        "conf": [95],
        "left": [10],
        "top": [10],
        "width": [30],
        "height": [15],
    }
    elements_meta, elements, control_like = analyze_elements_v2(img, ocr_data)
    assert elements_meta["ocrBasedCount"] == 1
    assert elements_meta["smallTargetsBelow44px"] == 0
    assert control_like == []


def test_small_contour_still_counts_as_small_target() -> None:
    img = _solid_image(200, 200, (255, 255, 255))
    img[50:75, 50:75] = (0, 0, 0)  # a 25x25 dark square -> one small contour
    elements_meta, elements, control_like = analyze_elements_v2(img, _empty_ocr())
    assert elements_meta["contourBasedCount"] == 1
    assert elements_meta["smallTargetsBelow44px"] == 1
    assert len(control_like) == 1


def test_single_row_band_is_never_flagged_as_a_grid() -> None:
    """A single dense, uniform row (this exact shape used to be flagged as
    a keyboard in the original Fix 3) is indistinguishable from ordinary
    single-row UI chrome (bottom nav, toolbar, chip row) and must never be
    excluded, no matter how uniform or tightly packed."""
    elements = [{"x": i * 40, "y": 500, "w": 35, "h": 35, "source": "contour"} for i in range(10)]
    excluded = _detect_repeating_grid_indices(elements)
    assert excluded == set()


def test_small_element_set_is_never_flagged_as_a_grid() -> None:
    elements = [{"x": i * 40, "y": 500, "w": 35, "h": 35, "source": "contour"} for i in range(3)]
    assert _detect_repeating_grid_indices(elements) == set()


def test_multi_row_dense_grid_is_excluded_from_filtered_count() -> None:
    """A genuine keyboard-like structure: 3 stacked rows of 10 tightly
    packed, uniformly sized contour boxes, plus one isolated real square
    elsewhere. Hick's Law must be computed off the filtered (grid-excluded)
    count, not the raw one."""
    img = _solid_image(700, 700, (255, 255, 255))
    for row in range(3):
        for col in range(10):
            x, y = 20 + col * 35, 500 + row * 35
            img[y : y + 30, x : x + 30] = (0, 0, 0)
    # One clearly separate, larger, isolated square elsewhere -> real content.
    img[50:110, 50:110] = (0, 0, 0)

    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())
    assert elements_meta["repeatingGridExcludedCount"] == 30
    assert elements_meta["filteredElementCount"] == len(eligible) == 1
    # Hick's Law must be computed off the filtered count, not the raw one.
    expected_ms = round(150 * np.log2(elements_meta["filteredElementCount"] + 1), 1)
    assert elements_meta["hicksLawEstimateMs"] == expected_ms


def test_hicks_law_b_constant_is_exposed_and_disclosed_as_unsourced() -> None:
    """`hicksLawBConstantMs` must be queryable as its own field (not only
    embedded in prose inside `source`), and `source` must disclose that it
    is an assumed constant, not derived from Hick (1952)."""
    img = _solid_image(200, 200, (255, 255, 255))
    elements_meta, _elements, _eligible = analyze_elements_v2(img, _empty_ocr())
    assert elements_meta["hicksLawBConstantMs"] == 150
    assert "not a value derived from Hick" in elements_meta["source"]


# ---------- Fix 3b: revised grid detection (multi-row/column, normalized density) ----------


def test_bottom_navigation_bar_is_not_treated_as_a_grid() -> None:
    """10 evenly-spaced, uniformly-sized icons in one row across a wide
    screen -- a normal bottom nav bar -- must survive into both Fitts's Law
    and Hick's Law untouched."""
    img = _solid_image(650, 800, (255, 255, 255))
    for i in range(10):
        x = i * 80
        img[600:640, x : x + 40] = (0, 0, 0)

    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())
    assert elements_meta["repeatingGridExcludedCount"] == 0
    assert elements_meta["filteredElementCount"] == len(eligible) == 10
    fitts = analyze_fitts_full_v2(eligible)
    assert fitts["elementsConsidered"] == 10


def test_filter_chip_row_is_not_treated_as_a_grid() -> None:
    """A single row of tightly-packed filter chips must not be misread as a
    keyboard-like grid just because it is dense."""
    elements = [{"x": i * 65, "y": 300, "w": 60, "h": 28, "source": "contour"} for i in range(9)]
    assert _detect_repeating_grid_indices(elements) == set()


def test_real_keyboard_grid_excludes_keys_from_both_fitts_and_hicks() -> None:
    """A genuine 3-row x 10-column, tightly packed keyboard, plus 3 real,
    separate controls elsewhere. The keyboard keys must be excluded from
    *both* Hick's Law and Fitts's Law, and both metrics must agree on
    `elementsConsidered == 3` -- the same shared eligible-element universe."""
    img = _solid_image(700, 400, (255, 255, 255))
    for row in range(3):
        for col in range(10):
            x, y = col * 35, 500 + row * 35
            img[y : y + 30, x : x + 30] = (0, 0, 0)
    real_controls = [(50, 50, 60, 60), (50, 150, 60, 60), (50, 250, 60, 60)]
    for x, y, w, h in real_controls:
        img[y : y + h, x : x + w] = (0, 0, 0)

    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())
    assert elements_meta["repeatingGridExcludedCount"] == 30
    assert elements_meta["filteredElementCount"] == 3

    fitts = analyze_fitts_full_v2(eligible)
    assert fitts["elementsConsidered"] == 3
    assert elements_meta["filteredElementCount"] == fitts["elementsConsidered"]


def test_sparse_multi_row_icon_grid_is_not_treated_as_a_keyboard() -> None:
    """A 3x6 grid of uniformly sized icons that is regular but *sparse*
    (large gaps relative to icon size, e.g. a home-screen icon grid) must
    not be classified as keyboard-like system chrome just because it forms
    multiple rows and columns."""
    elements = []
    for row in range(3):
        for col in range(6):
            elements.append(
                {"x": col * 160, "y": 100 + row * 160, "w": 60, "h": 60, "source": "contour"}
            )
    assert _detect_repeating_grid_indices(elements) == set()


def test_dense_keyboard_grid_is_correctly_excluded() -> None:
    """A tightly packed 3x10 grid (small, consistent horizontal/vertical
    gaps relative to element size) is exactly the shape a real on-screen
    keyboard has, and must be excluded in full."""
    elements = []
    for row in range(3):
        for col in range(10):
            elements.append(
                {"x": col * 35, "y": 500 + row * 35, "w": 30, "h": 30, "source": "contour"}
            )
    excluded = _detect_repeating_grid_indices(elements)
    assert len(excluded) == 30


def test_fitts_and_hicks_share_the_identical_eligible_element_set() -> None:
    """End to end: both metrics must be computed over the same
    eligible-element universe, so a mix of contour controls, OCR text
    boxes, and a keyboard-like grid band produces identical
    `elementsConsidered` / `filteredElementCount` values."""
    img = _solid_image(700, 400, (255, 255, 255))
    for row in range(3):
        for col in range(10):
            x, y = col * 35, 500 + row * 35
            img[y : y + 30, x : x + 30] = (0, 0, 0)
    real_controls = [(50, 50, 60, 60), (50, 150, 60, 60)]
    for x, y, w, h in real_controls:
        img[y : y + h, x : x + w] = (0, 0, 0)

    ocr_data = {
        "text": ["paragraph", "of", "body", "text"],
        "conf": [90, 90, 90, 90],
        "left": [50, 150, 250, 350],
        "top": [250, 250, 250, 250],
        "width": [80, 40, 60, 60],
        "height": [22, 22, 22, 22],
    }
    elements_meta, elements, eligible = analyze_elements_v2(img, ocr_data)
    fitts = analyze_fitts_full_v2(eligible)

    assert elements_meta["ocrBasedCount"] == 4  # OCR boxes exist, but...
    assert all(e["source"] == "contour" for e in eligible)  # ...never in the eligible list
    assert elements_meta["filteredElementCount"] == len(eligible) == fitts["elementsConsidered"] == 2


# ---------- Fix 4: group count (complete-linkage clustering) ----------


def test_long_dense_chain_does_not_collapse_into_one_group() -> None:
    """The classic single-linkage chaining failure: a long line of points,
    each close to its neighbor, spans far more than the cluster-diameter
    threshold end-to-end. Complete-linkage must not merge it into one blob."""
    elements = [{"x": i * 15, "y": 0, "w": 10, "h": 10, "source": "contour"} for i in range(30)]
    result = analyze_groups_v2(elements, (400, 400))
    assert result["estimatedGroupCount"] > 1


def test_tight_cluster_of_points_forms_one_group() -> None:
    elements = [{"x": i * 5, "y": 0, "w": 10, "h": 10, "source": "contour"} for i in range(5)]
    result = analyze_groups_v2(elements, (2000, 2000))
    assert result["estimatedGroupCount"] == 1


def test_empty_elements_produce_zero_groups() -> None:
    assert analyze_groups_v2([], (100, 100))["estimatedGroupCount"] == 0


# ---------- Fixes 5 & 7: whitespace (brightness-gated) & alignment (per-axis) ----------


def test_flat_saturated_color_is_not_counted_as_whitespace() -> None:
    """Ground truth from the audit: a solid saturated-green screen scored a
    high whitespace ratio under the variance-only check."""
    img = _solid_image(100, 100, (0, 255, 0))  # pure green (BGR), grayscale ~150
    result = analyze_whitespace_alignment_v2(img, [])
    assert result["whitespaceRatio"] == 0.0


def test_flat_white_region_is_counted_as_whitespace() -> None:
    img = _solid_image(100, 100, (255, 255, 255))
    result = analyze_whitespace_alignment_v2(img, [])
    assert result["whitespaceRatio"] == 1.0


def test_aligned_element_ratio_credits_multiple_axes() -> None:
    """Two elements share a left edge (column A), two share a top edge (row
    B) -- none share both axes together, so a single blended variance would
    undercredit this, but every element does share *some* axis."""
    elements = [
        {"x": 10, "y": 10, "w": 20, "h": 20, "source": "contour"},
        {"x": 10, "y": 300, "w": 20, "h": 20, "source": "contour"},
        {"x": 500, "y": 10, "w": 20, "h": 20, "source": "contour"},
        {"x": 5, "y": 10, "w": 20, "h": 20, "source": "contour"},
    ]
    img = _solid_image(400, 600, (255, 255, 255))
    result = analyze_whitespace_alignment_v2(img, elements)
    assert result["alignedElementRatio"] == 1.0


def test_alignment_fields_absent_with_fewer_than_two_elements() -> None:
    img = _solid_image(100, 100, (255, 255, 255))
    result = analyze_whitespace_alignment_v2(img, [{"x": 0, "y": 0, "w": 5, "h": 5, "source": "contour"}])
    assert result["alignmentVariance"] is None
    assert result["alignedElementRatio"] is None


# ---------- Fix 6: Fitts's Law over control-like elements only ----------


def test_fitts_returns_none_below_two_elements() -> None:
    """A single interactive target has no partner to measure a
    nearest-neighbor distance against; `elementsConsidered` still reports
    how many targets were considered (1), not conflated with 'an ID was
    computed' (it wasn't -- `status` says so explicitly)."""
    result = analyze_fitts_full_v2([{"x": 0, "y": 0, "w": 10, "h": 10, "source": "contour"}])
    assert result["averageIndexOfDifficulty"] is None
    assert result["elementsConsidered"] == 1
    assert result["status"] == "not_applicable"
    assert "reason" in result


def test_fitts_zero_elements_is_not_applicable() -> None:
    result = analyze_fitts_full_v2([])
    assert result["averageIndexOfDifficulty"] is None
    assert result["elementsConsidered"] == 0
    assert result["status"] == "not_applicable"


def test_fitts_computes_over_provided_control_like_list() -> None:
    elements = [
        {"x": 0, "y": 0, "w": 20, "h": 20, "source": "contour"},
        {"x": 100, "y": 0, "w": 20, "h": 20, "source": "contour"},
        {"x": 200, "y": 0, "w": 20, "h": 20, "source": "contour"},
    ]
    result = analyze_fitts_full_v2(elements)
    assert result["elementsConsidered"] == 3
    assert result["averageIndexOfDifficulty"] is not None


# ---------- Fix 8: text density (MAD-based font diversity) ----------


def test_font_diversity_is_outlier_resistant() -> None:
    """One 100px outlier among five 10px lines: std-dev is dragged far up by
    it, MAD stays close to the typical spread."""
    ocr_data = {
        "text": ["a", "b", "c", "d", "e"],
        "conf": [90, 90, 90, 90, 90],
        "left": [0, 0, 0, 0, 0],
        "top": [0, 20, 40, 60, 80],
        "width": [10, 10, 10, 10, 10],
        "height": [10, 10, 10, 10, 100],
    }
    img = _solid_image(200, 200, (255, 255, 255))
    result = analyze_text_density_v2(img, ocr_data)
    naive_std = round(float(np.std([10, 10, 10, 10, 100])), 2)
    assert result["fontSizeDiversityProxy"] < naive_std
    assert result["wordsDetected"] == 5


def test_text_density_ratio_matches_area_fraction() -> None:
    ocr_data = {
        "text": ["word"],
        "conf": [90],
        "left": [0],
        "top": [0],
        "width": [10],
        "height": [10],
    }
    img = _solid_image(100, 100, (255, 255, 255))  # 10,000 px total
    result = analyze_text_density_v2(img, ocr_data)
    assert result["textDensityRatio"] == pytest.approx(0.01, abs=1e-4)


def test_average_ocr_confidence_reflects_only_counted_words() -> None:
    """`averageOcrConfidence` must average confidence over the words that
    actually fed the metric (conf >= 60), and `lowConfidenceWordsExcluded`
    must count the ones that didn't -- not silently blend both together."""
    ocr_data = {
        "text": ["good", "also-good", "junk"],
        "conf": [90, 70, 40],
        "left": [0, 20, 40],
        "top": [0, 0, 0],
        "width": [10, 10, 10],
        "height": [10, 10, 10],
    }
    img = _solid_image(200, 200, (255, 255, 255))
    result = analyze_text_density_v2(img, ocr_data)
    assert result["wordsDetected"] == 2
    assert result["averageOcrConfidence"] == pytest.approx(80.0)
    assert result["lowConfidenceWordsExcluded"] == 1


def test_average_ocr_confidence_is_none_when_no_words_counted() -> None:
    ocr_data = {"text": ["junk"], "conf": [10], "left": [0], "top": [0], "width": [10], "height": [10]}
    img = _solid_image(100, 100, (255, 255, 255))
    result = analyze_text_density_v2(img, ocr_data)
    assert result["wordsDetected"] == 0
    assert result["averageOcrConfidence"] is None
    assert result["lowConfidenceWordsExcluded"] == 1


# ---------- Fix 9: hue diversity (new, additive signal) ----------


def test_flat_saturated_color_has_low_hue_diversity() -> None:
    img = _solid_image(100, 100, (0, 255, 0))  # pure green, one hue only
    result = analyze_hue_diversity(img)
    assert result["hueDiversityIndex"] < 0.15


def test_multi_hue_image_has_higher_hue_diversity_than_flat_color() -> None:
    img = _solid_image(120, 120, (0, 255, 0))
    img[0:40, :] = (0, 0, 255)  # red band (BGR)
    img[40:80, :] = (255, 0, 0)  # blue band
    img[80:120, :] = (0, 255, 255)  # yellow band
    multi = analyze_hue_diversity(img)
    flat = analyze_hue_diversity(_solid_image(120, 120, (0, 255, 0)))
    assert multi["hueDiversityIndex"] > flat["hueDiversityIndex"]


def test_hue_diversity_handles_fully_desaturated_image() -> None:
    img = _solid_image(50, 50, (128, 128, 128))  # gray, no saturated pixels
    result = analyze_hue_diversity(img)
    assert result["hueDiversityIndex"] == 0.0
    assert result["saturatedPixelRatio"] == 0.0


# ---------- Fix 2c: full-bleed background blind spot (RETR_CCOMP + dedup) ----------
#
# The original bug: a real screenshot with a solid-color full-bleed
# background behind a white card (a modal) reported contourBasedCount == 0,
# smallTargetsBelow44px == 0, and no Fitts's/Hick's Law data, because
# `cv2.RETR_EXTERNAL` never returns a foreground island nested inside a hole
# of a bigger shape (the background thresholds as one image-spanning blob;
# everything on the card is a hole-nested island). Each test below targets
# one theme/layout scenario named in the fix request; all use only
# synthetic, hard-edged fills (no real screenshots), per CLAUDE.md.


def test_light_theme_button_on_white_background_is_unaffected() -> None:
    """Baseline/no-regression: a plain white-background screen with a
    directly-placed dark button never had a background 'hole' problem
    under the old RETR_EXTERNAL code, and must behave identically now."""
    img = _solid_image(300, 300, (255, 255, 255))
    img[50:100, 50:250] = (40, 40, 40)
    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())
    assert elements_meta["contourBasedCount"] == 1
    assert elements_meta["backgroundContourExcludedCount"] == 0
    assert elements_meta["duplicateNestedContourExcludedCount"] == 0
    assert len(eligible) == 1


def test_solid_color_background_reveals_nested_button() -> None:
    """Direct reproduction of the real-world bug: a solid, moderately dark
    full-bleed color behind a white card, with a dark button on the card."""
    img = _solid_image(400, 300, (80, 160, 90))  # solid full-bleed color, grayscale well below 200
    img[50:350, 20:280] = (255, 255, 255)  # white card
    img[280:320, 60:240] = (60, 60, 60)  # dark button on the card
    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())

    assert elements_meta["backgroundContourExcludedCount"] >= 1
    contour_boxes = [(e["x"], e["y"], e["w"], e["h"]) for e in elements if e["source"] == "contour"]
    assert (60, 280, 180, 40) in contour_boxes
    assert len(eligible) >= 1


def test_dark_theme_full_bleed_background_reveals_nested_button() -> None:
    """Mirror image (dark theme): a near-black full-bleed background with a
    lighter card and a dark button on it -- proves the fix isn't
    polarity-specific to light-colored modals."""
    img = _solid_image(400, 300, (15, 15, 15))  # near-black full-bleed background
    img[50:350, 20:280] = (230, 230, 230)  # light card on the dark page
    img[280:320, 60:240] = (50, 50, 50)  # dark button/label on the light card
    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())

    assert elements_meta["backgroundContourExcludedCount"] >= 1
    contour_boxes = [(e["x"], e["y"], e["w"], e["h"]) for e in elements if e["source"] == "contour"]
    assert (60, 280, 180, 40) in contour_boxes


def test_card_based_screen_keeps_multiple_cards_distinct() -> None:
    """A light-page screen with two separate cards, each containing its own
    button -- both buttons must be found as two distinct elements, with no
    cross-card merging or duplication."""
    img = _solid_image(500, 300, (255, 255, 255))
    img[30:200, 20:280] = (245, 245, 245)  # card 1
    img[150:180, 40:260] = (50, 50, 50)  # card 1's button
    img[250:420, 20:280] = (245, 245, 245)  # card 2
    img[390:420, 40:260] = (50, 50, 50)  # card 2's button
    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())

    contour_boxes = {(e["x"], e["y"], e["w"], e["h"]) for e in elements if e["source"] == "contour"}
    assert (40, 150, 220, 30) in contour_boxes
    assert (40, 390, 220, 30) in contour_boxes
    assert len(contour_boxes) == 2
    assert elements_meta["duplicateNestedContourExcludedCount"] == 0


def test_photo_background_with_dark_overlay_button_is_detected() -> None:
    """A bright, photo-like hero-image background (smooth, spatially
    correlated texture, tonal range kept above the 200 threshold, like a
    sky/beach photo) with a dark CTA button placed on top -- a common
    real-world 'photo header + dark button' pattern."""
    h, w = 400, 300
    rng = np.random.default_rng(5)
    noise = rng.normal(230, 12, (h, w)).clip(205, 255).astype(np.uint8)
    photo = cv2.GaussianBlur(noise, (25, 25), 0)
    img = cv2.merge([photo, photo, photo])
    img[280:320, 60:240] = (30, 30, 30)

    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())
    contour_boxes = [(e["x"], e["y"], e["w"], e["h"]) for e in elements if e["source"] == "contour"]
    assert (60, 280, 180, 40) in contour_boxes


def test_near_duplicate_nested_contour_bbox_is_dropped() -> None:
    """Direct unit test of the dedup logic: a child contour whose bbox
    nearly coincides with its parent's (the same physical edge detected
    twice via nested threshold crossings) must be dropped in favor of the
    larger parent, not double-counted."""
    parent = {"x": 10, "y": 10, "w": 200, "h": 100, "source": "contour", "area": 20000, "bbox": (10, 10, 200, 100)}
    near_duplicate_child = {"x": 12, "y": 11, "w": 196, "h": 98, "source": "contour", "area": 19208, "bbox": (12, 11, 196, 98)}
    result = _dedupe_nested_contours([parent, near_duplicate_child])
    assert len(result) == 1
    assert result[0]["bbox"] == (10, 10, 200, 100)


def test_distinct_small_nested_feature_is_kept() -> None:
    """Direct unit test: a child contour meaningfully smaller than its
    parent (e.g. an icon inside a button) is a distinct visual feature, not
    a duplicate edge, and must survive dedup alongside its parent."""
    parent = {"x": 10, "y": 10, "w": 200, "h": 100, "source": "contour", "area": 20000, "bbox": (10, 10, 200, 100)}
    small_icon = {"x": 20, "y": 30, "w": 24, "h": 24, "source": "contour", "area": 576, "bbox": (20, 30, 24, 24)}
    result = _dedupe_nested_contours([parent, small_icon])
    assert len(result) == 2
    bboxes = {c["bbox"] for c in result}
    assert (10, 10, 200, 100) in bboxes
    assert (20, 30, 24, 24) in bboxes


def test_is_background_contour_flags_full_bleed_but_not_ordinary_content() -> None:
    """Direct unit test of the background classifier: a bbox spanning the
    whole image, or one touching all four borders, is background; a large
    but not full-bleed content block (e.g. a hero photo touching only the
    top edge) is not."""
    img_shape = (400, 300, 3)
    assert _is_background_contour((0, 0, 300, 400), img_shape) is True  # exact full image
    assert _is_background_contour((0, 0, 300, 250), img_shape) is True  # >= 55% area, touches all edges? (top/left/right only, but area alone qualifies)
    assert _is_background_contour((0, 0, 300, 100), img_shape) is False  # touches top/left/right only, modest area -- e.g. a header banner
    assert _is_background_contour((50, 50, 100, 60), img_shape) is False  # ordinary interior content block


# ---------- Fix D.1 (independent-audit follow-up): dark full-bleed background
# swallows real light-colored controls ----------
#
# The Fix 2c test suite above ("dark theme full-bleed background") always
# ends with a DARK element as the final visible target (a dark button on a
# light card on a dark page) -- CCOMP's hole-inside-a-hole re-promotion
# already finds that case via the pre-existing single-polarity threshold,
# with no gap. The bug this section targets is structurally different: a
# LIGHT-colored control sitting DIRECTLY on a dark background, with no
# intermediate light card/layer for CCOMP to re-promote it out of. That is
# exactly one level of nesting (background -> hole), and the old code
# dropped every hole unconditionally on the assumption that a hole is
# always empty interior space.


def test_dark_background_light_button_directly_on_it_is_recovered() -> None:
    """Direct reproduction of the reported bug: a light button placed
    directly on a dark full-bleed background (no card in between) must be
    found, not silently dropped as an empty 'hole'."""
    img = _solid_image(800, 400, (30, 28, 32))  # dark full-bleed background
    img[500:560, 60:340] = (235, 235, 240)  # light button directly on the dark bg
    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())

    assert elements_meta["darkBackgroundDetected"] is True
    assert elements_meta["recoveredFromDarkBackgroundCount"] == 1
    assert elements_meta["contourBasedCount"] == 1
    assert elements_meta["interactiveTargetCount"] == 1
    contour_boxes = [(e["x"], e["y"], e["w"], e["h"]) for e in elements if e["source"] == "contour"]
    # A recovered hole's boundingRect traces OpenCV's inner hole-contour
    # boundary, which is consistently ~1px larger on each side than a
    # top-level/external contour of the same fill region -- immaterial for
    # element detection, but the exact reason this isn't (60, 500, 280, 60).
    assert (59, 499, 282, 62) in contour_boxes
    assert len(eligible) == 1
    assert elements_meta["hicksLawEstimateMs"] > 0
    assert elements_meta["metricsStatus"] == "ok"


def test_dark_background_light_checkbox_directly_on_it_is_recovered() -> None:
    """Same bug, a smaller (checkbox-sized) light control."""
    img = _solid_image(800, 400, (30, 28, 32))
    img[650:690, 60:100] = (235, 235, 240)  # ~40x40 checkbox, directly on the dark bg
    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())

    assert elements_meta["darkBackgroundDetected"] is True
    assert elements_meta["recoveredFromDarkBackgroundCount"] == 1
    assert elements_meta["interactiveTargetCount"] == 1
    contour_boxes = [(e["x"], e["y"], e["w"], e["h"]) for e in elements if e["source"] == "contour"]
    assert (59, 649, 42, 42) in contour_boxes  # see the button test above for the +-1px hole-contour note
    assert len(eligible) == 1


def test_dark_background_two_distinct_light_controls_both_recovered() -> None:
    """Two separate light controls directly on a dark background -- both
    must be recovered as two distinct targets, with no cross-merging."""
    img = _solid_image(800, 400, (30, 28, 32))
    img[500:560, 60:340] = (235, 235, 240)  # light button
    img[650:690, 60:100] = (235, 235, 240)  # light checkbox, far from the button
    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())

    assert elements_meta["recoveredFromDarkBackgroundCount"] == 2
    assert elements_meta["contourBasedCount"] == 2
    assert elements_meta["interactiveTargetCount"] == 2
    contour_boxes = {(e["x"], e["y"], e["w"], e["h"]) for e in elements if e["source"] == "contour"}
    assert (59, 499, 282, 62) in contour_boxes
    assert (59, 649, 42, 42) in contour_boxes
    assert len(eligible) == 2


def test_light_theme_dark_button_is_unaffected_by_dark_background_fix() -> None:
    """Regression: an ordinary light-theme screen must report
    darkBackgroundDetected=False and behave exactly as before -- the light
    background is never itself a foreground contour under this threshold,
    so the Fix D.1 exception path never engages."""
    img = _solid_image(300, 300, (255, 255, 255))
    img[50:100, 50:250] = (40, 40, 40)  # ordinary dark button on a light page
    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())

    assert elements_meta["darkBackgroundDetected"] is False
    assert elements_meta["recoveredFromDarkBackgroundCount"] == 0
    assert elements_meta["contourBasedCount"] == 1
    assert elements_meta["interactiveTargetCount"] == 1
    assert elements_meta["metricsStatus"] == "ok"


def test_dark_background_card_screen_card_itself_stays_excluded() -> None:
    """Card-based screen, dark full-bleed page behind a large light card
    with a dark button on it (mirrors the real Congratulations.png layout).
    The card itself (a large, non-control container) must not become a
    spurious 'interactive target' just because Fix D.1 now looks at holes
    of a dark background -- it is still filtered by the pre-existing
    30%-of-image area ceiling, exactly as an ordinary large hole/container
    always was. The dark button on the card is found via the pre-existing
    CCOMP re-promotion path, unrelated to Fix D.1."""
    img = _solid_image(800, 400, (40, 130, 70))  # dark-ish full-bleed green, grayscale well below 200
    img[150:650, 30:370] = (255, 255, 255)  # large white card: (370-30)*(650-150) / (800*400) = 53% of image area
    img[560:610, 60:340] = (40, 130, 70)  # dark-ish button on the card
    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())

    assert elements_meta["darkBackgroundDetected"] is True
    contour_boxes = [(e["x"], e["y"], e["w"], e["h"]) for e in elements if e["source"] == "contour"]
    # The card's own bbox (30, 150, 340, 500) must never appear as an element.
    assert (30, 150, 340, 500) not in contour_boxes
    # The button on the card must still be found.
    assert (60, 560, 280, 50) in contour_boxes
    assert elements_meta["recoveredFromDarkBackgroundCount"] == 0  # the card itself never survives the area ceiling


def test_dark_photo_like_background_with_light_button_is_recovered() -> None:
    """A dark, textured (photo-like, not perfectly flat) background with a
    light button placed on it -- proves the recovery isn't restricted to a
    perfectly uniform flat fill."""
    h, w = 400, 300
    rng = np.random.default_rng(7)
    noise = rng.normal(35, 8, (h, w)).clip(0, 90).astype(np.uint8)
    dark_photo = cv2.GaussianBlur(noise, (25, 25), 0)
    img = cv2.merge([dark_photo, dark_photo, dark_photo])
    img[280:320, 60:240] = (230, 230, 230)  # light button on the dark, textured backdrop

    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())
    assert elements_meta["darkBackgroundDetected"] is True
    contour_boxes = [(e["x"], e["y"], e["w"], e["h"]) for e in elements if e["source"] == "contour"]
    assert (59, 279, 182, 42) in contour_boxes  # see the flat dark-bg button test for the +-1px hole-contour note
    assert len(eligible) >= 1


def test_photo_background_with_dark_overlay_button_is_still_detected() -> None:
    """Regression: the existing bright-photo-header scenario (Fix 2c) is
    untouched by Fix D.1, since its background is light, not dark."""
    h, w = 400, 300
    rng = np.random.default_rng(5)
    noise = rng.normal(230, 12, (h, w)).clip(205, 255).astype(np.uint8)
    photo = cv2.GaussianBlur(noise, (25, 25), 0)
    img = cv2.merge([photo, photo, photo])
    img[280:320, 60:240] = (30, 30, 30)

    elements_meta, elements, eligible = analyze_elements_v2(img, _empty_ocr())
    assert elements_meta["darkBackgroundDetected"] is False
    contour_boxes = [(e["x"], e["y"], e["w"], e["h"]) for e in elements if e["source"] == "contour"]
    assert (60, 280, 180, 40) in contour_boxes


def test_dark_background_genuinely_empty_screen_does_not_warn() -> None:
    """Silent-zero guard, negative case: a dark full-bleed background with
    NO other content at all is a genuinely empty screen (e.g. a splash
    screen) -- interactiveTargetCount == 0 here is the honest answer, not a
    detection gap, and must not be flagged as degraded."""
    img = _solid_image(800, 400, (30, 28, 32))
    elements_meta, _elements, _eligible = analyze_elements_v2(img, _empty_ocr())

    assert elements_meta["darkBackgroundDetected"] is True
    assert elements_meta["interactiveTargetCount"] == 0
    assert elements_meta["metricsStatus"] == "ok"
    assert elements_meta["warning"] is None


def test_dark_background_zero_targets_after_filtering_triggers_degraded_status() -> None:
    """Silent-zero guard, positive case: a dark full-bleed background WITH
    other visual content present, but where every recovered candidate is
    filtered back out (here: below the 20x20 size floor), must not present
    interactiveTargetCount == 0 as a clean 'ok' result."""
    img = _solid_image(800, 400, (30, 28, 32))
    img[500:510, 60:70] = (235, 235, 240)  # a light fleck, 10x10 -- well under the size floor
    elements_meta, _elements, eligible = analyze_elements_v2(img, _empty_ocr())

    assert elements_meta["darkBackgroundDetected"] is True
    assert elements_meta["interactiveTargetCount"] == 0
    assert len(eligible) == 0
    assert elements_meta["metricsStatus"] == "degraded"
    assert elements_meta["warning"] is not None
    assert "detection gap" in elements_meta["warning"]


# ---------- Fix 2d: text-glyph contours vs. interactive targets ----------
#
# The Fix 2c regression case: once nested elements stopped being discarded,
# a real screenshot showed a large/bold heading letter counted as a second
# "interactive target" alongside the screen's one real button, corrupting
# both Hick's Law and Fitts's Law. Each test below targets one scenario
# named in the fix request.


def _make_ocr(entries: list[tuple[str, int, int, int, int, int]]) -> dict:
    d: dict = {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}
    for text, x, y, w, h, conf in entries:
        d["text"].append(text)
        d["conf"].append(conf)
        d["left"].append(x)
        d["top"].append(y)
        d["width"].append(w)
        d["height"].append(h)
    return d


def test_large_heading_letter_is_excluded_button_is_kept() -> None:
    """Direct reproduction of the Congratulations.png bug: a large heading
    letter (contour coincides with an OCR-detected headline) plus a real
    button with no OCR correlate at all. Only the button should remain."""
    img = _solid_image(400, 300, (255, 255, 255))
    img[20:50, 20:39] = (20, 20, 20)  # a bold heading letter's ink, ~19x30
    img[300:340, 40:260] = (60, 140, 90)  # a real button, never read by OCR
    ocr_data = _make_ocr([("Heading", 20, 20, 120, 30, 95)])

    elements_meta, elements, targets = analyze_elements_v2(img, ocr_data)
    assert elements_meta["contourBasedCount"] == 2  # both are still visual contours
    assert elements_meta["interactiveTargetCount"] == 1
    assert elements_meta["textGlyphContourExcludedCount"] == 1
    assert elements_meta["smallTargetsBelow44px"] == 1  # button height (40px) is below 44px, correctly on the button, not the letter
    assert targets == [{"x": 40, "y": 300, "w": 220, "h": 40, "source": "contour"}]
    assert elements_meta["hicksLawEstimateMs"] == 150.0  # b*log2(1+1) for exactly one target


def test_text_labeled_button_is_kept_not_excluded() -> None:
    """A button whose label OCR *does* successfully read: the button
    contour is much larger than its label's OCR box, so it is a container
    (a labeled control), not glyph ink, and must be kept."""
    img = _solid_image(400, 300, (255, 255, 255))
    img[100:160, 40:240] = (50, 50, 50)  # a 200x60 button
    ocr_data = _make_ocr([("Submit", 100, 120, 70, 20, 95)])  # label inside the button

    elements_meta, elements, targets = analyze_elements_v2(img, ocr_data)
    assert elements_meta["textGlyphContourExcludedCount"] == 0
    assert elements_meta["interactiveTargetCount"] == 1
    assert targets == [{"x": 40, "y": 100, "w": 200, "h": 60, "source": "contour"}]


def test_checkbox_next_to_label_text_is_kept() -> None:
    """A small checkbox sitting beside (not overlapping) its label text: the
    checkbox has no OCR overlap at all and must survive as an interactive
    target, correctly flagged as a small target."""
    img = _solid_image(200, 300, (255, 255, 255))
    img[50:70, 20:40] = (40, 40, 40)  # a 20x20 checkbox
    ocr_data = _make_ocr([("Remember", 60, 50, 90, 16, 92), ("me", 155, 50, 25, 16, 92)])

    elements_meta, elements, targets = analyze_elements_v2(img, ocr_data)
    assert elements_meta["textGlyphContourExcludedCount"] == 0
    assert elements_meta["interactiveTargetCount"] == 1
    assert elements_meta["smallTargetsBelow44px"] == 1
    assert targets == [{"x": 20, "y": 50, "w": 20, "h": 20, "source": "contour"}]


def test_icon_only_small_button_with_no_ocr_is_kept() -> None:
    """An icon-only control (no text at all, OCR finds nothing) must never
    be swept away just for being small -- point 3 of the fix request."""
    img = _solid_image(200, 200, (255, 255, 255))
    img[80:110, 80:110] = (30, 30, 30)  # a 30x30 icon button
    elements_meta, elements, targets = analyze_elements_v2(img, _empty_ocr())

    assert elements_meta["interactiveTargetCount"] == 1
    assert elements_meta["smallTargetsBelow44px"] == 1
    assert targets == [{"x": 80, "y": 80, "w": 30, "h": 30, "source": "contour"}]


def test_logo_or_large_letter_closely_matched_by_ocr_is_excluded() -> None:
    """A large, decorative single-letter logo whose OCR-read box closely
    coincides with the contour (not a much-smaller label inside a much-
    bigger container) is content, not a control, and must be excluded --
    the size-ratio check, not raw size, is what distinguishes this from a
    real button."""
    img = _solid_image(300, 300, (255, 255, 255))
    img[40:120, 40:110] = (10, 10, 10)  # a large 70x80 logo/letter block
    ocr_data = _make_ocr([("L", 40, 40, 70, 80, 90)])  # OCR box closely matches the contour

    elements_meta, elements, targets = analyze_elements_v2(img, ocr_data)
    assert elements_meta["textGlyphContourExcludedCount"] == 1
    assert elements_meta["interactiveTargetCount"] == 0
    assert targets == []


def test_classify_interactive_targets_debug_reasons() -> None:
    """Direct unit test of the classifier's debug output: each excluded
    contour reports its bbox and an explicit exclusion reason."""
    contour_elements = [
        {"x": 69, "y": 263, "w": 19, "h": 23, "source": "contour"},  # coincides with headline OCR
        {"x": 32, "y": 467, "w": 311, "h": 51, "source": "contour"},  # no OCR correlate
    ]
    ocr_data = _make_ocr([("Congratulations!", 69, 262, 239, 30, 96)])
    kept, excluded_debug = _classify_interactive_targets(contour_elements, ocr_data)

    assert kept == [{"x": 32, "y": 467, "w": 311, "h": 51, "source": "contour"}]
    assert excluded_debug == [{"bbox": (69, 263, 19, 23), "reason": "text_glyph_ocr_match"}]


def test_fitts_single_target_never_fabricates_a_neighbor_distance() -> None:
    """End-to-end: with exactly one interactive target, Fitts's Law must
    report no ID, `status: not_applicable`, and `elementsConsidered == 1`,
    never a nearest-neighbor distance to a non-control contour."""
    img = _solid_image(400, 300, (255, 255, 255))
    img[20:50, 20:39] = (20, 20, 20)
    img[300:340, 40:260] = (60, 140, 90)
    ocr_data = _make_ocr([("Heading", 20, 20, 120, 30, 95)])
    _, _, targets = analyze_elements_v2(img, ocr_data)

    fitts = analyze_fitts_full_v2(targets)
    assert fitts["averageIndexOfDifficulty"] is None
    assert fitts["elementsConsidered"] == 1
    assert fitts["status"] == "not_applicable"


# ---------- Fix 2e: system-keyboard region detection ----------
#
# The Fix 2c/2d regression case: a real on-screen iOS keyboard still counted
# ~160 keyboard-related contours as interactive targets, since the existing
# repeating-grid detector (geometry-only) doesn't recognize a keyboard's
# irregular letter-ink/separator-line contour signature. Each test below
# targets one scenario named in the fix request; all use fabricated element
# dicts directly (no rendered images needed, matching `_detect_repeating_grid_indices`'s
# own test convention) except the end-to-end Sign-Up-shaped case.


def _qwerty_keyboard_elements(img_w: int = 400, y0: int = 600) -> list[dict]:
    rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    elements = []
    for r, row in enumerate(rows):
        key_w = img_w // len(row)
        for c in range(len(row)):
            elements.append({"x": c * key_w, "y": y0 + r * 35, "w": key_w - 4, "h": 30, "source": "contour"})
    elements.append({"x": 0, "y": y0 + 105, "w": 60, "h": 30, "source": "contour"})
    elements.append({"x": 70, "y": y0 + 105, "w": img_w - 130, "h": 30, "source": "contour"})
    elements.append({"x": img_w - 60, "y": y0 + 105, "w": 60, "h": 30, "source": "contour"})
    return elements


def _qwerty_ocr(img_w: int = 400, y0: int = 600) -> dict:
    return _make_ocr(
        [
            ("qwertyuiop", 0, y0, img_w, 30, 80),
            ("123", 0, y0 + 105, 60, 30, 85),
            ("space", 70, y0 + 105, img_w - 130, 30, 90),
            ("Go", img_w - 60, y0 + 105, 60, 30, 90),
        ]
    )


def test_realistic_qwerty_keyboard_is_detected() -> None:
    """A real iOS-QWERTY-shaped layout (3 letter rows + a control row,
    QWERTY OCR match, keyword hits) must be confidently detected."""
    elements = _qwerty_keyboard_elements()
    ocr_data = _qwerty_ocr()
    result = _detect_keyboard_region(elements, ocr_data, (800, 400, 3))
    assert result["status"] == "detected"
    assert result["detected"] is True
    assert result["confidence"] >= 0.55
    assert result["rowCount"] >= 3


def test_numeric_keypad_is_detected() -> None:
    """A narrower numeric keypad (PIN entry): no QWERTY sequence, but a
    high single-character OCR ratio and 4 dense rows must still cross the
    detection threshold."""
    digits = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["*", "0", "#"]]
    key_w, key_h, x_start, y0 = 80, 60, 80, 500
    elements = []
    ocr_entries = []
    for r, row in enumerate(digits):
        for c, d in enumerate(row):
            x, y = x_start + c * (key_w + 10), y0 + r * (key_h + 10)
            elements.append({"x": x, "y": y, "w": key_w, "h": key_h, "source": "contour"})
            ocr_entries.append((d, x, y, key_w, key_h, 85))
    ocr_data = _make_ocr(ocr_entries)
    result = _detect_keyboard_region(elements, ocr_data, (800, 400, 3))
    assert result["status"] == "detected"
    assert result["signals"]["singleCharSignal"] == 1.0


def test_keyboardless_form_screen_is_not_detected() -> None:
    """A form with a couple of input fields and a bottom submit button, no
    keyboard visible at all -- must not be flagged."""
    elements = [
        {"x": 20, "y": 100, "w": 360, "h": 50, "source": "contour"},
        {"x": 20, "y": 170, "w": 360, "h": 50, "source": "contour"},
        {"x": 20, "y": 700, "w": 360, "h": 50, "source": "contour"},
    ]
    ocr_data = _make_ocr([("Submit", 150, 715, 100, 20, 90)])
    result = _detect_keyboard_region(elements, ocr_data, (800, 400, 3))
    assert result["status"] == "none"
    assert result["detected"] is False


def test_bottom_button_grid_is_not_mistaken_for_a_keyboard() -> None:
    """A 2x2 bottom button grid (e.g. Home/Search/Cart/Profile) is
    bottom-anchored and reasonably wide, like a keyboard, but must not be
    confidently detected as one -- pure geometry is capped below the
    detection threshold."""
    labels = [["Home", "Search"], ["Cart", "Profile"]]
    y0 = 650
    elements = []
    ocr_entries = []
    for r, row in enumerate(labels):
        for c, label in enumerate(row):
            x, y = 40 + c * 180, y0 + r * 70
            elements.append({"x": x, "y": y, "w": 140, "h": 50, "source": "contour"})
            ocr_entries.append((label, x + 20, y + 15, len(label) * 10, 20, 90))
    ocr_data = _make_ocr(ocr_entries)
    result = _detect_keyboard_region(elements, ocr_data, (800, 400, 3))
    assert result["status"] != "detected"


def test_messaging_screen_bottom_nav_is_not_mistaken_for_a_keyboard() -> None:
    """A single-row, 5-icon bottom navigation bar -- extremely common,
    must never trigger keyboard detection or even a degraded warning."""
    elements = [{"x": i * 80, "y": 750, "w": 40, "h": 40, "source": "contour"} for i in range(5)]
    result = _detect_keyboard_region(elements, _empty_ocr(), (800, 400, 3))
    assert result["status"] == "none"


def test_partially_visible_keyboard_is_degraded_not_confidently_resolved() -> None:
    """Only one keyboard row is visible (e.g. scrolled/partially covered):
    with a QWERTY OCR match but insufficient row count, the result must be
    `degraded` (uncertain) -- neither a confident detection nor a confident
    dismissal."""
    row = "qwertyuiop"
    key_w = 400 // len(row)
    elements = [{"x": c * key_w, "y": 750, "w": key_w - 4, "h": 30, "source": "contour"} for c in range(len(row))]
    ocr_data = _make_ocr([("qwertyuiop", 0, 750, 400, 30, 80)])
    result = _detect_keyboard_region(elements, ocr_data, (800, 400, 3))
    assert result["status"] == "degraded"
    assert result["detected"] is False


def test_degraded_keyboard_detection_excludes_nothing_but_warns() -> None:
    """End to end: a `degraded` (uncertain) keyboard signal -- one row, hard
    against the bottom edge, with a QWERTY OCR match but insufficient row
    count -- must not exclude any contour from interactiveTargets, but must
    surface `metricsStatus`/`warning`."""
    row = "qwertyuiop"
    img_w, img_h = 400, 800
    key_w = img_w // len(row)
    img = _solid_image(img_h, img_w, (255, 255, 255))
    for c in range(len(row)):
        img[750:780, c * key_w : c * key_w + key_w - 4] = (30, 30, 30)
    ocr_data = _make_ocr([("qwertyuiop", 0, 750, img_w, 30, 80)])

    elements_meta, elements, targets = analyze_elements_v2(img, ocr_data)
    assert elements_meta["keyboardDetected"] is False
    assert elements_meta["metricsStatus"] == "degraded"
    assert elements_meta["warning"] is not None
    # Nothing excluded on the *keyboard* pathway specifically, despite the
    # uncertainty (a separate, already-tested mechanism -- Fix 2d's
    # text-glyph classifier -- independently excludes these same contours
    # here because they coincide with the single merged "qwertyuiop" OCR
    # box; that is not what this test is checking).
    assert elements_meta["keyboardExcludedTargetCount"] == 0


def test_real_qwerty_keyboard_end_to_end_excludes_targets_and_flags_status() -> None:
    """End to end via `analyze_elements_v2`: a confidently detected keyboard
    excludes its own contours from interactiveTargets/Hick's Law/
    smallTargetsBelow44px, while unrelated form elements above it survive,
    and `metricsStatus` stays "ok" (not degraded) for a confident result."""
    img_w = 1125
    img = _solid_image(1000, img_w, (255, 255, 255))
    # A real control well above the keyboard: a 200x60 button.
    img[400:460, 100:300] = (60, 60, 60)
    for e in _qwerty_keyboard_elements(img_w=img_w, y0=700):
        img[e["y"] : e["y"] + e["h"], e["x"] : e["x"] + e["w"]] = (20, 20, 20)
    ocr_data = _qwerty_ocr(img_w=img_w, y0=700)

    elements_meta, elements, targets = analyze_elements_v2(img, ocr_data)
    assert elements_meta["keyboardDetected"] is True
    assert elements_meta["keyboardDetectionConfidence"] >= 0.55
    assert elements_meta["keyboardRegionBbox"] is not None
    assert elements_meta["keyboardExcludedTargetCount"] > 0
    assert elements_meta["metricsStatus"] == "ok"
    assert elements_meta["warning"] is None
    # the button above the keyboard survives as the only interactive target
    assert targets == [{"x": 100, "y": 400, "w": 200, "h": 60, "source": "contour"}]
