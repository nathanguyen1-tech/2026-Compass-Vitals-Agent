"""Tests for Clinical Scoring Engine — rule-based clinical decision scores."""

from app.agents.tools.clinical_scoring import (
    calculate_heart_score_proxy,
    calculate_phq2_score,
    calculate_qsofa_proxy,
    calculate_score,
    calculate_wells_pe_proxy,
    get_applicable_scores,
)
from app.agents.tools.intake_tracker import IntakeTracker


def _make_tracker(**kwargs) -> IntakeTracker:
    """Create a tracker with specified fields."""
    tracker = IntakeTracker()
    for k, v in kwargs.items():
        setattr(tracker, k, v)
    return tracker


class TestHeartScoreProxy:
    def test_typical_angina_high_risk(self):
        tracker = _make_tracker(
            cc="chest pressure and tightness",
            hpi={"onset": "1 hour ago", "character": "heavy pressure, squeezing",
                 "severity": "8/10", "location": "center chest",
                 "duration": None, "aggravating": None, "alleviating": None, "timing": None},
            pmh="diabetes, hypertension, prior MI",
            medications="metformin, lisinopril, aspirin",
            social_family="father had heart attack at 50, smoker",
            active_symptoms=["shortness of breath", "sweating"],
        )
        result = calculate_heart_score_proxy(tracker)
        assert result["risk"] == "high"
        assert result["score"] >= 5

    def test_atypical_no_risk_factors_low(self):
        tracker = _make_tracker(
            cc="sharp stabbing chest pain",
            hpi={"onset": "2 days ago", "character": "sharp, stabbing",
                 "severity": "3/10", "location": "right side",
                 "duration": None, "aggravating": None, "alleviating": None, "timing": None},
            pmh="",
            medications="",
            social_family="",
            active_symptoms=[],
        )
        result = calculate_heart_score_proxy(tracker)
        assert result["risk"] == "low"
        assert result["score"] <= 2

    def test_moderate_risk_some_factors(self):
        tracker = _make_tracker(
            cc="chest discomfort",
            hpi={"onset": "yesterday", "character": "aching",
                 "severity": "5/10", "location": "left chest",
                 "duration": None, "aggravating": None, "alleviating": None, "timing": None},
            pmh="hypertension",
            medications="amlodipine",
            social_family="",
            active_symptoms=[],
        )
        result = calculate_heart_score_proxy(tracker)
        assert result["risk"] in ("low", "moderate")

    def test_returns_required_keys(self):
        tracker = _make_tracker(
            cc="chest pain",
            hpi={f: None for f in ["onset", "location", "duration", "character",
                                    "aggravating", "alleviating", "timing", "severity"]},
        )
        result = calculate_heart_score_proxy(tracker)
        assert "score" in result
        assert "risk" in result
        assert "components" in result
        assert "max_score" in result


class TestWellsPEProxy:
    def test_high_risk_pe(self):
        tracker = _make_tracker(
            cc="chest pain and shortness of breath",
            hpi={"onset": "sudden", "character": "pleuritic",
                 "severity": "7/10", "location": "right chest",
                 "duration": None, "aggravating": None, "alleviating": None, "timing": None},
            pmh="cancer, recent surgery",
            active_symptoms=["leg swelling", "shortness of breath", "racing heart"],
        )
        result = calculate_wells_pe_proxy(tracker)
        assert result["risk"] == "high"

    def test_low_risk_no_pe_signs(self):
        tracker = _make_tracker(
            cc="mild cough",
            hpi={f: None for f in ["onset", "location", "duration", "character",
                                    "aggravating", "alleviating", "timing", "severity"]},
            active_symptoms=[],
        )
        result = calculate_wells_pe_proxy(tracker)
        assert result["risk"] == "low"
        assert result["score"] < 2


class TestQsofaProxy:
    def test_high_risk_sepsis(self):
        tracker = _make_tracker(
            cc="high fever and confusion",
            hpi={"onset": "today", "character": "confused",
                 "severity": None, "location": None,
                 "duration": None, "aggravating": None, "alleviating": None, "timing": None},
            active_symptoms=["confused", "rapid breathing", "dizzy"],
        )
        result = calculate_qsofa_proxy(tracker)
        assert result["risk"] == "high"
        assert result["score"] >= 2

    def test_low_risk_no_sepsis_signs(self):
        tracker = _make_tracker(
            cc="sore throat",
            hpi={f: None for f in ["onset", "location", "duration", "character",
                                    "aggravating", "alleviating", "timing", "severity"]},
            active_symptoms=[],
        )
        result = calculate_qsofa_proxy(tracker)
        assert result["risk"] == "low"
        assert result["score"] == 0


class TestPHQ2Score:
    def test_positive_screening(self):
        result = calculate_phq2_score({"interest": 2, "mood": 2})
        assert result["positive"] is True
        assert result["score"] == 4
        assert result["risk"] == "high"

    def test_negative_screening(self):
        result = calculate_phq2_score({"interest": 0, "mood": 1})
        assert result["positive"] is False
        assert result["score"] == 1
        assert result["risk"] == "low"

    def test_borderline(self):
        result = calculate_phq2_score({"interest": 1, "mood": 2})
        assert result["positive"] is True
        assert result["score"] == 3

    def test_clamps_values(self):
        result = calculate_phq2_score({"interest": 10, "mood": -5})
        assert result["score"] == 3  # clamped to 3 + 0

    def test_missing_keys(self):
        result = calculate_phq2_score({})
        assert result["score"] == 0


class TestGetApplicableScores:
    def test_chest_pain_includes_heart(self):
        scores = get_applicable_scores("chest_pain")
        assert "heart" in scores
        assert "wells_pe" in scores

    def test_mental_health_includes_phq2(self):
        scores = get_applicable_scores("mental_health")
        assert "phq2" in scores

    def test_general_includes_qsofa(self):
        scores = get_applicable_scores("uri_cough")
        assert "qsofa" in scores

    def test_none_category(self):
        scores = get_applicable_scores(None)
        assert "qsofa" in scores


class TestCalculateScore:
    def test_heart_score(self):
        tracker = _make_tracker(
            cc="chest pain",
            hpi={f: None for f in ["onset", "location", "duration", "character",
                                    "aggravating", "alleviating", "timing", "severity"]},
        )
        result = calculate_score("heart", tracker)
        assert "score" in result
        assert "risk" in result

    def test_unknown_score_returns_empty(self):
        tracker = _make_tracker(
            cc="test",
            hpi={f: None for f in ["onset", "location", "duration", "character",
                                    "aggravating", "alleviating", "timing", "severity"]},
        )
        result = calculate_score("unknown_score_type", tracker)
        assert result == {}
