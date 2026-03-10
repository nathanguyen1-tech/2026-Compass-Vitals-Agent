"""Tests for Clinical Summary Generator — pure Python data transformation."""

import pytest

from app.agents.clinical_summary_generator import (
    _build_hpi,
    _build_oldcarts,
    _build_onset_narrative,
    _build_ros,
    _parse_ros_finding,
    generate_clinical_summary,
)
from app.agents.tools.intake_tracker import IntakeTracker
from app.api.v1.schemas.flow import OLDCARTSDetail


def _make_state(**overrides):
    base = {
        "patient_id": "test-patient",
        "case_id": "test-case",
        "organization_id": "test-org",
        "messages": [],
        "intake_data": {
            "chief_complaint": "abdominal pain",
            "onset": "2 days ago",
            "location": "right lower quadrant",
            "duration": "constant",
            "character": "sharp, stabbing",
            "aggravating": "movement, coughing",
            "alleviating": "lying still",
            "timing": "continuous",
            "severity": "7/10",
            "pmh": "Hypertension, Type 2 Diabetes",
            "medications": "Metformin 500mg BID, Lisinopril 10mg daily",
            "allergies": "Penicillin (rash)",
            "social_family": "Non-smoker, social drinker",
            "ros": {
                "constitutional": "positive: fever 38.5C, malaise; negative: weight loss",
                "gastrointestinal": "positive: nausea, decreased appetite; negative: vomiting, diarrhea",
                "cardiovascular": "negative: chest pain, palpitations",
            },
            "red_flags_found": ["rebound_tenderness", "guarding"],
        },
        "intake_complete": True,
        "intake_tracker": None,
        "is_emergency": False,
        "detected_language": "vi",
        "cultural_expressions": [
            {"original": "nong trong", "medical_meaning": "internal heat sensation"}
        ],
    }
    base.update(overrides)
    return base


def _make_tracker_data(**overrides):
    """Create a serialized IntakeTracker dict."""
    data = {
        "phase": "complete",
        "complaint_category": "abdominal_gi",
        "message_count": 12,
        "cc": "abdominal pain, right side",
        "hpi": {
            "onset": "2 days ago",
            "location": "right lower quadrant",
            "duration": "constant",
            "character": "sharp",
            "aggravating": "movement",
            "alleviating": "lying still",
            "timing": "continuous",
            "severity": "7/10",
        },
        "hpi_additional": {},
        "relevant_oldcarts": ["onset", "location", "duration", "character",
                              "aggravating", "alleviating", "timing", "severity"],
        "red_flags_checked": ["rebound_tenderness", "guarding", "fever"],
        "red_flags_found": ["rebound_tenderness"],
        "red_flag_screening_done": True,
        "ros_systems": {
            "constitutional": "positive: fever; negative: weight loss",
            "gastrointestinal": "positive: nausea; negative: vomiting",
        },
        "pmh": "Hypertension",
        "pmh_complete": True,
        "medications": "Lisinopril 10mg",
        "medications_complete": True,
        "allergies": "NKDA",
        "allergies_complete": True,
        "social_family": "Non-smoker",
        "social_family_complete": True,
        "pmh_prefilled": False,
        "medications_prefilled": False,
        "allergies_prefilled": False,
        "social_family_prefilled": False,
        "summary_confirmed": True,
        "emergency_detected_reason": None,
    }
    data.update(overrides)
    return data


# ── generate_clinical_summary ──


class TestGenerateClinicalSummary:
    def test_returns_clinical_summary_response(self):
        state = _make_state()
        result = generate_clinical_summary(state, "session-1")
        assert result.case_id == "test-case"
        assert result.session_id == "session-1"
        assert result.generated_at

    def test_chief_complaint_from_intake_data(self):
        state = _make_state()
        result = generate_clinical_summary(state, "s1")
        assert result.chief_complaint.complaint == "abdominal pain"

    def test_chief_complaint_from_tracker(self):
        state = _make_state(intake_tracker=_make_tracker_data())
        result = generate_clinical_summary(state, "s1")
        assert result.chief_complaint.complaint == "abdominal pain, right side"

    def test_oldcarts_populated_from_intake_data(self):
        state = _make_state()
        result = generate_clinical_summary(state, "s1")
        assert result.chief_complaint.oldcarts.onset == "2 days ago"
        assert result.chief_complaint.oldcarts.location == "right lower quadrant"
        assert result.chief_complaint.oldcarts.severity == "7/10"

    def test_oldcarts_populated_from_tracker(self):
        state = _make_state(intake_tracker=_make_tracker_data())
        result = generate_clinical_summary(state, "s1")
        assert result.chief_complaint.oldcarts.onset == "2 days ago"
        assert result.chief_complaint.oldcarts.character == "sharp"

    def test_hpi_populated(self):
        state = _make_state()
        result = generate_clinical_summary(state, "s1")
        assert result.hpi.past_medical_history == "Hypertension, Type 2 Diabetes"
        assert result.hpi.current_medications == "Metformin 500mg BID, Lisinopril 10mg daily"
        assert result.hpi.allergies == "Penicillin (rash)"

    def test_hpi_from_tracker(self):
        state = _make_state(intake_tracker=_make_tracker_data())
        result = generate_clinical_summary(state, "s1")
        assert result.hpi.past_medical_history == "Hypertension"
        assert result.hpi.current_medications == "Lisinopril 10mg"
        assert result.hpi.allergies == "NKDA"

    def test_ros_full_with_positives_and_negatives(self):
        state = _make_state()
        result = generate_clinical_summary(state, "s1")
        assert len(result.ros) == 3

        # Find constitutional
        constitutional = next(r for r in result.ros if r.system_name == "constitutional")
        assert "fever 38.5C" in constitutional.positives
        assert "malaise" in constitutional.positives
        assert "weight loss" in constitutional.pertinent_negatives

    def test_ros_from_tracker(self):
        state = _make_state(intake_tracker=_make_tracker_data())
        result = generate_clinical_summary(state, "s1")
        assert len(result.ros) == 2
        gi = next(r for r in result.ros if r.system_name == "gastrointestinal")
        assert "nausea" in gi.positives
        assert "vomiting" in gi.pertinent_negatives

    def test_ros_vi_translation(self):
        state = _make_state()
        result = generate_clinical_summary(state, "s1")
        cv = next(r for r in result.ros if r.system_name == "cardiovascular")
        assert cv.system_name_vi == "Tim mach"

    def test_red_flags(self):
        state = _make_state()
        result = generate_clinical_summary(state, "s1")
        assert "rebound_tenderness" in result.red_flags
        assert "guarding" in result.red_flags

    def test_red_flags_from_tracker(self):
        state = _make_state(intake_tracker=_make_tracker_data())
        result = generate_clinical_summary(state, "s1")
        assert "rebound_tenderness" in result.red_flags

    def test_cultural_expressions(self):
        state = _make_state()
        result = generate_clinical_summary(state, "s1")
        assert len(result.cultural_expressions) == 1
        assert result.cultural_expressions[0]["original"] == "nong trong"

    def test_emergency_flag(self):
        state = _make_state(is_emergency=True)
        result = generate_clinical_summary(state, "s1")
        assert result.is_emergency is True

    def test_detected_language(self):
        state = _make_state(detected_language="en")
        result = generate_clinical_summary(state, "s1")
        assert result.detected_language == "en"

    def test_onset_description_narrative(self):
        state = _make_state()
        result = generate_clinical_summary(state, "s1")
        desc = result.chief_complaint.onset_description
        assert "Onset: 2 days ago" in desc
        assert "Severity: 7/10" in desc

    def test_empty_intake_data(self):
        state = _make_state(intake_data=None)
        result = generate_clinical_summary(state, "s1")
        assert result.chief_complaint.complaint == ""
        assert result.hpi.past_medical_history == ""
        assert result.ros == []

    def test_empty_ros(self):
        state = _make_state(intake_data={"chief_complaint": "headache"})
        result = generate_clinical_summary(state, "s1")
        assert result.ros == []


# ── _build_oldcarts ──


class TestBuildOLDCARTS:
    def test_from_intake_data(self):
        intake = {"onset": "yesterday", "severity": "5/10"}
        result = _build_oldcarts(intake, None)
        assert result.onset == "yesterday"
        assert result.severity == "5/10"
        assert result.location == ""

    def test_from_tracker(self):
        tracker = IntakeTracker()
        tracker.hpi["onset"] = "3 hours ago"
        tracker.hpi["location"] = "left temple"
        result = _build_oldcarts({}, tracker)
        assert result.onset == "3 hours ago"
        assert result.location == "left temple"

    def test_tracker_takes_priority(self):
        intake = {"onset": "from intake"}
        tracker = IntakeTracker()
        tracker.hpi["onset"] = "from tracker"
        result = _build_oldcarts(intake, tracker)
        assert result.onset == "from tracker"


# ── _build_onset_narrative ──


class TestBuildOnsetNarrative:
    def test_full_narrative(self):
        oldcarts = OLDCARTSDetail(
            onset="2 days ago", duration="constant",
            character="sharp", severity="8/10",
        )
        result = _build_onset_narrative(oldcarts)
        assert "Onset: 2 days ago" in result
        assert "Duration: constant" in result
        assert "Character: sharp" in result
        assert "Severity: 8/10" in result

    def test_partial_narrative(self):
        oldcarts = OLDCARTSDetail(onset="yesterday")
        result = _build_onset_narrative(oldcarts)
        assert result == "Onset: yesterday"

    def test_empty_narrative(self):
        oldcarts = OLDCARTSDetail()
        result = _build_onset_narrative(oldcarts)
        assert result == ""


# ── _parse_ros_finding ──


class TestParseROSFinding:
    def test_structured_format(self):
        finding = "positive: cough, fever; negative: chest pain, hemoptysis"
        positives, negatives, past = _parse_ros_finding(finding)
        assert positives == ["cough", "fever"]
        assert negatives == ["chest pain", "hemoptysis"]
        assert past == ""

    def test_with_past_episodes(self):
        finding = "positive: headache; negative: nausea; past: similar migraine 6 months ago"
        positives, negatives, past = _parse_ros_finding(finding)
        assert positives == ["headache"]
        assert negatives == ["nausea"]
        assert past == "similar migraine 6 months ago"

    def test_simple_text(self):
        finding = "patient reports occasional dizziness"
        positives, negatives, past = _parse_ros_finding(finding)
        assert positives == ["patient reports occasional dizziness"]
        assert negatives == []
        assert past == ""

    def test_empty_finding(self):
        positives, negatives, past = _parse_ros_finding("")
        assert positives == []
        assert negatives == []
        assert past == ""

    def test_only_negatives(self):
        finding = "negative: chest pain, dyspnea"
        positives, negatives, past = _parse_ros_finding(finding)
        assert positives == []
        assert negatives == ["chest pain", "dyspnea"]


# ── _build_ros ──


class TestBuildROS:
    def test_from_tracker(self):
        tracker = IntakeTracker()
        tracker.ros_systems = {
            "cardiovascular": "negative: chest pain",
            "respiratory": "positive: cough",
        }
        result = _build_ros({}, tracker)
        assert len(result) == 2
        cv = next(r for r in result if r.system_name == "cardiovascular")
        assert "chest pain" in cv.pertinent_negatives

    def test_from_intake_data(self):
        intake = {"ros": {"neurological": "positive: headache; negative: dizziness"}}
        result = _build_ros(intake, None)
        assert len(result) == 1
        assert result[0].system_name == "neurological"
        assert "headache" in result[0].positives
        assert "dizziness" in result[0].pertinent_negatives

    def test_empty(self):
        result = _build_ros({}, None)
        assert result == []

    def test_vi_translation_applied(self):
        tracker = IntakeTracker()
        tracker.ros_systems = {"respiratory": "positive: cough"}
        result = _build_ros({}, tracker)
        assert result[0].system_name_vi == "Ho hap"

    def test_unknown_system_no_vi(self):
        tracker = IntakeTracker()
        tracker.ros_systems = {"custom_system": "positive: something"}
        result = _build_ros({}, tracker)
        assert result[0].system_name_vi == ""
