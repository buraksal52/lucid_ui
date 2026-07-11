"""Production-facing adapter around the validated legacy metric engine.

Wraps `backend/reference/legacy_metric_engine.py` (immutable scientific
logic, never modified — see CLAUDE.md) so it can run against an in-memory
`DecodedImage` (Phase 2A) instead of a file path. Composes the legacy
module's lower-level functions directly in their original order and data
dependencies; never calls the legacy `analyze_image(path)`, which uses
`cv2.imread()` and requires a filesystem path.

Runtime pipeline:

    DecodedImage.cv2_image
            |
            v
    Tesseract OCR (exactly once)
            |
            v
    Element detection (analyze_elements)
            |
            +--> group analysis (analyze_groups)
            |
            +--> Fitts proxy (analyze_fitts_full)
            |
            v
    Remaining deterministic metrics (contrast, clutter, text density,
    whitespace/alignment, colorfulness, visual balance)
            |
            v
    Normalization (normalize_metrics)
            |
            v
    Weighted score (weighted_score)
            |
            v
    Typed, JSON-safe DeterministicMetricResult
"""

from typing import Any

import numpy as np
import pytesseract

from app.images.models import DecodedImage
from app.metrics.exceptions import MetricAnalysisError, OCRExecutionError
from app.metrics.models import DeterministicMetricResult
from app.metrics.serializer import to_json_safe
from app.schemas.common import AnalysisContext
from reference.legacy_metric_engine import (
    analyze_clutter,
    analyze_colorfulness,
    analyze_contrast,
    analyze_elements,
    analyze_fitts_full,
    analyze_groups,
    analyze_text_density,
    analyze_visual_balance,
    analyze_whitespace_alignment,
    normalize_metrics,
    weighted_score,
)


class MetricEngine:
    """Runs the validated legacy deterministic metrics against a decoded image."""

    def analyze(self, image: DecodedImage, context: AnalysisContext) -> DeterministicMetricResult:
        cv_image = self._require_valid_image(image)
        ocr_data = self._run_ocr(cv_image)

        try:
            elements_meta, elements = analyze_elements(cv_image, ocr_data)

            raw: dict[str, Any] = {
                "contrast": analyze_contrast(cv_image, ocr_data),
                "clutter": analyze_clutter(cv_image),
                "elements": elements_meta,
                "groups": analyze_groups(elements, cv_image.shape),
                "textDensity": analyze_text_density(cv_image, ocr_data),
                "whitespaceAlignment": analyze_whitespace_alignment(cv_image, elements),
            }

            additional_signals: dict[str, Any] = {
                "colorfulness": analyze_colorfulness(cv_image),
                "fittsFullIndexOfDifficulty": analyze_fitts_full(elements),
                "visualBalance": analyze_visual_balance(cv_image),
            }

            normalized = normalize_metrics(raw)
            score = weighted_score(normalized, context.value)
        except MetricAnalysisError:
            raise
        except Exception as exc:
            raise MetricAnalysisError(f"Deterministic metric computation failed: {exc}") from exc

        return DeterministicMetricResult(
            raw=to_json_safe(raw),
            normalized=to_json_safe(normalized),
            additional_signals=to_json_safe(additional_signals),
            weighted_score=to_json_safe(score),
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
        except OCRExecutionError:
            raise
        except Exception as exc:
            raise OCRExecutionError("OCR execution failed while analyzing the image.") from exc
