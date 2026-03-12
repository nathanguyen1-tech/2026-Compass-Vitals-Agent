"""Tests for Intake Tracker — progress tracking, serialization, completeness."""

from app.agents.tools.intake_tracker import IntakeTracker, parse_intake_markers


class TestInitialization:
    def test_fresh_tracker_has_greeting_phase(self):
        t = IntakeTracker()
        assert t.phase == "greeting"

    def test_fresh_tracker_has_empty_hpi(self):
        t = IntakeTracker()
        assert all(v is None for v in t.hpi.values())

    def test_fresh_tracker_no_cc(self):
        t = IntakeTracker()
        assert t.cc is None

    def test_fresh_tracker_zero_completeness(self):
        t = IntakeTracker()
        assert t.get_completeness_score() == 0.0


class TestPreExistingHistory:
    def test_prefills_pmh(self):
        t = IntakeTracker(existing_history={"pmh": "Hypertension, Type 2 DM"})
        assert t.pmh_complete is True
        assert t.pmh_prefilled is True
        assert t.pmh == "Hypertension, Type 2 DM"

    def test_prefills_medications(self):
        t = IntakeTracker(existing_history={"medications": "Metformin 500mg, Lisinopril 10mg"})
        assert t.medications_complete is True
        assert t.medications_prefilled is True

    def test_prefills_allergies(self):
        t = IntakeTracker(existing_history={"allergies": "Penicillin - hives"})
        assert t.allergies_complete is True
        assert t.allergies_prefilled is True

    def test_prefills_social_family(self):
        t = IntakeTracker(existing_history={"social_family": "Non-smoker, social drinker"})
        assert t.social_family_complete is True
        assert t.social_family_prefilled is True

    def test_prefilled_sections_listed(self):
        t = IntakeTracker(existing_history={
            "pmh": "HTN", "medications": "Lisinopril", "allergies": "NKDA"
        })
        prefilled = t.get_prefilled_sections()
        assert "pmh" in prefilled
        assert "medications" in prefilled
        assert "allergies" in prefilled

    def test_prefilled_sections_count_as_complete(self):
        t = IntakeTracker(existing_history={
            "pmh": "HTN", "medications": "Lisinopril", "allergies": "NKDA"
        })
        completed = t.get_completed_sections()
        assert "pmh" in completed
        assert "medications" in completed
        assert "allergies" in completed

    def test_completeness_score_with_prefilled(self):
        t = IntakeTracker(existing_history={
            "pmh": "HTN", "medications": "Lisinopril", "allergies": "NKDA"
        })
        # PMH=8% + Meds=8% + Allergies=8% = 24%
        assert t.get_completeness_score() == 0.24


class TestSerialization:
    def test_round_trip(self):
        t = IntakeTracker()
        t.phase = "hpi"
        t.cc = "headache"
        t.complaint_category = "headache"
        t.hpi["onset"] = "3 days ago"
        t.hpi["severity"] = "7/10"

        data = t.to_dict()
        t2 = IntakeTracker(data=data)

        assert t2.phase == "hpi"
        assert t2.cc == "headache"
        assert t2.complaint_category == "headache"
        assert t2.hpi["onset"] == "3 days ago"
        assert t2.hpi["severity"] == "7/10"
        assert t2.hpi["location"] is None

    def test_round_trip_with_prefilled(self):
        t = IntakeTracker(existing_history={"pmh": "DM2"})
        data = t.to_dict()
        t2 = IntakeTracker(data=data)
        assert t2.pmh_prefilled is True
        assert t2.pmh_complete is True
        assert t2.pmh == "DM2"

    def test_round_trip_with_ros(self):
        t = IntakeTracker()
        t.ros_systems["cardiovascular"] = "negative"
        t.ros_systems["neurological"] = "headaches, no focal deficits"
        data = t.to_dict()
        t2 = IntakeTracker(data=data)
        assert t2.ros_systems["cardiovascular"] == "negative"
        assert len(t2.ros_systems) == 2


class TestFieldUpdates:
    def test_update_cc(self):
        t = IntakeTracker()
        t.update_field("cc", "severe headache")
        assert t.cc == "severe headache"

    def test_update_oldcarts_field(self):
        t = IntakeTracker()
        t.update_field("onset", "2 days ago")
        assert t.hpi["onset"] == "2 days ago"

    def test_update_hpi_additional(self):
        t = IntakeTracker()
        t.update_field("hpi_home_bp", "140/90")
        assert t.hpi_additional["hpi_home_bp"] == "140/90"

    def test_update_ros(self):
        t = IntakeTracker()
        t.update_field("ros_cardiovascular", "negative")
        assert t.ros_systems["cardiovascular"] == "negative"

    def test_update_red_flag_check_negative(self):
        t = IntakeTracker()
        t.update_field("red_flag_check", "acs_active:negative")
        assert "acs_active" in t.red_flags_checked
        assert "acs_active" not in t.red_flags_found

    def test_update_red_flag_check_positive(self):
        t = IntakeTracker()
        t.update_field("red_flag_check", "acs_active:positive")
        assert "acs_active" in t.red_flags_checked
        assert "acs_active" in t.red_flags_found

    def test_update_pmh(self):
        t = IntakeTracker()
        t.update_field("pmh", "Hypertension, DM2")
        assert t.pmh_complete is True
        assert t.pmh == "Hypertension, DM2"

    def test_update_medications(self):
        t = IntakeTracker()
        t.update_field("medications", "Metformin 500mg BD")
        assert t.medications_complete is True

    def test_update_allergies(self):
        t = IntakeTracker()
        t.update_field("allergies", "NKDA")
        assert t.allergies_complete is True

    def test_update_social_family(self):
        t = IntakeTracker()
        t.update_field("social_family", "Non-smoker, teacher")
        assert t.social_family_complete is True

    def test_update_phase(self):
        t = IntakeTracker()
        t.update_field("phase", "hpi")
        assert t.phase == "hpi"

    def test_update_phase_invalid_ignored(self):
        t = IntakeTracker()
        t.update_field("phase", "invalid_phase")
        assert t.phase == "greeting"

    def test_update_summary_confirmed(self):
        t = IntakeTracker()
        t.update_field("summary_confirmed", "true")
        assert t.summary_confirmed is True


class TestCompleteness:
    def test_hpi_coverage_empty(self):
        t = IntakeTracker()
        filled, total = t.get_hpi_coverage()
        assert filled == 0
        assert total == 8

    def test_hpi_coverage_partial(self):
        t = IntakeTracker()
        t.hpi["onset"] = "3 days"
        t.hpi["location"] = "frontal"
        t.hpi["severity"] = "7"
        filled, total = t.get_hpi_coverage()
        assert filled == 3
        assert total == 8

    def test_missing_hpi_fields(self):
        t = IntakeTracker()
        t.hpi["onset"] = "3 days"
        t.hpi["severity"] = "7"
        missing = t.get_missing_hpi_fields()
        assert "onset" not in missing
        assert "severity" not in missing
        assert "location" in missing
        assert len(missing) == 6

    def test_minimum_complete_false_when_missing(self):
        t = IntakeTracker()
        assert t.is_minimum_complete() is False

    def test_minimum_complete_true(self):
        t = IntakeTracker()
        t.age = "45"
        t.gender = "male"
        t.cc = "headache"
        # Fill 6 OLDCARTS
        for field in ["onset", "location", "duration", "character", "aggravating", "severity"]:
            t.hpi[field] = "some value"
        # 2 ROS
        t.ros_systems["neurological"] = "positive"
        t.ros_systems["ophthalmologic"] = "negative"
        # PMH, meds, allergies
        t.pmh_complete = True
        t.medications_complete = True
        t.allergies_complete = True
        # Red flag screening
        t.red_flags_checked.append("thunderclap_headache")
        assert t.is_minimum_complete() is True

    def test_minimum_complete_false_without_demographics(self):
        t = IntakeTracker()
        t.cc = "headache"
        for field in ["onset", "location", "duration", "character", "aggravating", "severity"]:
            t.hpi[field] = "some value"
        t.ros_systems["neurological"] = "positive"
        t.ros_systems["ophthalmologic"] = "negative"
        t.pmh_complete = True
        t.medications_complete = True
        t.allergies_complete = True
        t.red_flags_checked.append("thunderclap_headache")
        # Missing age and gender
        assert t.is_minimum_complete() is False

    def test_missing_sections(self):
        t = IntakeTracker()
        missing = t.get_missing_sections()
        assert "cc" in missing
        assert "hpi" in missing
        assert "pmh" in missing

    def test_completeness_score_full(self):
        t = IntakeTracker()
        t.age = "45"
        t.gender = "male"
        t.cc = "headache"
        for field in ["onset", "location", "duration", "character",
                       "aggravating", "alleviating", "timing", "severity"]:
            t.hpi[field] = "value"
        t.ros_systems["neuro"] = "pos"
        t.ros_systems["ent"] = "neg"
        t.pmh_complete = True
        t.medications_complete = True
        t.allergies_complete = True
        t.social_family_complete = True
        t.red_flag_screening_done = True
        score = t.get_completeness_score()
        assert score == 1.0


class TestProgress:
    def test_progress_just_started(self):
        t = IntakeTracker()
        desc = t.get_progress_description("vi")
        assert "bat dau" in desc

    def test_progress_halfway(self):
        t = IntakeTracker()
        t.cc = "headache"
        t.red_flag_screening_done = True
        for field in ["onset", "location", "duration", "character"]:
            t.hpi[field] = "value"
        t.pmh_complete = True
        desc = t.get_progress_description("vi")
        assert "nua" in desc or "phan tu" in desc

    def test_progress_english(self):
        t = IntakeTracker()
        desc = t.get_progress_description("en")
        assert "started" in desc.lower()

    def test_suggest_next_phase_cc(self):
        t = IntakeTracker()
        assert t.suggest_next_phase() == "cc"

    def test_suggest_next_phase_red_flags(self):
        t = IntakeTracker()
        t.cc = "headache"
        assert t.suggest_next_phase() == "red_flag_screening"

    def test_suggest_next_phase_hpi(self):
        t = IntakeTracker()
        t.cc = "headache"
        t.red_flag_screening_done = True
        assert t.suggest_next_phase() == "hpi"


class TestIntakeDataExport:
    def test_empty_export(self):
        t = IntakeTracker()
        data = t.to_intake_data()
        assert data == {}

    def test_export_with_cc_and_hpi(self):
        t = IntakeTracker()
        t.cc = "headache"
        t.complaint_category = "headache"
        t.hpi["onset"] = "3 days ago"
        t.hpi["severity"] = "7/10"
        data = t.to_intake_data()
        assert data["chief_complaint"] == "headache"
        assert data["complaint_category"] == "headache"
        assert data["onset"] == "3 days ago"
        assert data["severity"] == "7/10"
        assert "location" not in data  # Not filled

    def test_export_with_ros(self):
        t = IntakeTracker()
        t.ros_systems["cardiovascular"] = "negative"
        data = t.to_intake_data()
        assert data["ros"]["cardiovascular"] == "negative"

    def test_export_with_red_flags(self):
        t = IntakeTracker()
        t.red_flags_found.append("acs_active")
        data = t.to_intake_data()
        assert "acs_active" in data["red_flags_found"]


class TestMarkerParsing:
    def test_parses_single_marker(self):
        text = "I see, your headache started 3 days ago. [INTAKE:onset=3 days ago]"
        clean, fields = parse_intake_markers(text)
        assert "INTAKE" not in clean
        assert fields["onset"] == "3 days ago"
        assert "I see" in clean

    def test_parses_multiple_markers(self):
        text = "Got it. [INTAKE:onset=2 days] [INTAKE:severity=7]"
        clean, fields = parse_intake_markers(text)
        assert fields["onset"] == "2 days"
        assert fields["severity"] == "7"
        assert "INTAKE" not in clean

    def test_parses_phase_marker(self):
        text = "Let me ask about your medical history. [INTAKE:phase=pmh]"
        clean, fields = parse_intake_markers(text)
        assert fields["phase"] == "pmh"

    def test_parses_ros_marker(self):
        text = "Thank you. [INTAKE:ros_cardiovascular=negative]"
        clean, fields = parse_intake_markers(text)
        assert fields["ros_cardiovascular"] == "negative"

    def test_parses_red_flag_check(self):
        text = "OK. [INTAKE:red_flag_check=acs_active:negative]"
        clean, fields = parse_intake_markers(text)
        assert fields["red_flag_check"] == "acs_active:negative"

    def test_no_markers_returns_original(self):
        text = "How are you feeling today?"
        clean, fields = parse_intake_markers(text)
        assert clean == text
        assert fields == {}

    def test_strips_extra_spaces(self):
        text = "OK.  [INTAKE:cc=headache]  How long?"
        clean, fields = parse_intake_markers(text)
        assert "  " not in clean
        assert fields["cc"] == "headache"


class TestRelevantOldcarts:
    def test_default_is_all_eight(self):
        t = IntakeTracker()
        assert len(t.relevant_oldcarts) == 8

    def test_set_relevant_oldcarts(self):
        t = IntakeTracker()
        t.set_relevant_oldcarts(["onset", "duration", "severity"])
        assert t.relevant_oldcarts == ["onset", "duration", "severity"]

    def test_set_relevant_filters_invalid(self):
        t = IntakeTracker()
        t.set_relevant_oldcarts(["onset", "invalid_field", "severity"])
        assert "invalid_field" not in t.relevant_oldcarts
        assert len(t.relevant_oldcarts) == 2

    def test_set_relevant_empty_falls_back(self):
        t = IntakeTracker()
        t.set_relevant_oldcarts([])
        assert len(t.relevant_oldcarts) == 8

    def test_missing_fields_only_relevant(self):
        t = IntakeTracker()
        t.set_relevant_oldcarts(["onset", "duration", "severity"])
        t.hpi["onset"] = "3 days ago"
        missing = t.get_missing_hpi_fields()
        assert "onset" not in missing
        assert "duration" in missing
        assert "severity" in missing
        assert "location" not in missing  # not relevant
        assert len(missing) == 2

    def test_hpi_coverage_respects_relevant(self):
        t = IntakeTracker()
        t.set_relevant_oldcarts(["onset", "duration", "severity"])
        t.hpi["onset"] = "3 days"
        filled, total = t.get_hpi_coverage()
        assert filled == 1
        assert total == 3

    def test_min_oldcarts_required_all_eight(self):
        t = IntakeTracker()
        assert t.get_min_oldcarts_required() == 6

    def test_min_oldcarts_required_four(self):
        t = IntakeTracker()
        t.set_relevant_oldcarts(["onset", "duration", "aggravating", "severity"])
        assert t.get_min_oldcarts_required() == 3

    def test_min_oldcarts_required_six(self):
        t = IntakeTracker()
        t.set_relevant_oldcarts(["onset", "duration", "character", "aggravating", "timing", "severity"])
        assert t.get_min_oldcarts_required() == 5

    def test_minimum_complete_with_reduced_fields(self):
        """Hypertension-like: 4 relevant fields, need 3."""
        t = IntakeTracker()
        t.age = "55"
        t.gender = "female"
        t.set_relevant_oldcarts(["onset", "duration", "aggravating", "severity"])
        t.cc = "high blood pressure"
        t.hpi["onset"] = "2 weeks"
        t.hpi["duration"] = "constant"
        t.hpi["severity"] = "160/100"
        t.ros_systems["cardiovascular"] = "negative"
        t.ros_systems["neurological"] = "negative"
        t.pmh_complete = True
        t.medications_complete = True
        t.allergies_complete = True
        t.red_flags_checked.append("hypertensive_emergency")
        assert t.is_minimum_complete() is True

    def test_serialization_preserves_relevant(self):
        t = IntakeTracker()
        t.set_relevant_oldcarts(["onset", "severity"])
        data = t.to_dict()
        t2 = IntakeTracker(data=data)
        assert t2.relevant_oldcarts == ["onset", "severity"]

    def test_completeness_score_with_reduced_fields(self):
        t = IntakeTracker()
        t.set_relevant_oldcarts(["onset", "duration", "aggravating", "severity"])
        t.hpi["onset"] = "val"
        t.hpi["duration"] = "val"
        # HPI: 0.30 * (2/4) = 0.15
        assert t.get_completeness_score() == 0.15


class TestSuspectedEmergency:
    """Tests for suspected_emergency state and emergency confirmation markers."""

    def test_fresh_tracker_no_suspected(self):
        t = IntakeTracker()
        assert t.suspected_emergency is None

    def test_emergency_suspected_marker(self):
        t = IntakeTracker()
        t.update_field("emergency_suspected", "chest_pain_active")
        assert t.suspected_emergency is not None
        assert t.suspected_emergency["reason"] == "chest_pain_active"
        assert t.suspected_emergency["confirmation_questions_asked"] == 0
        assert t.suspected_emergency["source"] == "llm"

    def test_emergency_confirmed_marker(self):
        t = IntakeTracker()
        t.update_field("emergency_suspected", "chest_pain_active")
        t.update_field("emergency_confirmed", "severe_acs_confirmed")
        assert t.emergency_detected_reason == "severe_acs_confirmed"

    def test_emergency_cleared_marker(self):
        t = IntakeTracker()
        t.update_field("emergency_suspected", "chest_pain_active")
        assert t.suspected_emergency is not None
        t.update_field("emergency_cleared", "mild_resolved")
        assert t.suspected_emergency is None

    def test_serialization_preserves_suspected(self):
        t = IntakeTracker()
        t.suspected_emergency = {
            "reason": "test_reason",
            "confirmation_questions_asked": 1,
            "source": "llm",
        }
        data = t.to_dict()
        t2 = IntakeTracker(data=data)
        assert t2.suspected_emergency is not None
        assert t2.suspected_emergency["reason"] == "test_reason"
        assert t2.suspected_emergency["confirmation_questions_asked"] == 1

    def test_serialization_none_suspected(self):
        t = IntakeTracker()
        data = t.to_dict()
        t2 = IntakeTracker(data=data)
        assert t2.suspected_emergency is None


class TestRiskLevelTracking:
    """Tests for continuous risk assessment tracking."""

    def test_default_risk_level(self):
        t = IntakeTracker()
        assert t.risk_level == "low"
        assert t.risk_history == []
        assert t.risk_reasoning == ""

    def test_update_risk_level(self):
        t = IntakeTracker()
        t.update_field("risk_level", "moderate")
        assert t.risk_level == "moderate"
        assert t.risk_history == ["moderate"]

    def test_update_risk_reasoning(self):
        t = IntakeTracker()
        t.update_field("risk_reasoning", "chest pain reported, need acuity assessment")
        assert t.risk_reasoning == "chest pain reported, need acuity assessment"

    def test_risk_history_accumulates(self):
        t = IntakeTracker()
        t.update_field("risk_level", "low")
        t.update_field("risk_level", "moderate")
        t.update_field("risk_level", "high")
        assert t.risk_history == ["low", "moderate", "high"]
        assert t.risk_level == "high"

    def test_invalid_risk_level_ignored(self):
        t = IntakeTracker()
        t.update_field("risk_level", "invalid_value")
        assert t.risk_level == "low"  # unchanged
        assert t.risk_history == []  # not added

    def test_risk_level_case_insensitive(self):
        t = IntakeTracker()
        t.update_field("risk_level", "HIGH")
        assert t.risk_level == "high"
        t.update_field("risk_level", "Critical")
        assert t.risk_level == "critical"

    def test_serialization_preserves_risk(self):
        t = IntakeTracker()
        t.update_field("risk_level", "high")
        t.update_field("risk_level", "critical")
        t.update_field("risk_reasoning", "active chest pain with dyspnea")
        data = t.to_dict()
        t2 = IntakeTracker(data=data)
        assert t2.risk_level == "critical"
        assert t2.risk_history == ["high", "critical"]
        assert t2.risk_reasoning == "active chest pain with dyspnea"

    def test_should_auto_escalate_false_with_no_history(self):
        t = IntakeTracker()
        assert t.should_auto_escalate() is False

    def test_should_auto_escalate_false_with_one_high(self):
        t = IntakeTracker()
        t.update_field("risk_level", "high")
        assert t.should_auto_escalate() is False

    def test_should_auto_escalate_true_with_two_high(self):
        t = IntakeTracker()
        t.update_field("risk_level", "high")
        t.update_field("risk_level", "high")
        assert t.should_auto_escalate() is True

    def test_should_auto_escalate_true_with_high_then_critical(self):
        t = IntakeTracker()
        t.update_field("risk_level", "high")
        t.update_field("risk_level", "critical")
        assert t.should_auto_escalate() is True

    def test_should_auto_escalate_false_after_drop(self):
        t = IntakeTracker()
        t.update_field("risk_level", "high")
        t.update_field("risk_level", "high")
        t.update_field("risk_level", "moderate")  # dropped
        assert t.should_auto_escalate() is False

    def test_should_auto_escalate_false_with_low_moderate(self):
        t = IntakeTracker()
        t.update_field("risk_level", "low")
        t.update_field("risk_level", "moderate")
        assert t.should_auto_escalate() is False


class TestDemographics:
    """Tests for age and gender tracking."""

    def test_fresh_tracker_no_demographics(self):
        t = IntakeTracker()
        assert t.age is None
        assert t.gender is None

    def test_update_age(self):
        t = IntakeTracker()
        t.update_field("age", "45")
        assert t.age == "45"

    def test_update_gender(self):
        t = IntakeTracker()
        t.update_field("gender", "male")
        assert t.gender == "male"

    def test_empty_age_ignored(self):
        t = IntakeTracker()
        t.update_field("age", "")
        assert t.age is None

    def test_whitespace_age_ignored(self):
        t = IntakeTracker()
        t.update_field("age", "   ")
        assert t.age is None

    def test_empty_gender_ignored(self):
        t = IntakeTracker()
        t.update_field("gender", "")
        assert t.gender is None

    def test_age_stripped(self):
        t = IntakeTracker()
        t.update_field("age", "  45  ")
        assert t.age == "45"

    def test_gender_stripped(self):
        t = IntakeTracker()
        t.update_field("gender", "  female  ")
        assert t.gender == "female"

    def test_serialization_preserves_demographics(self):
        t = IntakeTracker()
        t.age = "50"
        t.gender = "male"
        data = t.to_dict()
        t2 = IntakeTracker(data=data)
        assert t2.age == "50"
        assert t2.gender == "male"

    def test_export_includes_demographics(self):
        t = IntakeTracker()
        t.age = "45"
        t.gender = "female"
        t.cc = "headache"
        data = t.to_intake_data()
        assert data["age"] == "45"
        assert data["gender"] == "female"

    def test_export_excludes_missing_demographics(self):
        t = IntakeTracker()
        t.cc = "headache"
        data = t.to_intake_data()
        assert "age" not in data
        assert "gender" not in data

    def test_existing_history_age_gender(self):
        t = IntakeTracker(existing_history={"age": 55, "gender": "male"})
        assert t.age == "55"
        assert t.gender == "male"

    def test_completeness_score_includes_demographics(self):
        t = IntakeTracker()
        t.age = "45"
        t.gender = "male"
        # Only demographics: 2.5% + 2.5% = 5%
        assert t.get_completeness_score() == 0.05


class TestEmptyValueRejection:
    """Tests for rejecting empty/whitespace values in history fields."""

    def test_empty_pmh_not_marked_complete(self):
        t = IntakeTracker()
        t.update_field("pmh", "")
        assert t.pmh_complete is False
        assert t.pmh is None

    def test_whitespace_pmh_not_marked_complete(self):
        t = IntakeTracker()
        t.update_field("pmh", "   ")
        assert t.pmh_complete is False

    def test_valid_pmh_marked_complete(self):
        t = IntakeTracker()
        t.update_field("pmh", "none")
        assert t.pmh_complete is True
        assert t.pmh == "none"

    def test_empty_medications_not_marked_complete(self):
        t = IntakeTracker()
        t.update_field("medications", "")
        assert t.medications_complete is False

    def test_valid_medications_marked_complete(self):
        t = IntakeTracker()
        t.update_field("medications", "khong co")
        assert t.medications_complete is True

    def test_empty_allergies_not_marked_complete(self):
        t = IntakeTracker()
        t.update_field("allergies", "")
        assert t.allergies_complete is False

    def test_valid_allergies_marked_complete(self):
        t = IntakeTracker()
        t.update_field("allergies", "NKDA")
        assert t.allergies_complete is True

    def test_empty_social_family_not_marked_complete(self):
        t = IntakeTracker()
        t.update_field("social_family", "")
        assert t.social_family_complete is False

    def test_valid_social_family_marked_complete(self):
        t = IntakeTracker()
        t.update_field("social_family", "non-smoker")
        assert t.social_family_complete is True


class TestEmergencySymptomCombo:
    """Tests for has_emergency_symptom_combo() — dangerous symptom accumulations."""

    def test_fever_plus_breathing_is_emergency(self):
        t = IntakeTracker()
        t.add_symptom("sot cao")
        t.add_symptom("kho tho")
        assert t.has_emergency_symptom_combo() is True

    def test_fever_plus_altered_speech_is_emergency(self):
        t = IntakeTracker()
        t.add_symptom("sot")
        t.add_symptom("khong the noi")
        assert t.has_emergency_symptom_combo() is True

    def test_chest_pain_plus_breathing_is_emergency(self):
        t = IntakeTracker()
        t.add_symptom("dau nguc")
        t.add_symptom("kho tho")
        assert t.has_emergency_symptom_combo() is True

    def test_severe_pain_plus_breathing_is_emergency(self):
        t = IntakeTracker()
        t.add_symptom("dau du doi")
        t.add_symptom("kho tho")
        assert t.has_emergency_symptom_combo() is True

    def test_meningitis_triad_is_emergency(self):
        t = IntakeTracker()
        t.add_symptom("dau dau du doi")
        t.add_symptom("sot")
        t.add_symptom("buon non")
        assert t.has_emergency_symptom_combo() is True

    def test_high_risk_plus_three_symptoms_is_emergency(self):
        t = IntakeTracker()
        t.risk_level = "high"
        t.add_symptom("met moi")
        t.add_symptom("chong mat")
        t.add_symptom("buon non")
        assert t.has_emergency_symptom_combo() is True

    def test_single_symptom_no_emergency(self):
        t = IntakeTracker()
        t.add_symptom("dau bung")
        assert t.has_emergency_symptom_combo() is False

    def test_two_mild_symptoms_no_emergency(self):
        t = IntakeTracker()
        t.add_symptom("dau bung")
        t.add_symptom("buon non")
        assert t.has_emergency_symptom_combo() is False

    def test_cc_field_contributes_to_combo(self):
        """CC field 'sot cao' + active_symptom 'kho tho' should trigger."""
        t = IntakeTracker()
        t.cc = "sot cao"
        t.add_symptom("kho tho")
        assert t.has_emergency_symptom_combo() is True

    def test_hpi_severity_contributes_to_combo(self):
        """HPI severity 'du doi' + breathing symptom should trigger."""
        t = IntakeTracker()
        t.hpi["severity"] = "dau du doi"
        t.add_symptom("kho tho")
        assert t.has_emergency_symptom_combo() is True
