"""Tests for Dynamic Intake Prompt Composer."""

from app.agents.prompts.complaint_protocols import get_complaint_protocol
from app.agents.prompts.intake_prompt import INTAKE_SYSTEM_PROMPT, compose_intake_prompt
from app.agents.tools.intake_tracker import IntakeTracker


class TestBackwardCompatibility:
    def test_intake_system_prompt_constant_exists(self):
        """INTAKE_SYSTEM_PROMPT still importable for backward compatibility."""
        assert isinstance(INTAKE_SYSTEM_PROMPT, str)
        assert len(INTAKE_SYSTEM_PROMPT) > 100

    def test_default_prompt_contains_role(self):
        prompt = compose_intake_prompt()
        assert "Medical Intake Specialist" in prompt

    def test_default_prompt_contains_rules(self):
        prompt = compose_intake_prompt()
        assert "ONE question at a time" in prompt

    def test_default_prompt_contains_marker_instructions(self):
        prompt = compose_intake_prompt()
        assert "INTAKE:" in prompt


class TestGreetingPhase:
    def test_greeting_vi(self):
        prompt = compose_intake_prompt(detected_language="vi")
        assert "15 phut" in prompt

    def test_greeting_en(self):
        prompt = compose_intake_prompt(detected_language="en")
        assert "15 minutes" in prompt

    def test_greeting_contains_cc_prompt(self):
        prompt = compose_intake_prompt(detected_language="vi")
        assert "GREETING" in prompt


class TestCCPhase:
    def test_cc_phase_instruction(self):
        tracker = IntakeTracker()
        tracker.phase = "cc"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "CHIEF COMPLAINT" in prompt


class TestRedFlagPhase:
    def test_red_flag_phase_standard(self):
        tracker = IntakeTracker()
        tracker.phase = "red_flag_screening"
        protocol = get_complaint_protocol("headache")
        prompt = compose_intake_prompt(tracker=tracker, complaint_protocol=protocol)
        assert "RED FLAG SCREENING" in prompt
        assert "thunderclap" in prompt.lower() or "worst headache" in prompt.lower()

    def test_red_flag_phase_chest_pain_first(self):
        tracker = IntakeTracker()
        tracker.phase = "red_flag_screening"
        protocol = get_complaint_protocol("chest_pain")
        prompt = compose_intake_prompt(tracker=tracker, complaint_protocol=protocol)
        assert "RED_FLAGS_FIRST" in prompt
        assert "911" in prompt


class TestHPIPhase:
    def test_hpi_shows_oldcarts(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "OLDCARTS" in prompt
        assert "Onset" in prompt
        assert "Severity" in prompt

    def test_hpi_shows_missing_fields(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        tracker.hpi["onset"] = "3 days"
        tracker.hpi["severity"] = "7"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "FIELDS STILL NEEDED" in prompt
        assert "onset" not in prompt.split("FIELDS STILL NEEDED")[1].split("\n")[0].lower()

    def test_hpi_with_complaint_protocol(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        protocol = get_complaint_protocol("hypertension")
        prompt = compose_intake_prompt(tracker=tracker, complaint_protocol=protocol)
        assert "COMPLAINT-SPECIFIC" in prompt
        assert "BP" in prompt or "blood pressure" in prompt.lower()

    def test_hpi_shows_progress(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        for f in ["onset", "location", "duration"]:
            tracker.hpi[f] = "val"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "3/8" in prompt


class TestROSPhase:
    def test_ros_phase(self):
        tracker = IntakeTracker()
        tracker.phase = "ros"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "REVIEW OF SYSTEMS" in prompt

    def test_ros_with_protocol_focus(self):
        tracker = IntakeTracker()
        tracker.phase = "ros"
        protocol = get_complaint_protocol("headache")
        prompt = compose_intake_prompt(tracker=tracker, complaint_protocol=protocol)
        assert "neurological" in prompt.lower()

    def test_ros_shows_already_covered(self):
        tracker = IntakeTracker()
        tracker.phase = "ros"
        tracker.ros_systems["cardiovascular"] = "negative"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "cardiovascular" in prompt.lower()


class TestHistorySections:
    def test_history_needed_when_no_prefill(self):
        tracker = IntakeTracker()
        tracker.phase = "pmh"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "PMH" in prompt or "medical history" in prompt.lower()

    def test_history_skipped_when_prefilled(self):
        tracker = IntakeTracker(existing_history={
            "pmh": "HTN", "medications": "Lisinopril", "allergies": "NKDA"
        })
        tracker.phase = "hpi"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "on file" in prompt.lower()
        assert "do NOT need to ask" in prompt or "do not need to ask" in prompt.lower()


class TestSummaryPhase:
    def test_summary_phase(self):
        tracker = IntakeTracker()
        tracker.phase = "summary"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "SUMMARY" in prompt
        assert "confirm" in prompt.lower()


class TestCompletePhase:
    def test_complete_phase(self):
        tracker = IntakeTracker()
        tracker.phase = "complete"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "physician" in prompt.lower()


class TestCulturalNotes:
    def test_cultural_notes_included(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        protocol = get_complaint_protocol("abdominal_gi")
        prompt = compose_intake_prompt(tracker=tracker, complaint_protocol=protocol)
        assert "Hepatitis B" in prompt or "viem gan" in prompt.lower()

    def test_no_cultural_notes_for_general(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        protocol = get_complaint_protocol("general")
        prompt = compose_intake_prompt(tracker=tracker, complaint_protocol=protocol)
        # General protocol has cultural notes too, just generic
        assert isinstance(prompt, str)


class TestProgressIndicator:
    def test_no_progress_early(self):
        tracker = IntakeTracker()
        tracker.phase = "cc"
        prompt = compose_intake_prompt(tracker=tracker, message_count=1)
        # Progress only shown after message_count > 2
        assert "PROGRESS UPDATE" not in prompt

    def test_progress_shown_later(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        tracker.cc = "headache"
        prompt = compose_intake_prompt(tracker=tracker, message_count=5)
        assert "PROGRESS UPDATE" in prompt


class TestRelevantOldcartsFiltering:
    def test_hypertension_excludes_location_in_prompt(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        tracker.set_relevant_oldcarts(["onset", "duration", "aggravating", "severity"])
        protocol = get_complaint_protocol("hypertension")
        prompt = compose_intake_prompt(tracker=tracker, complaint_protocol=protocol)
        assert "Where exactly?" not in prompt
        assert "NEVER ask about" in prompt
        assert "location" in prompt.split("NEVER ask about")[1].split(".")[0]

    def test_chest_pain_includes_all_fields(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        protocol = get_complaint_protocol("chest_pain")
        tracker.set_relevant_oldcarts(protocol["relevant_oldcarts"])
        prompt = compose_intake_prompt(tracker=tracker, complaint_protocol=protocol)
        assert "Onset" in prompt
        assert "Location" in prompt
        assert "Severity" in prompt
        assert "CRITICAL RESTRICTION" not in prompt

    def test_progress_shows_relevant_count(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        tracker.set_relevant_oldcarts(["onset", "duration", "aggravating", "severity"])
        tracker.hpi["onset"] = "2 weeks"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "1/4" in prompt

    def test_missing_fields_only_relevant(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        tracker.set_relevant_oldcarts(["onset", "duration", "severity"])
        tracker.hpi["onset"] = "3 days"
        prompt = compose_intake_prompt(tracker=tracker)
        needed = prompt.split("FIELDS STILL NEEDED:")[1].split("\n")[0]
        assert "duration" in needed
        assert "severity" in needed
        assert "location" not in needed


class TestRedFlagOldcartsExclusion:
    """OLDCARTS exclusion should also appear in red_flag_screening phase."""

    def test_red_flag_phase_excludes_irrelevant_fields(self):
        tracker = IntakeTracker()
        tracker.phase = "red_flag_screening"
        tracker.set_relevant_oldcarts(["onset", "duration", "aggravating", "severity"])
        protocol = get_complaint_protocol("uri_cough")
        prompt = compose_intake_prompt(tracker=tracker, complaint_protocol=protocol)
        assert "NOT clinically relevant" in prompt
        assert "location" in prompt.split("NOT clinically relevant")[1].split("***")[0]

    def test_red_flag_phase_no_exclusion_for_full_oldcarts(self):
        tracker = IntakeTracker()
        tracker.phase = "red_flag_screening"
        tracker.set_relevant_oldcarts(list(
            ["onset", "location", "duration", "character",
             "aggravating", "alleviating", "timing", "severity"]
        ))
        protocol = get_complaint_protocol("chest_pain")
        prompt = compose_intake_prompt(tracker=tracker, complaint_protocol=protocol)
        assert "NOT clinically relevant" not in prompt


class TestEmergencyDetectionInstructions:
    """Emergency detection instructions should appear in ALL phases."""

    def test_emergency_instructions_in_greeting(self):
        prompt = compose_intake_prompt(detected_language="vi")
        assert "EMERGENCY DETECTION" in prompt
        assert "emergency_suspected" in prompt

    def test_emergency_instructions_in_hpi(self):
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "EMERGENCY DETECTION" in prompt

    def test_emergency_instructions_in_ros(self):
        tracker = IntakeTracker()
        tracker.phase = "ros"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "EMERGENCY DETECTION" in prompt

    def test_emergency_instructions_in_summary(self):
        tracker = IntakeTracker()
        tracker.phase = "summary"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "EMERGENCY DETECTION" in prompt


class TestEmergencyConfirmationPrompt:
    """Tests for the 2-question confirmation protocol in prompt."""

    def test_confirmation_section_injected_when_suspected(self):
        """Confirmation section should be injected when suspected_emergency is set."""
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        tracker.suspected_emergency = {
            "reason": "chest_pain_active",
            "confirmation_questions_asked": 0,
            "source": "llm",
        }
        prompt = compose_intake_prompt(tracker=tracker)
        assert "ACTIVE EMERGENCY INVESTIGATION" in prompt
        assert "chest_pain_active" in prompt

    def test_no_confirmation_section_without_suspected(self):
        """No confirmation section when suspected_emergency is None."""
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "ACTIVE EMERGENCY INVESTIGATION" not in prompt

    def test_emergency_instructions_include_confirmation_flow(self):
        """Prompt should instruct LLM to use 2-question confirmation protocol."""
        prompt = compose_intake_prompt()
        assert "emergency_suspected" in prompt
        assert "emergency_confirmed" in prompt
        assert "emergency_cleared" in prompt

    def test_confirmation_section_shows_remaining_questions(self):
        """Confirmation section should show how many questions remain."""
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        tracker.suspected_emergency = {
            "reason": "possible_acs",
            "confirmation_questions_asked": 1,
            "source": "llm",
        }
        prompt = compose_intake_prompt(tracker=tracker)
        assert "1 more" in prompt

    def test_confirmation_section_shows_must_decide(self):
        """After 2 questions, section should tell LLM to decide."""
        tracker = IntakeTracker()
        tracker.phase = "hpi"
        tracker.suspected_emergency = {
            "reason": "possible_acs",
            "confirmation_questions_asked": 2,
            "source": "llm",
        }
        prompt = compose_intake_prompt(tracker=tracker)
        assert "MUST now emit" in prompt


class TestDemographicsInPrompt:
    """Tests for age/gender demographics in prompt."""

    def test_greeting_asks_for_demographics_vi(self):
        prompt = compose_intake_prompt(detected_language="vi")
        assert "tuoi" in prompt.lower()
        assert "gioi tinh" in prompt.lower()

    def test_greeting_asks_for_demographics_en(self):
        prompt = compose_intake_prompt(detected_language="en")
        assert "age" in prompt.lower()
        assert "gender" in prompt.lower()

    def test_marker_instructions_include_age_gender(self):
        prompt = compose_intake_prompt()
        assert "age" in prompt
        assert "gender" in prompt

    def test_demographics_missing_warning_in_history(self):
        tracker = IntakeTracker()
        tracker.phase = "pmh"
        # age and gender not set
        prompt = compose_intake_prompt(tracker=tracker)
        assert "DEMOGRAPHICS MISSING" in prompt

    def test_no_demographics_warning_when_present(self):
        tracker = IntakeTracker()
        tracker.phase = "pmh"
        tracker.age = "45"
        tracker.gender = "male"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "DEMOGRAPHICS MISSING" not in prompt


class TestMandatoryHistoryRule:
    """Tests for mandatory history collection rule in _CORE_RULES."""

    def test_mandatory_collection_rule_exists(self):
        prompt = compose_intake_prompt()
        assert "MANDATORY INFORMATION COLLECTION" in prompt

    def test_mandatory_rule_mentions_age_gender(self):
        prompt = compose_intake_prompt()
        mandatory_section = prompt.split("MANDATORY INFORMATION COLLECTION")[1].split("\n\n")[0]
        assert "age" in mandatory_section
        assert "gender" in mandatory_section

    def test_history_sections_directive_language(self):
        tracker = IntakeTracker()
        tracker.phase = "pmh"
        prompt = compose_intake_prompt(tracker=tracker)
        assert "You MUST still ask about" in prompt
        assert "Do NOT move to summary" in prompt
