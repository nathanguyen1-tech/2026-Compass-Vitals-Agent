"""Tests for Complaint Protocol Data Layer — protocol definitions and CC classification."""

from app.agents.prompts.complaint_protocols import (
    FALLBACK_PROTOCOL,
    OLDCARTS_ALL,
    PROTOCOLS,
    classify_chief_complaint,
    get_complaint_protocol,
    get_relevant_oldcarts,
)


class TestProtocolDefinitions:
    """All 11 protocols have required fields."""

    def test_all_protocols_have_required_fields(self):
        required_keys = {
            "id", "name_en", "name_vi", "keywords_en", "keywords_vi",
            "hpi_additions", "relevant_oldcarts", "red_flags", "ros_focus",
            "cultural_notes", "priority_order",
        }
        for protocol_id, protocol in PROTOCOLS.items():
            for key in required_keys:
                assert key in protocol, f"Protocol '{protocol_id}' missing key '{key}'"

    def test_eleven_protocols_defined(self):
        assert len(PROTOCOLS) == 11

    def test_fallback_protocol_has_required_fields(self):
        assert FALLBACK_PROTOCOL["id"] == "general"
        assert len(FALLBACK_PROTOCOL["hpi_additions"]) > 0

    def test_chest_pain_has_red_flags_first_priority(self):
        assert PROTOCOLS["chest_pain"]["priority_order"] == "red_flags_first"

    def test_standard_protocols_have_standard_priority(self):
        for pid, protocol in PROTOCOLS.items():
            if pid != "chest_pain":
                assert protocol["priority_order"] == "standard"

    def test_all_red_flags_have_bilingual_messages(self):
        for protocol_id, protocol in PROTOCOLS.items():
            for rf in protocol["red_flags"]:
                assert rf.get("message_en"), f"{protocol_id}/{rf['id']} missing message_en"
                assert rf.get("message_vi"), f"{protocol_id}/{rf['id']} missing message_vi"
                assert rf.get("action") in ("911", "ER", "urgent_review"), (
                    f"{protocol_id}/{rf['id']} invalid action: {rf.get('action')}"
                )

    def test_all_protocols_have_keywords(self):
        for protocol_id, protocol in PROTOCOLS.items():
            assert len(protocol["keywords_en"]) > 0, f"{protocol_id} missing English keywords"
            assert len(protocol["keywords_vi"]) > 0, f"{protocol_id} missing Vietnamese keywords"


class TestClassifyChiefComplaint:
    """Test CC classification function."""

    def test_classifies_chest_pain_en(self):
        assert classify_chief_complaint("I have chest pain") == "chest_pain"

    def test_classifies_chest_pain_vi(self):
        assert classify_chief_complaint("toi bi dau nguc") == "chest_pain"

    def test_classifies_headache_en(self):
        assert classify_chief_complaint("I have a terrible headache") == "headache"

    def test_classifies_headache_vi(self):
        assert classify_chief_complaint("toi bi dau dau du doi") == "headache"

    def test_classifies_diabetes_en(self):
        assert classify_chief_complaint("my blood sugar is high") == "diabetes"

    def test_classifies_diabetes_vi(self):
        assert classify_chief_complaint("duong huyet toi cao") == "diabetes"

    def test_classifies_hypertension_en(self):
        assert classify_chief_complaint("my blood pressure is high") == "hypertension"

    def test_classifies_mental_health_en(self):
        assert classify_chief_complaint("I feel depressed and can't sleep") == "mental_health"

    def test_classifies_mental_health_vi(self):
        assert classify_chief_complaint("toi bi tram cam va mat ngu") == "mental_health"

    def test_classifies_abdominal_en(self):
        assert classify_chief_complaint("I have stomach pain and nausea") == "abdominal_gi"

    def test_classifies_uri_vi(self):
        assert classify_chief_complaint("toi bi ho va so mui") == "uri_cough"

    def test_classifies_back_pain_en(self):
        assert classify_chief_complaint("I have lower back pain") == "back_joint_pain"

    def test_classifies_skin_rash_en(self):
        assert classify_chief_complaint("I have a rash on my arm") == "skin_rash"

    def test_classifies_urinary_en(self):
        assert classify_chief_complaint("burning urination and blood in urine") == "urinary"

    def test_classifies_fatigue_en(self):
        assert classify_chief_complaint("I'm always tired and exhausted") == "fatigue"

    def test_returns_general_for_unknown(self):
        assert classify_chief_complaint("something random here") == "general"

    def test_returns_general_for_empty(self):
        assert classify_chief_complaint("") == "general"


class TestGetComplaintProtocol:
    def test_returns_protocol_for_known_category(self):
        protocol = get_complaint_protocol("chest_pain")
        assert protocol["id"] == "chest_pain"

    def test_returns_fallback_for_general(self):
        protocol = get_complaint_protocol("general")
        assert protocol["id"] == "general"

    def test_returns_fallback_for_none(self):
        protocol = get_complaint_protocol(None)
        assert protocol["id"] == "general"

    def test_returns_fallback_for_unknown(self):
        protocol = get_complaint_protocol("unknown_category")
        assert protocol["id"] == "general"


class TestRelevantOldcarts:
    """Tests for complaint-specific OLDCARTS field filtering."""

    def test_all_protocols_have_relevant_oldcarts(self):
        for pid, protocol in PROTOCOLS.items():
            assert "relevant_oldcarts" in protocol, f"{pid} missing relevant_oldcarts"
            assert len(protocol["relevant_oldcarts"]) >= 3, (
                f"{pid} should have at least 3 relevant OLDCARTS fields"
            )

    def test_fallback_has_all_eight(self):
        assert len(FALLBACK_PROTOCOL["relevant_oldcarts"]) == 8

    def test_relevant_fields_are_valid(self):
        valid = set(OLDCARTS_ALL)
        for pid, protocol in PROTOCOLS.items():
            for field in protocol["relevant_oldcarts"]:
                assert field in valid, f"{pid} has invalid field '{field}'"

    def test_chest_pain_has_all_eight(self):
        assert len(PROTOCOLS["chest_pain"]["relevant_oldcarts"]) == 8

    def test_hypertension_excludes_location_character(self):
        fields = PROTOCOLS["hypertension"]["relevant_oldcarts"]
        assert "location" not in fields
        assert "character" not in fields

    def test_diabetes_excludes_location_character(self):
        fields = PROTOCOLS["diabetes"]["relevant_oldcarts"]
        assert "location" not in fields
        assert "character" not in fields

    def test_mental_health_excludes_location_character(self):
        fields = PROTOCOLS["mental_health"]["relevant_oldcarts"]
        assert "location" not in fields
        assert "character" not in fields

    def test_fatigue_excludes_location_character(self):
        fields = PROTOCOLS["fatigue"]["relevant_oldcarts"]
        assert "location" not in fields
        assert "character" not in fields

    def test_headache_includes_location(self):
        assert "location" in PROTOCOLS["headache"]["relevant_oldcarts"]

    def test_abdominal_includes_location(self):
        assert "location" in PROTOCOLS["abdominal_gi"]["relevant_oldcarts"]

    def test_get_relevant_oldcarts_helper(self):
        protocol = get_complaint_protocol("hypertension")
        fields = get_relevant_oldcarts(protocol)
        assert "onset" in fields
        assert "location" not in fields

    def test_get_relevant_oldcarts_fallback(self):
        fake_protocol = {"id": "test"}
        fields = get_relevant_oldcarts(fake_protocol)
        assert len(fields) == 8


class TestFeverClassifiesAsURICough:
    """Fever keywords should classify into uri_cough, not general."""

    def test_sot_ascii(self):
        assert classify_chief_complaint("toi bi sot") == "uri_cough"

    def test_sot_unicode(self):
        assert classify_chief_complaint("toi bi sốt") == "uri_cough"

    def test_fever_en(self):
        assert classify_chief_complaint("I have a fever") == "uri_cough"

    def test_chills_en(self):
        assert classify_chief_complaint("I have chills and body aches") == "uri_cough"

    def test_nhiet_do_cao(self):
        assert classify_chief_complaint("nhiet do cao qua") == "uri_cough"


class TestClinicalReasoning:
    """All protocols should have clinical_reasoning for LLM decision support."""

    def test_all_protocols_have_clinical_reasoning(self):
        for pid, protocol in PROTOCOLS.items():
            assert "clinical_reasoning" in protocol, (
                f"Protocol '{pid}' missing 'clinical_reasoning'"
            )

    def test_fallback_has_clinical_reasoning(self):
        assert "clinical_reasoning" in FALLBACK_PROTOCOL

    def test_clinical_reasoning_has_required_keys(self):
        required_keys = {"risk_stratification", "investigation_strategy", "danger_combinations"}
        for pid, protocol in PROTOCOLS.items():
            cr = protocol["clinical_reasoning"]
            for key in required_keys:
                assert key in cr, (
                    f"Protocol '{pid}' clinical_reasoning missing key '{key}'"
                )

    def test_danger_combinations_are_lists(self):
        for pid, protocol in PROTOCOLS.items():
            combos = protocol["clinical_reasoning"]["danger_combinations"]
            assert isinstance(combos, list), f"{pid} danger_combinations must be a list"
            assert len(combos) >= 2, f"{pid} should have at least 2 danger combinations"

    def test_chest_pain_has_most_danger_combinations(self):
        """Chest pain is highest-stakes — should have the most danger combos."""
        chest = PROTOCOLS["chest_pain"]["clinical_reasoning"]["danger_combinations"]
        assert len(chest) >= 5

    def test_mental_health_has_mandatory_safety_screening(self):
        """Mental health protocol must mention mandatory safety screening."""
        mh = PROTOCOLS["mental_health"]["clinical_reasoning"]
        assert "MANDATORY" in mh["investigation_strategy"].upper()

    def test_pmh_modifiers_present_in_key_protocols(self):
        """High-risk protocols should have pmh_modifiers."""
        for pid in ("chest_pain", "headache", "diabetes", "abdominal_gi"):
            cr = PROTOCOLS[pid]["clinical_reasoning"]
            assert "pmh_modifiers" in cr, f"{pid} should have pmh_modifiers"
            assert len(cr["pmh_modifiers"]) >= 1
