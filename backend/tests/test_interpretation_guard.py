"""Tests for the deterministic interpretation guard (app.llm.interpretation_guard).

Pure unit tests against the guard functions directly — no provider, no
network, per CLAUDE.md ("Tests must not require ... LLM providers").
"""

import pytest
import pytesseract

from app.images.models import DecodedImage
from app.llm.interpretation_guard import (
    TAXONOMY,
    filter_observations,
    filter_recommendations,
    filter_summary,
    is_unsupported,
)
from app.llm.models import LLMObservationOutput
from app.metrics.engine import MetricEngine
from app.schemas.common import AnalysisContext


# ---------- 1-2: estimatedGroupCount alone cannot produce a cognitive-load recommendation ----------


def test_group_count_cognitive_load_recommendation_is_dropped() -> None:
    recs = [
        "Considering the estimated group count (raw.groups.estimatedGroupCount), organizing interactive "
        "elements into logical groupings could potentially improve information chunking and reduce "
        "cognitive load for users."
    ]
    kept, dropped = filter_recommendations(recs)
    assert kept == []
    assert dropped is True


def test_group_count_seven_plus_minus_two_recommendation_is_dropped() -> None:
    recs = [
        "With 15 groups detected, well above Miller's 7±2, simplifying the grouping could help.",
        "The estimated group count is far from the ideal of 7 +/- 2, so consider reducing the number of groups.",
    ]
    kept, dropped = filter_recommendations(recs)
    assert kept == []
    assert dropped is True


# ---------- 3: colorfulness alone cannot produce an increase/decrease recommendation ----------


def test_colorfulness_increase_recommendation_is_dropped() -> None:
    recs = [
        "If the content is intended to be more visually engaging, increasing the 'colorfulness' of "
        "certain elements could potentially enhance visual appeal, assuming it aligns with brand and "
        "accessibility goals."
    ]
    kept, dropped = filter_recommendations(recs)
    assert kept == []
    assert dropped is True


# ---------- 4: hue diversity alone cannot produce an increase/decrease recommendation ----------


def test_hue_diversity_increase_recommendation_is_dropped() -> None:
    recs = ["Increasing hue diversity across the interface could enhance visual appeal for users."]
    kept, dropped = filter_recommendations(recs)
    assert kept == []
    assert dropped is True


# ---------- Visual balance quality-judgment language is dropped ----------


def test_visual_balance_good_bad_language_is_dropped() -> None:
    text = (
        "The UI shows good visual balance, with a low asymmetry score suggesting that elements are "
        "distributed evenly across the screen."
    )
    assert is_unsupported(text) is True
    observations = [LLMObservationOutput(id="o1", text=text, metric_evidence=["additionalSignals.visualBalance"])]
    kept, dropped = filter_observations(observations)
    assert kept == []
    assert dropped is True


# ---------- Text density "optimal" language is dropped ----------


def test_text_density_optimal_language_is_dropped() -> None:
    recs = ["The text density is close to optimal, so no change is needed."]
    kept, dropped = filter_recommendations(recs)
    assert kept == []
    assert dropped is True


# ---------- Descriptive metrics may still appear as plain observations ----------


def test_plain_descriptive_observation_about_colorfulness_survives() -> None:
    text = "The colorfulness score was measured at 48.82, reflecting the saturation and area of colored regions."
    assert is_unsupported(text) is False
    observations = [LLMObservationOutput(id="o1", text=text, metric_evidence=["additionalSignals.colorfulness"])]
    kept, dropped = filter_observations(observations)
    assert kept == observations
    assert dropped is False


def test_plain_descriptive_observation_about_group_count_survives() -> None:
    text = "15 groups were estimated from the detected element positions using complete-linkage clustering."
    assert is_unsupported(text) is False


# ---------- Justified contrast recommendations survive unchanged ----------


def test_justified_contrast_recommendation_survives() -> None:
    recs = [
        "Reviewing the specific regions identified as 'below AA threshold' "
        "(raw.contrast.regionsBelowAAThreshold) or 'borderline' (raw.contrast.regionsBorderline) could "
        "ensure that all critical text and interactive elements meet or exceed WCAG AA contrast "
        "guidelines, potentially improving accessibility for users with visual impairments.",
    ]
    kept, dropped = filter_recommendations(recs)
    assert kept == recs
    assert dropped is False


def test_mixed_recommendations_keep_only_the_justified_one() -> None:
    justified = "Reviewing regions below the AA contrast threshold could improve accessibility."
    unjustified_group = "Reducing the estimated group count could reduce cognitive load."
    unjustified_color = "Increasing colorfulness could make the interface more engaging."
    kept, dropped = filter_recommendations([justified, unjustified_group, unjustified_color])
    assert kept == [justified]
    assert dropped is True


# ---------- Summary sentences are filtered independently ----------


def test_summary_drops_only_the_offending_sentence() -> None:
    summary = (
        "This UI has a high overall contrast ratio, with most text estimated to be above accessibility "
        "guidelines. The visual balance appears good, with low asymmetry."
    )
    filtered, dropped = filter_summary(summary)
    assert dropped is True
    assert "contrast ratio" in filtered
    assert "good" not in (filtered or "")


def test_summary_with_no_violations_is_returned_unchanged() -> None:
    summary = "This UI has a high overall contrast ratio, estimated well above accessibility guidelines."
    filtered, dropped = filter_summary(summary)
    assert filtered == summary
    assert dropped is False


def test_summary_none_and_empty_pass_through() -> None:
    assert filter_summary(None) == (None, False)
    assert filter_summary("") == ("", False)


# ---------- Taxonomy completeness: every retained raw/additionalSignals key is classified,          ----------
# ---------- and no removed Tier 3 field name is present (docs/metrics/reliability-tiers.md)          ----------


@pytest.fixture(autouse=True)
def _empty_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    empty = {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}
    monkeypatch.setattr(pytesseract, "image_to_data", lambda *args, **kwargs: empty)


def test_taxonomy_covers_every_key_metric_engine_actually_produces(decoded_image: DecodedImage) -> None:
    """Runs the real `MetricEngine` (not a hand-maintained key list) so this
    test breaks the moment a future metric change adds an unclassified
    field, per task requirement F.6/F.9."""
    result = MetricEngine().analyze(decoded_image, AnalysisContext.GENERAL)
    raw_keys = set(result.raw) - {"resolution"}  # resolution carries no interpretable content
    additional_keys = set(result.additional_signals)

    for key in raw_keys | additional_keys:
        assert key in TAXONOMY, f"{key} has no interpretation-taxonomy classification"
    assert set(TAXONOMY) == raw_keys | additional_keys


def test_taxonomy_does_not_reintroduce_removed_tier_3_fields() -> None:
    removed = {"clutter", "whitespaceAlignment"}
    assert not (removed & set(TAXONOMY))
