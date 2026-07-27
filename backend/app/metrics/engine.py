"""Production-facing adapter around the deterministic metric engine.

`backend/reference/legacy_metric_engine.py` is immutable (never modified —
see CLAUDE.md) and remains importable as the frozen "legacy-v1" baseline.
As of engine version "corrected-v1", this wrapper was wired to
`app.metrics.corrected` for the seven metrics a source-code + manual
ground-truth audit found structurally weak or mislabelled (contrast
sampling, small-target scope, element-count contamination, grouping
chaining, alignment, Fitts's Law input, font-size-diversity outlier
sensitivity). As of "corrected-v2", a per-region diagnostic follow-up found
`analyze_contrast_v2`'s Otsu ink-cluster *mean* still understated contrast
on small, regular-weight text — this wrapper called `analyze_contrast_v3`
instead. As of "corrected-v3", a cross-check against three independent
whole-region estimation methods found `analyze_contrast_v3`'s core-percentile
estimate measurably higher than all three specifically on small anti-aliased
paragraph text, large enough to flip the WCAG AA classification — this
wrapper now calls `analyze_contrast_v4`, which reports a region as a
confirmed pass/fail only when a core estimate and a conservative
whole-cluster estimate agree, and `borderline` otherwise, rather than
picking a side. `analyze_contrast_v2`/`v3` are kept in `app.metrics.corrected`
for reference, unused here. A subsequent independent re-verification of the
element/grid-exclusion fix found it flagged ordinary single-row UI (bottom
nav bars, toolbars, chip rows) as system chrome, and found it was applied
inconsistently — Hick's Law used the grid exclusion, Fitts's Law's
control-like element list did not. `analyze_elements_v2` was revised so the
grid detector requires an actual multi-row, multi-column, tightly-packed
grid (never a single row, however uniform), and now returns one shared
`interactive_targets` list that both Hick's Law and Fitts's Law
consume, so a grid-exclusion fix can never silently apply to only one of
them. A further re-verification found a large/bold heading letter is just
as much a ">=20x20px dark contour" as a real button, and was being counted
as a second interactive target alongside it; `interactive_targets` now also
excludes contours substantially coincident with OCR text ink (unless the
contour is a much-larger container around a text label, i.e. a labeled
button), and `analyze_fitts_full_v2` never fabricates a nearest-neighbor
estimate from a single target. A subsequent audit found the *same design*
exported as screenshots of different raw pixel widths (e.g. 380px vs
328px) produced meaningfully different metrics — OCR word count, contour
count, `estimatedGroupCount`, small-target counts, alignment/whitespace
ratios — purely from export resolution, because most of the deterministic
thresholds inside `app.metrics.corrected` (the 400px-area contour/OCR
floor, the 44px small-target check, the 8px alignment-edge tolerance, the
20px whitespace sampling block, etc.) are fixed in raw image pixels, not
scaled to the image's own resolution. Rather than rescale each of those
thresholds individually (touching contrast/whitespace/keyboard-detector
internals this fix deliberately leaves alone), `MetricEngine.analyze` now
upscales a decoded image narrower than a fixed reference floor width
(`_REFERENCE_ANALYSIS_WIDTH`, aspect ratio preserved) up to it *before*
OCR and every deterministic metric runs, so all of those internal
thresholds implicitly operate at a consistent effective scale for any
image at or below that floor. Deliberately asymmetric: an image already at
or above the floor is left at native resolution, never downscaled, because
an early symmetric version (resizing every image, up or down) downscaled
high-DPI exports enough to shrink small-but-legitimate detail (most
visibly a keyboard key's letter ink) below the fixed area floors Fix 2e's
keyboard detector depends on, silently breaking a previously-working
detection — exactly the kind of regression this pass must not introduce.
This does not, and cannot, fully equalize OCR word count across
resolutions even for images at or below the floor (Tesseract's own
recognition accuracy on the upscaled image is still resolution-dependent —
upscaling cannot fabricate detail that was never captured), which is
disclosed via `raw.resolution.resolutionWarning`/`inputQualityStatus`
rather than silently claimed as fixed; nor does it normalize two exports
that are both already above the floor against each other. See
`app.metrics.corrected`'s module docstring for the full list and
rationale. `analyze_colorfulness` and `analyze_visual_balance` are
unchanged and still imported from the legacy module — the colorfulness
formula is explicitly out of scope for this correction pass.

A later pass (Fix 15, `app.metrics.corrected`) removed every metric
classified Tier 3 ("Problematic") in docs/metrics/reliability-tiers.md
from the engine/API entirely, per explicit user instruction for
research-paper defensibility: `clutter` (`edgeDensity`), `whitespaceAlignment`
(`whitespaceRatio`/`alignmentVariance`/`alignedElementRatio`), and
`elements.hicksLawEstimateMs`/`hicksLawBConstantMs`/`smallTargetsBelow44px`/
`repeatingGridExcludedCount` are no longer computed or returned (the
repeating-grid *filtering* itself is retained — only its standalone count
field is gone). The composite score now uses `weighted_score_v2`/
`WEIGHTS_V2`/`normalize_metrics_v2` (`app.metrics.corrected`), covering
only `contrast`+`textDensity` — see that module's Fix 15 docstring section
for the weight-rescaling rationale. Every report now carries
`metricEngineVersion: "corrected-v4"`.

Runtime pipeline:

    DecodedImage.cv2_image
            |
            v
    Upscale to the analysis reference floor width only if narrower than it
    (aspect ratio preserved; an image at/above the floor is left at native
    resolution); raw.resolution discloses original/analysis resolution,
    the scale factor, and a warning when upscaling is large enough to
    risk detail loss
            |
            v
    Tesseract OCR (exactly once, on the possibly-upscaled image)
            |
            v
    Element detection (analyze_elements_v2)
            |
            +--> group analysis (analyze_groups_v2, all elements)
            |
            +--> Fitts proxy (analyze_fitts_full_v2, interactive targets only)
            |
            v
    Remaining deterministic metrics (contrast v4, text density,
    colorfulness, hue diversity, visual balance)
            |
            v
    Normalization (normalize_metrics_v2: contrast + textDensity only)
            |
            v
    Weighted score (weighted_score_v2)
            |
            v
    Typed, JSON-safe DeterministicMetricResult (metricEngineVersion: "corrected-v4")
"""

from typing import Any

import cv2
import numpy as np
import pytesseract

from app.core.logging import get_logger
from app.images.models import DecodedImage
from app.metrics.corrected import (
    analyze_contrast_v4,
    analyze_elements_v2,
    analyze_fitts_full_v2,
    analyze_groups_v2,
    analyze_hue_diversity,
    analyze_text_density_v2,
    normalize_metrics_v2,
    weighted_score_v2,
)
from app.metrics.exceptions import MetricAnalysisError
from app.metrics.models import DeterministicMetricResult
from app.metrics.serializer import to_json_safe
from app.schemas.common import AnalysisContext
from reference.legacy_metric_engine import (
    analyze_colorfulness,
    analyze_visual_balance,
)

_METRIC_ENGINE_VERSION = "corrected-v4"

# Fix 2f (post-audit follow-up): resolution-driven metric inconsistency.
#
# The same design, exported as screenshots at different raw pixel widths,
# produced different metrics purely from export resolution -- not because
# the design differs. `_REFERENCE_ANALYSIS_WIDTH` is a floor width: any
# decoded image narrower than it is upscaled up to it (aspect ratio
# preserved) before OCR and any deterministic metric runs, so the many
# raw-pixel thresholds scattered through `app.metrics.corrected`
# (contour/OCR area floors, the 44px small-target check, alignment/
# whitespace tolerances, ...) implicitly operate at a consistent effective
# scale for images at or below that floor, without modifying any of those
# thresholds directly. Chosen as a common modern mobile CSS width (roughly
# midway between 320px and 430px, both common device widths) -- not
# derived from either reference screenshot, so it doesn't quietly favor
# one export over the other.
#
# Deliberately asymmetric -- an image AT OR ABOVE the reference width is
# left at its native resolution, never downscaled. An early symmetric
# version (resizing every image, up or down, to exactly the reference
# width) was tried and reverted: downscaling a high-DPI export (e.g. a 3x
# Retina capture, ~1125px wide) down to ~390px shrinks small but
# legitimate detail -- most visibly, a keyboard key's individual letter
# ink -- below the fixed area floors those subsystems already depend on
# (see Fix 2e, `_detect_keyboard_region`, deliberately not touched this
# round), silently breaking a previously-working detection on exactly the
# kind of image it exists to handle. Upscaling a narrow image, by
# contrast, only blurs; it cannot make a feature disappear the way
# downscaling can. This asymmetry means two exports of the same design
# that are BOTH already at or above the reference width, but at different
# native widths (e.g. 500px vs 800px), are NOT normalized against each
# other -- a known, disclosed
# limitation, not a general resolution-invariance guarantee. It does fully
# resolve the reported case (any export at or below the reference floor,
# e.g. 380px vs 328px) and every image in this codebase's own test corpus
# above the floor keeps its native-resolution behavior unchanged,
# including keyboard detection.
#
# The `44px small-target` check inside `app.metrics.corrected` compares
# directly against raw analysis-resolution pixels. WCAG's 44x44 guideline
# is defined in CSS/device-independent pixels, not raw image pixels; this
# reference-width normalization makes that comparison *consistent* across
# differently-sized exports of the same design that are at or below the
# floor, but it does not by itself make raw analysis pixels equal to CSS
# px in an absolute sense -- that would require knowing the screenshot's
# actual device pixel ratio, which is not available here. This is a
# deliberate, disclosed simplification, not a claim that
# `_REFERENCE_ANALYSIS_WIDTH` pixels are CSS px.
#
# Upscaling is not free either: it cannot recover detail (small text, fine
# edges) that was never captured at the original resolution. Disclosed via
# `raw.resolution.resolutionWarning`/`inputQualityStatus`, never silently
# presented as equivalent to native-resolution analysis.
_REFERENCE_ANALYSIS_WIDTH = 390
_UPSCALE_WARNING_SCALE = 1.15  # normalizationScale above this means the original was notably smaller than the reference width

logger = get_logger("lucidui.metrics")


class MetricEngine:
    """Runs the deterministic metrics (corrected-v3) against a decoded image."""

    def analyze(self, image: DecodedImage, context: AnalysisContext) -> DeterministicMetricResult:
        original_cv_image = self._require_valid_image(image)
        cv_image, resolution_info = self._normalize_for_analysis(original_cv_image)
        ocr_data = self._run_ocr(cv_image)

        try:
            elements_meta, elements, interactive_targets = analyze_elements_v2(cv_image, ocr_data)
            # The second return value is a per-region diagnostic list (text,
            # bbox, polarity, core/conservative estimates, status) — not
            # part of the JSON contract, useful for reports/debugging; only
            # the aggregate dict is persisted into `raw["contrast"]`.
            contrast_aggregate, _contrast_regions = analyze_contrast_v4(cv_image, ocr_data)

            raw: dict[str, Any] = {
                "resolution": resolution_info,
                "contrast": contrast_aggregate,
                "elements": elements_meta,
                "groups": analyze_groups_v2(elements, cv_image.shape),
                "textDensity": analyze_text_density_v2(cv_image, ocr_data),
            }

            additional_signals: dict[str, Any] = {
                "colorfulness": analyze_colorfulness(cv_image),
                "hueDiversity": analyze_hue_diversity(cv_image),
                "fittsFullIndexOfDifficulty": analyze_fitts_full_v2(interactive_targets),
                "visualBalance": analyze_visual_balance(cv_image),
            }

            normalized = normalize_metrics_v2(raw)
            score = weighted_score_v2(normalized, context.value)
        except MetricAnalysisError:
            raise
        except Exception as exc:
            raise MetricAnalysisError(f"Deterministic metric computation failed: {exc}") from exc

        return DeterministicMetricResult(
            raw=to_json_safe(raw),
            normalized=to_json_safe(normalized),
            additional_signals=to_json_safe(additional_signals),
            weighted_score=to_json_safe(score),
            metric_engine_version=_METRIC_ENGINE_VERSION,
        )

    @staticmethod
    def _require_valid_image(image: DecodedImage) -> np.ndarray:
        cv_image = image.cv2_image
        if not isinstance(cv_image, np.ndarray) or cv_image.size == 0 or cv_image.ndim < 2:
            raise MetricAnalysisError("Decoded image has no usable pixel data to analyze.")
        return cv_image

    @staticmethod
    def _run_ocr(cv_image: np.ndarray) -> dict:
        try:
            return pytesseract.image_to_data(cv_image, output_type=pytesseract.Output.DICT)
        except Exception as exc:
            logger.warning("OCR execution failed; continuing with empty OCR data: %s", exc)
            return {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}

    @staticmethod
    def _normalize_for_analysis(cv_image: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        """Upscales `cv_image` up to `_REFERENCE_ANALYSIS_WIDTH` (aspect
        ratio preserved) when it is narrower than that floor; an image
        already at or above the reference width is returned unchanged, at
        its native resolution — see the module-level Fix 2f comment for
        why this is deliberately asymmetric (downscaling risks destroying
        small-but-legitimate detail, e.g. keyboard key ink, that other
        subsystems depend on). Every coordinate in the returned
        `DeterministicMetricResult` (bboxes, region extents, ...) is in
        this analysis-resolution space, not the original upload's raw
        pixel space; `originalResolution`/`analysisResolution`/
        `normalizationScale` are returned precisely so a caller that needs
        to draw back onto the original upload can convert (divide by
        `normalizationScale`), rather than the two coordinate spaces being
        silently mixed."""
        original_h, original_w = cv_image.shape[:2]
        scale = _REFERENCE_ANALYSIS_WIDTH / original_w if original_w > 0 else 1.0

        if scale <= 1.0:
            # Already at or above the reference width -- never downscaled.
            resolution_info = {
                "originalResolution": {"width": original_w, "height": original_h},
                "analysisResolution": {"width": original_w, "height": original_h},
                "normalizationScale": 1.0,
                "resolutionWarning": None,
                "inputQualityStatus": "ok",
                "source": (
                    f"the decoded image ({original_w}px wide) is already at or above the "
                    f"{_REFERENCE_ANALYSIS_WIDTH}px analysis reference floor width and is analyzed "
                    "at its native resolution, unchanged -- only images narrower than the floor "
                    "are upscaled (corrected-v1)"
                ),
            }
            return cv_image, resolution_info

        analysis_w = _REFERENCE_ANALYSIS_WIDTH
        analysis_h = max(1, round(original_h * scale))
        resized = cv2.resize(cv_image, (analysis_w, analysis_h), interpolation=cv2.INTER_CUBIC)

        warning: str | None = None
        input_quality_status = "ok"
        if scale >= _UPSCALE_WARNING_SCALE:
            warning = (
                f"original image ({original_w}px wide) is significantly narrower than the "
                f"{_REFERENCE_ANALYSIS_WIDTH}px analysis reference width and was upscaled "
                f"~{scale:.2f}x; upscaling cannot recover detail (small text, fine edges) that "
                "was never captured, so OCR and contour precision may be reduced"
            )
            input_quality_status = "degraded"

        resolution_info = {
            "originalResolution": {"width": original_w, "height": original_h},
            "analysisResolution": {"width": analysis_w, "height": analysis_h},
            "normalizationScale": round(scale, 4),
            "resolutionWarning": warning,
            "inputQualityStatus": input_quality_status,
            "source": (
                f"the decoded image ({original_w}px wide) is narrower than the "
                f"{_REFERENCE_ANALYSIS_WIDTH}px analysis reference floor and is upscaled up to "
                "it (aspect ratio preserved, never downscaled) before OCR and any deterministic "
                "metric runs, so raw-pixel thresholds elsewhere in the pipeline (contour/OCR "
                "area floors, the 44px small-target check, alignment/whitespace tolerances) are "
                "applied at a consistent effective scale relative to that floor; this does not "
                "fully equalize OCR accuracy across resolutions, and images already at or above "
                "the floor are not normalized against each other -- see "
                "resolutionWarning/inputQualityStatus (corrected-v1)"
            ),
        }
        return resized, resolution_info
