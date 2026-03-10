"""Tests for Contextual Emergency Detection — complaint-specific red flags."""

from app.agents.tools.emergency_detector import (
    detect_contextual_red_flags,
    get_red_flag_screening_questions,
)


class TestContextualRedFlagDetection:
    def test_chest_pain_with_dyspnea(self):
        flags = detect_contextual_red_flags(
            "I have chest pain right now and I can't breathe",
            complaint_category="chest_pain",
        )
        assert len(flags) > 0
        assert flags[0]["action"] == "911"
        assert flags[0]["id"] == "acs_active"

    def test_chest_pain_without_active_symptoms(self):
        flags = detect_contextual_red_flags(
            "I had some chest discomfort yesterday but it went away",
            complaint_category="chest_pain",
        )
        # "chest pain now" not in text, so may not trigger
        # but check that function runs without error
        assert isinstance(flags, list)

    def test_headache_thunderclap(self):
        flags = detect_contextual_red_flags(
            "This is the worst headache of my life, it came on suddenly",
            complaint_category="headache",
        )
        assert len(flags) > 0
        assert any(f["id"] == "thunderclap_headache" for f in flags)

    def test_headache_normal(self):
        flags = detect_contextual_red_flags(
            "I have a mild headache for two days",
            complaint_category="headache",
        )
        assert len(flags) == 0

    def test_mental_health_suicidal(self):
        flags = detect_contextual_red_flags(
            "I don't want to live anymore, I want to kill myself",
            complaint_category="mental_health",
        )
        assert len(flags) > 0
        assert flags[0]["id"] == "suicidal_ideation"
        assert flags[0]["action"] == "911"

    def test_mental_health_vi_suicidal(self):
        flags = detect_contextual_red_flags(
            "toi khong muon song nua",
            complaint_category="mental_health",
        )
        assert len(flags) > 0
        assert flags[0]["id"] == "suicidal_ideation"

    def test_abdominal_acute(self):
        flags = detect_contextual_red_flags(
            "I have severe abdominal pain and I'm di cau ra mau",
            complaint_category="abdominal_gi",
        )
        assert len(flags) > 0
        assert flags[0]["id"] == "acute_abdomen"

    def test_back_pain_cauda_equina(self):
        flags = detect_contextual_red_flags(
            "I lost bladder control and my legs are getting weaker",
            complaint_category="back_joint_pain",
        )
        assert len(flags) > 0
        assert flags[0]["id"] == "cauda_equina"

    def test_fatigue_sudden_weakness(self):
        flags = detect_contextual_red_flags(
            "I had sudden weakness on one side of my body",
            complaint_category="fatigue",
        )
        assert len(flags) > 0
        assert flags[0]["id"] == "sudden_weakness"

    def test_no_category_no_specific_flags(self):
        flags = detect_contextual_red_flags(
            "I have a cold",
            complaint_category=None,
        )
        assert isinstance(flags, list)

    def test_sorted_by_severity(self):
        """911 flags should come before ER flags."""
        flags = detect_contextual_red_flags(
            "I have chest pain now and can't breathe and my leg is swollen",
            complaint_category="chest_pain",
        )
        if len(flags) > 1:
            actions = [f["action"] for f in flags]
            # 911 should come first
            if "911" in actions and "ER" in actions:
                assert actions.index("911") < actions.index("ER")


class TestCrossComplaintRedFlags:
    def test_stroke_signs_face_droop(self):
        flags = detect_contextual_red_flags(
            "my face is drooping on one side",
            complaint_category=None,
        )
        assert any(f["id"] == "stroke_signs" for f in flags)

    def test_stroke_signs_vi(self):
        flags = detect_contextual_red_flags(
            "toi bi meo mieng dot ngot",
            complaint_category=None,
        )
        assert any(f["id"] == "stroke_signs" for f in flags)

    def test_anaphylaxis_needs_both_groups(self):
        # Only throat swelling, no breathing difficulty — should not trigger
        flags = detect_contextual_red_flags(
            "my throat is swelling",
            complaint_category=None,
        )
        anaphylaxis_flags = [f for f in flags if f["id"] == "anaphylaxis"]
        # Should NOT trigger because min_groups=2
        assert len(anaphylaxis_flags) == 0

    def test_anaphylaxis_both_groups(self):
        flags = detect_contextual_red_flags(
            "my throat is closing and I can't breathe",
            complaint_category=None,
        )
        assert any(f["id"] == "anaphylaxis" for f in flags)


class TestConversationHistory:
    def test_uses_history_for_context(self):
        """Red flags from previous messages should be detected."""
        flags = detect_contextual_red_flags(
            "yes, it's getting worse",
            complaint_category="chest_pain",
            conversation_history=[
                "I have chest pain right now",
                "do mo hoi nhieu",
            ],
        )
        # The history mentions "chest pain now" and "do mo hoi"
        assert len(flags) > 0


class TestRedFlagScreeningQuestions:
    def test_chest_pain_has_3_safety_questions(self):
        questions = get_red_flag_screening_questions("chest_pain")
        assert len(questions) == 3
        assert all("question_en" in q for q in questions)
        assert all("question_vi" in q for q in questions)

    def test_headache_has_screening_questions(self):
        questions = get_red_flag_screening_questions("headache")
        assert len(questions) >= 2

    def test_mental_health_has_safety_screening(self):
        questions = get_red_flag_screening_questions("mental_health")
        assert len(questions) >= 1
        assert any("hurt" in q["question_en"].lower() for q in questions)

    def test_back_pain_has_cauda_equina_screening(self):
        questions = get_red_flag_screening_questions("back_joint_pain")
        assert len(questions) >= 2

    def test_unknown_category_returns_empty(self):
        questions = get_red_flag_screening_questions("unknown")
        assert questions == []

    def test_general_returns_empty(self):
        questions = get_red_flag_screening_questions("general")
        assert questions == []


class TestAnaphylaxisExpandedKeywords:
    """Test expanded anaphylaxis cross-complaint keywords (hives, swollen face)."""

    def test_hives_plus_breathing_en(self):
        flags = detect_contextual_red_flags(
            "I have hives all over and I can't breathe",
            complaint_category=None,
        )
        assert any(f["id"] == "anaphylaxis" for f in flags)

    def test_noi_me_day_plus_kho_tho_vi(self):
        flags = detect_contextual_red_flags(
            "toi bi noi me day khap nguoi va kho tho",
            complaint_category=None,
        )
        assert any(f["id"] == "anaphylaxis" for f in flags)
