"""Tests for `analyze_contrast_v3` (Contrast Sampling V3, engine "corrected-v2").

A per-region diagnostic run against a real screenshot found `analyze_contrast_v2`
(Otsu ink/paper separation, but a flat mean of the whole ink cluster) still
understated contrast on small, regular-weight text, because anti-aliased
edge pixels dominate a small glyph's ink cluster and pull its mean toward
gray. These tests build synthetic regions with a controlled, deterministic
anti-aliasing pattern (no system font dependency, fully portable) to prove
the darkest/lightest-core-percentile + per-channel-median fix actually
recovers the true ink color, without pushing every region toward 21:1 and
without a single stray pixel skewing the result. No real screenshots, no
Tesseract binary, no network, per CLAUDE.md Testing Rules.
"""

import numpy as np

from app.metrics.corrected import analyze_contrast_v3


def _canvas(height: int, width: int, bgr: tuple[int, int, int]) -> np.ndarray:
    return np.full((height, width, 3), bgr, dtype=np.uint8)


def _ocr(bbox: tuple[int, int, int, int], text: str = "sample", conf: int = 90) -> dict:
    x, y, w, h = bbox
    return {"text": [text], "conf": [conf], "left": [x], "top": [y], "width": [w], "height": [h]}


def _draw_anti_aliased_strokes(
    img: np.ndarray, y0: int, y1: int, core_bgr: tuple[int, int, int], edge_bgr: tuple[int, int, int]
) -> None:
    """Paints three thin "glyph strokes" across the image width, each a
    narrow solid core flanked by a much wider anti-aliasing band — so most
    of the resulting ink-cluster pixels are edge blend, not core, matching
    how small regular-weight text actually rasterizes."""
    for stroke in range(3):
        x0 = 5 + stroke * 15
        img[y0:y1, x0 : x0 + 4, :] = edge_bgr
        img[y0:y1, x0 + 4 : x0 + 6, :] = core_bgr
        img[y0:y1, x0 + 6 : x0 + 10, :] = edge_bgr


# ---------- 1. Small black anti-aliased text on white ----------


def test_small_anti_aliased_black_text_recovers_true_black() -> None:
    img = _canvas(30, 60, (255, 255, 255))
    _draw_anti_aliased_strokes(img, 10, 20, core_bgr=(0, 0, 0), edge_bgr=(120, 120, 120))
    aggregate, regions = analyze_contrast_v3(img, _ocr((0, 5, 60, 20)))
    region = regions[0]

    assert region["status"] == "valid"
    assert region["polarity"] == "dark_on_light"
    # The core-percentile sample must be dominated by anti-aliasing edge
    # pixels in this fixture (60 core px vs 120 edge px in the ink
    # cluster) -- if the fix regressed to a whole-cluster mean, foreground
    # would land near (80,80,80), not near-black.
    assert all(c < 20 for c in region["foregroundRgb"])
    assert region["ratio"] >= 15.0
    assert region["aa"] == "pass"
    assert aggregate["regionsBelowAAThreshold"] == 0


# ---------- 2. Large bold black text on white ----------


def test_large_bold_black_text_remains_high_contrast() -> None:
    img = _canvas(60, 70, (255, 255, 255))
    for stroke in range(3):
        x0 = 8 + stroke * 20
        img[10:50, x0 : x0 + 10, :] = (0, 0, 0)  # thick solid bar, no anti-aliasing needed
    aggregate, regions = analyze_contrast_v3(img, _ocr((5, 5, 60, 50)))
    region = regions[0]

    assert region["status"] == "valid"
    assert region["polarity"] == "dark_on_light"
    assert region["foregroundRgb"] == (0.0, 0.0, 0.0)
    assert region["ratio"] == 21.0
    assert region["aa"] == "pass"


# ---------- 3. Small white anti-aliased text on dark green ----------


def test_small_anti_aliased_white_text_on_dark_green_recovers_true_white() -> None:
    img = _canvas(30, 60, (20, 90, 20))  # dark green background (BGR)
    _draw_anti_aliased_strokes(img, 10, 20, core_bgr=(255, 255, 255), edge_bgr=(150, 180, 150))
    aggregate, regions = analyze_contrast_v3(img, _ocr((0, 5, 60, 20)))
    region = regions[0]

    assert region["status"] == "valid"
    assert region["polarity"] == "light_on_dark"
    assert all(c > 235 for c in region["foregroundRgb"])
    assert region["ratio"] > 4.5
    assert region["aa"] == "pass"


# ---------- 4. Genuinely gray text on white ----------


def test_genuinely_gray_text_is_reported_as_gray_not_pushed_to_an_extreme() -> None:
    """The algorithm must not force every region toward 21:1 -- real
    mid-gray text (e.g. a deliberate #666666 body-copy color) should come
    back close to its true color and a plausible mid ratio."""
    img = _canvas(30, 60, (255, 255, 255))
    img[10:20, 10:50, :] = (102, 102, 102)
    aggregate, regions = analyze_contrast_v3(img, _ocr((5, 5, 50, 20)))
    region = regions[0]

    assert region["status"] == "valid"
    assert region["foregroundRgb"] == (102.0, 102.0, 102.0)
    assert 4.5 < region["ratio"] < 8.0
    assert region["aa"] == "pass"


# ---------- 5. Isolated black noise pixel inside an otherwise gray region ----------


def test_single_noise_pixel_does_not_skew_the_median_estimate() -> None:
    img = _canvas(30, 60, (255, 255, 255))
    img[10:20, 10:50, :] = (102, 102, 102)
    img[15, 30, :] = (0, 0, 0)  # one stray pure-black pixel -- noise/compression artifact
    aggregate, regions = analyze_contrast_v3(img, _ocr((5, 5, 50, 20)))
    region = regions[0]

    # Must match the noise-free case exactly: a single outlier pixel must
    # never move a per-channel median.
    assert region["foregroundRgb"] == (102.0, 102.0, 102.0)
    assert region["ratio"] < 8.0
    assert region["corePixelCount"] > 1


# ---------- Uncertain-status handling ----------


def test_tiny_ink_cluster_is_reported_uncertain_not_fabricated() -> None:
    img = _canvas(30, 60, (255, 255, 255))
    img[15, 15, :] = (0, 0, 0)  # a single dark pixel -- far too small a sample to trust
    aggregate, regions = analyze_contrast_v3(img, _ocr((5, 5, 20, 20)))
    region = regions[0]

    assert region["status"] == "uncertain"
    assert region["ratio"] is None
    assert region["aa"] is None
    assert aggregate["regionsAnalyzed"] == 0
    assert aggregate["regionsUncertain"] == 1
    # Uncertain regions must never count toward confirmed AA violations.
    assert aggregate["regionsBelowAAThreshold"] == 0


def test_uncertain_regions_are_never_counted_as_aa_violations_in_aggregate() -> None:
    img = _canvas(40, 80, (255, 255, 255))
    img[15, 15, :] = (0, 0, 0)  # tiny/uncertain region
    img[20:30, 40:70, :] = (102, 102, 102)  # a real, valid, passing gray region
    ocr_data = {
        "text": ["tiny", "gray"],
        "conf": [90, 90],
        "left": [5, 35],
        "top": [5, 15],
        "width": [20, 40],
        "height": [20, 20],
    }
    aggregate, regions = analyze_contrast_v3(img, ocr_data)

    statuses = {r["text"]: r["status"] for r in regions}
    assert statuses["tiny"] == "uncertain"
    assert statuses["gray"] == "valid"
    assert aggregate["regionsAnalyzed"] == 1
    assert aggregate["regionsUncertain"] == 1
    assert aggregate["regionsBelowAAThreshold"] == 0


# ---------- Diagnostic fields ----------


def test_valid_region_reports_all_required_diagnostic_fields() -> None:
    img = _canvas(30, 60, (255, 255, 255))
    img[10:20, 10:50, :] = (0, 0, 0)
    _, regions = analyze_contrast_v3(img, _ocr((5, 5, 50, 20), text="Sign", conf=96))
    region = regions[0]

    assert region["text"] == "Sign"
    assert region["bbox"] == (5, 5, 50, 20)
    assert region["ocrConfidence"] == 96
    assert isinstance(region["otsuThreshold"], float)
    assert region["polarity"] in ("dark_on_light", "light_on_dark")
    assert isinstance(region["inkClusterSize"], int)
    assert region["corePixelPercentile"] == 15
    assert isinstance(region["corePixelCount"], int)
    assert len(region["foregroundRgb"]) == 3
    assert len(region["backgroundRgb"]) == 3
    assert 0.0 <= region["confidence"] <= 1.0
    assert region["status"] == "valid"
    assert region["aa"] in ("pass", "fail")


# ---------- Background estimation (border-connected only) ----------


def test_background_excludes_holes_enclosed_inside_a_glyph() -> None:
    """A background-colored pixel enclosed inside a glyph (e.g. the inside
    of a bold "O") must not be averaged into the background estimate --
    only background pixels touching the crop border should count. The
    enclosed "hole" is deliberately a *different* light shade from the true
    border background, so an incorrect implementation (one that averages
    the whole background-side Otsu cluster) would measurably shift the
    result away from pure white."""
    img = _canvas(40, 40, (255, 255, 255))
    img[5:35, 5:35, :] = (0, 0, 0)  # bold ring...
    img[12:28, 12:28, :] = (235, 235, 235)  # ...with a light-gray "hole" in the middle, like an "O"
    _, regions = analyze_contrast_v3(img, _ocr((3, 3, 34, 34)))
    region = regions[0]

    assert region["status"] == "valid"
    # Must read as the true border background (pure white), not a blend
    # with the enclosed hole's 235 gray.
    assert region["backgroundRgb"] == (255.0, 255.0, 255.0)
