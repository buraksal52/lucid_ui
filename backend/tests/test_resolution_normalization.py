"""Tests for Fix 2f: resolution-driven metric inconsistency.

The same design, exported as screenshots at different raw pixel widths,
produced different deterministic metrics purely from export resolution --
not because the design differs -- because many thresholds inside
`app.metrics.corrected` (the 400px-area contour/OCR floor, the 44px
small-target check, the 8px alignment tolerance, the 20px whitespace
block, ...) are fixed in raw image pixels. `MetricEngine._normalize_for_analysis`
resizes the decoded image to one fixed reference width (aspect ratio
preserved) before OCR and any deterministic metric runs, so those
thresholds implicitly apply at a consistent effective scale.

Synthetic images/OCR data only (contour-only, empty OCR) — no real
screenshots, no Tesseract binary, per CLAUDE.md Testing Rules. OCR
word-count consistency specifically depends on Tesseract's own real
recognition behavior and can only be empirically verified against real
screenshots (done ad hoc, outside this suite, against
`screen.png`/`screen2.png`).
"""

import numpy as np
import pytest

from app.metrics.corrected import analyze_elements_v2
from app.metrics.engine import MetricEngine


def _empty_ocr() -> dict:
    return {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}


# ---------- Direct unit tests of `_normalize_for_analysis` ----------


def test_upscales_narrow_image_to_reference_width_preserving_aspect_ratio() -> None:
    img = np.full((800, 300, 3), 255, dtype=np.uint8)  # 300x800, narrower than the 390 floor
    resized, info = MetricEngine._normalize_for_analysis(img)

    assert resized.shape[1] == 390
    assert resized.shape[0] == round(800 * (390 / 300))
    # aspect ratio preserved to within rounding
    original_ratio = 300 / 800
    resized_ratio = resized.shape[1] / resized.shape[0]
    assert abs(original_ratio - resized_ratio) < 0.01
    assert info["originalResolution"] == {"width": 300, "height": 800}
    assert info["analysisResolution"] == {"width": 390, "height": resized.shape[0]}
    assert info["normalizationScale"] == pytest.approx(390 / 300, abs=1e-4)


def test_image_already_at_reference_width_is_untouched() -> None:
    img = np.full((700, 390, 3), 255, dtype=np.uint8)
    resized, info = MetricEngine._normalize_for_analysis(img)

    assert resized.shape == img.shape
    assert info["normalizationScale"] == 1.0
    assert info["resolutionWarning"] is None
    assert info["inputQualityStatus"] == "ok"


def test_significant_upscale_flags_resolution_warning_and_degraded_status() -> None:
    img = np.full((560, 320, 3), 255, dtype=np.uint8)  # notably narrower than reference
    _resized, info = MetricEngine._normalize_for_analysis(img)

    assert info["normalizationScale"] > 1.0
    assert info["resolutionWarning"] is not None
    assert "upscal" in info["resolutionWarning"]
    assert info["inputQualityStatus"] == "degraded"


def test_wide_image_is_never_downscaled_regardless_of_how_far_above_the_floor() -> None:
    """Fix 2f is deliberately asymmetric: an early symmetric version
    downscaled high-DPI exports (e.g. a 3x Retina capture) enough to
    shrink small-but-legitimate detail -- most visibly a keyboard key's
    letter ink -- below fixed area floors the keyboard detector (Fix 2e)
    depends on, silently regressing an already-working detection. An image
    at or above the reference floor must be left at native resolution."""
    img = np.full((2436, 1125, 3), 255, dtype=np.uint8)  # a 3x Retina-scale export
    resized, info = MetricEngine._normalize_for_analysis(img)

    assert resized.shape == img.shape
    assert info["originalResolution"] == {"width": 1125, "height": 2436}
    assert info["analysisResolution"] == {"width": 1125, "height": 2436}
    assert info["normalizationScale"] == 1.0
    assert info["resolutionWarning"] is None
    assert info["inputQualityStatus"] == "ok"


def test_moderate_scale_difference_has_no_warning() -> None:
    # 375px and 430px are both common device widths, close enough to the
    # 390px reference that resampling is minor -- must not be flagged.
    for width in (375, 430):
        img = np.full((round(700 * width / 390), width, 3), 255, dtype=np.uint8)
        _resized, info = MetricEngine._normalize_for_analysis(img)
        assert info["resolutionWarning"] is None, f"unexpected warning at width={width}"
        assert info["inputQualityStatus"] == "ok"


# ---------- Cross-resolution invariance: same design, four raw widths ----------
#
# A single logical layout, defined once at the reference width (390), is
# rendered as raw contour rectangles at four different raw pixel widths
# (320/375/390/430 -- the four widths named in the original fix request).
# Comparing metrics computed after each is normalized back to the reference
# width demonstrates the fix: the same design should read the same
# regardless of which width it happened to be exported at.
#
# The original version of this section tracked `smallTargetsBelow44px`/
# `alignedElementRatio`/`whitespaceRatio`/`weightedScore` specifically
# because they were the clearest illustration of a fixed-raw-pixel-
# threshold consistency bug (a 9px reference-space gap crossing the fixed
# 8px alignment tolerance purely from render width). All four were removed
# from the engine/API as Tier 3 ("Problematic") per
# docs/metrics/reliability-tiers.md (corrected-v4) -- this section now
# tracks the retained, still resolution-sensitive `contourBasedCount`/
# `interactiveTargetCount` instead. The `_normalize_for_analysis` resize
# mechanism itself is unchanged by that removal and is covered directly by
# the unit tests above.

_REFERENCE_WIDTH = 390
_REFERENCE_HEIGHT = 700
_LOGICAL_ELEMENTS = [
    (20, 550, 350, 48),  # a real button, >=44px both dims at reference scale
    (20, 100, 32, 32),  # icon A
    (29, 160, 32, 32),  # icon B
    (300, 250, 32, 32),  # icon C, unaligned with anything
]
_TEST_WIDTHS = (320, 375, 390, 430)


def _render_design(width: int) -> np.ndarray:
    scale = width / _REFERENCE_WIDTH
    height = round(_REFERENCE_HEIGHT * scale)
    img = np.full((height, width, 3), (250, 250, 250), dtype=np.uint8)
    for x, y, w, h in _LOGICAL_ELEMENTS:
        rx, ry, rw, rh = round(x * scale), round(y * scale), round(w * scale), round(h * scale)
        img[ry : ry + rh, rx : rx + rw] = (40, 40, 40)
    return img


def _compute_metrics(img: np.ndarray) -> dict:
    elements_meta, _elements, _targets = analyze_elements_v2(img, _empty_ocr())
    return {
        "contourBasedCount": elements_meta["contourBasedCount"],
        "interactiveTargetCount": elements_meta["interactiveTargetCount"],
    }


@pytest.mark.parametrize("width", _TEST_WIDTHS)
def test_normalized_analysis_matches_reference_within_tolerance(width: int) -> None:
    """After resizing back to the reference width, each of the four renders
    must agree with the reference-width (390) render itself."""
    reference_metrics = _compute_metrics(_render_design(_REFERENCE_WIDTH))

    raw_render = _render_design(width)
    normalized_img, _info = MetricEngine._normalize_for_analysis(raw_render)
    metrics = _compute_metrics(normalized_img)

    assert metrics["contourBasedCount"] == reference_metrics["contourBasedCount"]
    assert metrics["interactiveTargetCount"] == reference_metrics["interactiveTargetCount"]
