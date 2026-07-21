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

from app.metrics.corrected import analyze_elements_v2, analyze_whitespace_alignment_v2
from app.metrics.engine import MetricEngine
from reference.legacy_metric_engine import normalize_metrics, weighted_score


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
# (320/375/390/430 -- the four widths named in the fix request). Comparing
# metrics computed directly on each raw-width render ("before") against
# metrics computed after each is normalized back to the reference width
# ("after") demonstrates the fix: the same design should read the same
# regardless of which width it happened to be exported at.

_REFERENCE_WIDTH = 390
_REFERENCE_HEIGHT = 700
_LOGICAL_ELEMENTS = [
    (20, 550, 350, 48),  # a real button, >=44px both dims at reference scale
    (20, 100, 32, 32),  # icon A, x=20
    (29, 160, 32, 32),  # icon B, x=29 -- a 9px reference-space offset from icon A: just
    # outside the (fixed, unscaled) 8px alignment tolerance at reference scale, but downscaling
    # (e.g. to 320px, factor ~0.82) shrinks that same 9px gap to ~7.4px raw -- under the
    # tolerance -- flipping "aligned" purely from render width unless normalized first.
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
    elements_meta, elements, _targets = analyze_elements_v2(img, _empty_ocr())
    whitespace = analyze_whitespace_alignment_v2(img, elements)
    raw = {
        "contrast": {"averageContrastRatio": 10.0},
        "clutter": {"edgeDensity": 0.05},
        "textDensity": {"textDensityRatio": 0.05},
        "elements": elements_meta,
        "groups": {"estimatedGroupCount": 4},
    }
    score = weighted_score(normalize_metrics(raw), "general")
    return {
        "interactiveTargetCount": elements_meta["interactiveTargetCount"],
        "smallTargetsBelow44px": elements_meta["smallTargetsBelow44px"],
        "alignedElementRatio": whitespace["alignedElementRatio"],
        "whitespaceRatio": whitespace["whitespaceRatio"],
        "weightedScore": score,
    }


def test_native_resolution_analysis_is_inconsistent_across_widths() -> None:
    """Documents the bug being fixed: analyzing each raw-width render
    directly (no normalization) produces inconsistent metrics for the
    identical design, exceeding the fix's own tolerance targets."""
    results = {w: _compute_metrics(_render_design(w)) for w in _TEST_WIDTHS}
    small_targets = [r["smallTargetsBelow44px"] for r in results.values()]
    aligned = [r["alignedElementRatio"] for r in results.values()]
    whitespace = [r["whitespaceRatio"] for r in results.values()]
    scores = [r["weightedScore"] for r in results.values()]

    # At least one of these must exceed tolerance pre-fix, proving the
    # synthetic design actually exercises the bug (not a vacuous check).
    assert (
        (max(small_targets) - min(small_targets)) > 0
        or (max(aligned) - min(aligned)) > 0.05
        or (max(whitespace) - min(whitespace)) > 0.03
        or (max(scores) - min(scores)) > 3
    )


@pytest.mark.parametrize("width", _TEST_WIDTHS)
def test_normalized_analysis_matches_reference_within_tolerance(width: int) -> None:
    """The fix: after resizing back to the reference width, each of the
    four renders must agree with the reference-width (390) render itself,
    within the fix's stated tolerance targets."""
    reference_metrics = _compute_metrics(_render_design(_REFERENCE_WIDTH))

    raw_render = _render_design(width)
    normalized_img, _info = MetricEngine._normalize_for_analysis(raw_render)
    metrics = _compute_metrics(normalized_img)

    assert abs(metrics["interactiveTargetCount"] - reference_metrics["interactiveTargetCount"]) <= 1
    assert metrics["smallTargetsBelow44px"] == reference_metrics["smallTargetsBelow44px"]
    assert abs(metrics["alignedElementRatio"] - reference_metrics["alignedElementRatio"]) <= 0.05
    assert abs(metrics["whitespaceRatio"] - reference_metrics["whitespaceRatio"]) <= 0.03
    assert abs(metrics["weightedScore"] - reference_metrics["weightedScore"]) <= 3


def test_normalization_meaningfully_reduces_cross_width_spread() -> None:
    """End-to-end comparison: the spread (max-min) across all four widths
    must shrink after normalization for every metric the fix targets."""
    before = {w: _compute_metrics(_render_design(w)) for w in _TEST_WIDTHS}
    after = {}
    for w in _TEST_WIDTHS:
        normalized_img, _info = MetricEngine._normalize_for_analysis(_render_design(w))
        after[w] = _compute_metrics(normalized_img)

    def spread(results: dict, key: str) -> float:
        values = [r[key] for r in results.values()]
        return max(values) - min(values)

    for key in ("smallTargetsBelow44px", "alignedElementRatio", "whitespaceRatio", "weightedScore"):
        assert spread(after, key) <= spread(before, key), f"{key} spread got worse after normalization"

    # And the post-fix spread must meet the fix's own tolerance targets outright.
    assert spread(after, "smallTargetsBelow44px") == 0
    assert spread(after, "alignedElementRatio") <= 0.05
    assert spread(after, "whitespaceRatio") <= 0.03
    assert spread(after, "weightedScore") <= 3
