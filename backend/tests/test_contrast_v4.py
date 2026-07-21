"""Tests for `analyze_contrast_v4` (dual-estimate contrast, engine "corrected-v3").

A cross-check against three independent whole-region methods (Otsu-cluster
mean, percentile-decile, k-means) found `analyze_contrast_v3`'s core-percentile
estimate measurably higher than all three on small anti-aliased paragraph
text — large enough to flip the WCAG AA classification. These tests prove
`analyze_contrast_v4` only reports a confirmed pass/fail when a core
estimate and a conservative (whole-ink-cluster median) estimate agree, and
reports `borderline` with both ratios otherwise — never picking a side, never
fabricating a single number, never counting a borderline/uncertain region as
a confirmed pass or violation. No real screenshots, no Tesseract binary, no
network, per CLAUDE.md Testing Rules.
"""

import numpy as np

from app.metrics.corrected import analyze_contrast_v4


def _canvas(height: int, width: int, bgr: tuple[int, int, int]) -> np.ndarray:
    return np.full((height, width, 3), bgr, dtype=np.uint8)


def _ocr(bbox: tuple[int, int, int, int], text: str = "sample", conf: int = 90) -> dict:
    x, y, w, h = bbox
    return {"text": [text], "conf": [conf], "left": [x], "top": [y], "width": [w], "height": [h]}


def _draw_straddling_strokes(img: np.ndarray, y0: int, y1: int, core_val: int, edge_val: int) -> None:
    """Four strokes with a core fraction (~33% of the ink cluster) comfortably
    above the 15% core-percentile window, tuned so the whole-cluster median
    (conservative) and the darkest-15% median (core) land on opposite sides
    of the 4.5 AA threshold."""
    for stroke in range(4):
        x0 = 5 + stroke * 22
        img[y0:y1, x0 : x0 + 4, :] = edge_val
        img[y0:y1, x0 + 4 : x0 + 8, :] = core_val
        img[y0:y1, x0 + 8 : x0 + 12, :] = edge_val


# ---------- Confirmed pass / fail ----------


def test_large_bold_text_is_a_confirmed_pass() -> None:
    img = _canvas(60, 70, (255, 255, 255))
    for stroke in range(3):
        x0 = 8 + stroke * 20
        img[10:50, x0 : x0 + 10, :] = (0, 0, 0)
    _, regions = analyze_contrast_v4(img, _ocr((5, 5, 60, 50)))
    region = regions[0]

    assert region["status"] == "valid"
    assert region["aaResult"] == "pass"
    assert region["coreRatio"] == region["conservativeRatio"] == region["ratio"]
    assert region["range"] is None


def test_light_gray_text_is_a_confirmed_fail() -> None:
    """Both estimates should agree on a genuinely low-contrast light-gray
    solid fill (no anti-aliasing gradient to disagree about)."""
    img = _canvas(30, 60, (255, 255, 255))
    img[10:20, 10:50, :] = (200, 200, 200)
    _, regions = analyze_contrast_v4(img, _ocr((5, 5, 50, 20)))
    region = regions[0]

    assert region["status"] == "valid"
    assert region["aaResult"] == "fail"
    assert region["coreRatio"] == region["conservativeRatio"]
    assert region["range"] is None


# ---------- Borderline (estimate disagreement) ----------


def test_straddling_estimates_are_reported_borderline_not_forced() -> None:
    img = _canvas(30, 100, (255, 255, 255))
    _draw_straddling_strokes(img, 10, 20, core_val=60, edge_val=130)
    aggregate, regions = analyze_contrast_v4(img, _ocr((0, 5, 100, 20)))
    region = regions[0]

    assert region["status"] == "uncertain"
    assert region["reason"] == "estimate_disagreement"
    assert region["aaResult"] == "borderline"
    assert region["ratio"] is None
    assert region["coreRatio"] >= 4.5
    assert region["conservativeRatio"] < 4.5
    assert region["range"] == [region["conservativeRatio"], region["coreRatio"]]

    # Never counted as either a confirmed pass or a confirmed violation.
    assert aggregate["regionsAnalyzed"] == 0
    assert aggregate["regionsBelowAAThreshold"] == 0
    assert aggregate["regionsBorderline"] == 1
    assert aggregate["averageContrastRatio"] is None


def test_range_is_sorted_regardless_of_which_estimate_is_higher() -> None:
    """Build the mirror image of the light-on-dark case so the conservative
    estimate ends up numerically *larger* than the core estimate, and check
    the range is still [low, high]."""
    img = _canvas(30, 100, (20, 20, 20))  # dark background
    for stroke in range(4):
        x0 = 5 + stroke * 22
        img[10:20, x0 : x0 + 4, :] = (140, 140, 140)
        img[10:20, x0 + 4 : x0 + 8, :] = (250, 250, 250)  # bright core, minority
        img[10:20, x0 + 8 : x0 + 12, :] = (140, 140, 140)
    _, regions = analyze_contrast_v4(img, _ocr((0, 5, 100, 20)))
    region = regions[0]

    if region["aaResult"] == "borderline":
        low, high = region["range"]
        assert low <= high
        assert low == min(region["coreRatio"], region["conservativeRatio"])
        assert high == max(region["coreRatio"], region["conservativeRatio"])


# ---------- Uncertain (insufficient sample) — unchanged semantics, new field names ----------


def test_tiny_ink_cluster_is_uncertain_with_v4_field_names() -> None:
    img = _canvas(30, 60, (255, 255, 255))
    img[15, 15, :] = (0, 0, 0)
    aggregate, regions = analyze_contrast_v4(img, _ocr((5, 5, 20, 20)))
    region = regions[0]

    assert region["status"] == "uncertain"
    assert region["reason"] == "ink_cluster_too_small"
    assert region["aaResult"] is None
    assert region["ratio"] is None
    assert region["range"] is None
    assert aggregate["regionsUncertain"] == 1
    assert aggregate["regionsBorderline"] == 0
    assert aggregate["regionsBelowAAThreshold"] == 0


# ---------- Aggregate accounting across a mix of region types ----------


def test_aggregate_accounts_for_every_region_exactly_once() -> None:
    img = _canvas(50, 160, (255, 255, 255))
    img[5:15, 5:45, :] = (0, 0, 0)  # confirmed pass (bold black)
    img[20:30, 5:45, :] = (200, 200, 200)  # confirmed fail (flat light gray)
    _draw_straddling_strokes(img, 35, 45, core_val=60, edge_val=130)  # borderline
    ocr_data = {
        "text": ["bold", "faint", "straddle"],
        "conf": [90, 90, 90],
        "left": [5, 5, 0],
        "top": [5, 20, 35],
        "width": [40, 40, 100],
        "height": [10, 10, 10],
    }
    aggregate, regions = analyze_contrast_v4(img, ocr_data)

    statuses = {r["text"]: (r["status"], r["aaResult"]) for r in regions}
    assert statuses["bold"] == ("valid", "pass")
    assert statuses["faint"] == ("valid", "fail")
    assert statuses["straddle"] == ("uncertain", "borderline")

    assert aggregate["regionsAnalyzed"] == 2  # bold + faint only
    assert aggregate["regionsBelowAAThreshold"] == 1  # faint only
    assert aggregate["regionsBorderline"] == 1
    assert aggregate["regionsUncertain"] == 0
