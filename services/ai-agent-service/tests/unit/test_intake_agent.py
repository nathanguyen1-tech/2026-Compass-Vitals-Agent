"""Tests for Intake Agent — symptom collection, emergency detection, NLP integration."""

from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.intake_agent import intake_node
from app.domain.services.llm_gateway import LLMGateway, LLMResponse
from app.domain.services.phi_deidentifier import PHIDeidentifier


@pytest.fixture
def phi():
    key = Fernet.generate_key().decode()
    return PHIDeidentifier(encryption_key=key)


@pytest.fixture
def mock_gateway(phi):
    gateway = LLMGateway(
        openai_api_key="test-key",
        phi_deidentifier=phi,
    )
    return gateway


@pytest.fixture
def mock_response():
    return LLMResponse(
        content="Bạn bị đau bụng ở vị trí nào? Bên phải hay bên trái?",
        model="gpt-4o-mini",
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        finish_reason="stop",
    )


def _make_state(**overrides):
    base = {
        "patient_id": "test-patient",
        "case_id": "test-case",
        "organization_id": "test-org",
        "messages": [],
        "intake_data": None,
        "intake_complete": False,
        "is_emergency": False,
        "detected_language": "vi",
        "cultural_expressions": [],
        "created_at": "2026-02-27T00:00:00Z",
        "updated_at": "2026-02-27T00:00:00Z",
        "correlation_id": "test-corr",
        "intake_tracker": None,
    }
    base.update(overrides)
    return base


class TestIntakeNodeEmptyMessages:
    @pytest.mark.asyncio
    async def test_returns_greeting_when_no_messages(self, mock_gateway, phi):
        state = _make_state(messages=[])
        result = await intake_node(state, mock_gateway, phi)
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert "Compass Vitals" in result["messages"][0].content


class TestEmergencyDetection:
    @pytest.mark.asyncio
    async def test_detects_instant_emergency_bat_tinh(self, mock_gateway, phi):
        """INSTANT keywords (bất tỉnh) should trigger emergency immediately."""
        state = _make_state(
            messages=[HumanMessage(content="Bệnh nhân bất tỉnh, co giật")]
        )
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is True
        assert "KHẨN CẤP" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_no_emergency_normal_symptoms(self, mock_gateway, phi, mock_response):
        state = _make_state(
            messages=[HumanMessage(content="Tôi bị đau bụng 2 ngày rồi")]
        )
        # Mock the LLM call
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False


class TestLanguageDetection:
    @pytest.mark.asyncio
    async def test_detects_vietnamese(self, mock_gateway, phi, mock_response):
        state = _make_state(
            messages=[HumanMessage(content="Tôi bị đau bụng")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["detected_language"] == "vi"

    @pytest.mark.asyncio
    async def test_detects_mixed(self, mock_gateway, phi, mock_response):
        state = _make_state(
            messages=[HumanMessage(content="Con bị fever 3 ngày rồi")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["detected_language"] == "mixed"


class TestCulturalExpressions:
    @pytest.mark.asyncio
    async def test_detects_nong_trong(self, mock_gateway, phi, mock_response):
        state = _make_state(
            messages=[HumanMessage(content="Tôi bị nóng trong người")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert len(result["cultural_expressions"]) >= 1
        assert any(
            "inflammation" in e["medical_terms"]
            for e in result["cultural_expressions"]
        )


class TestLLMEmergencyMarkerOverride:
    """Tests for LLM emergency markers: suspected → confirmed → cleared flow."""

    @pytest.mark.asyncio
    async def test_legacy_emergency_detected_sets_suspected(self, mock_gateway, phi):
        """Legacy emergency_detected marker should set suspected, not immediately escalate."""
        llm_response_with_marker = LLMResponse(
            content=(
                "I understand you're feeling pressure on your chest. "
                "Let me ask: is this happening RIGHT NOW? "
                "[INTAKE:emergency_detected=probable_acs_indirect_description]"
            ),
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        state = _make_state(
            messages=[HumanMessage(content="nguc toi nhu bi de nat, kho chiu lam")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=llm_response_with_marker)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False
        # LLM text is returned (with markers stripped)
        assert "happening RIGHT NOW" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_emergency_suspected_sets_suspected(self, mock_gateway, phi):
        """emergency_suspected marker should set suspected, continue with LLM text."""
        response = LLMResponse(
            content=(
                "Ban mo ta trieu chung nghiem trong. "
                "[INTAKE:emergency_suspected=severe_symptoms_detected]"
            ),
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        # Use a message that does NOT match broad keywords so LLM path runs
        state = _make_state(
            messages=[HumanMessage(content="toi cam thay rat choang vang va buon non lien tuc")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False
        assert "trieu chung nghiem trong" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_emergency_confirmed_with_enough_questions_escalates(self, mock_gateway, phi):
        """emergency_confirmed escalates only after ≥2 confirmation questions."""
        response = LLMResponse(
            content=(
                "Based on your answers, this needs immediate attention. "
                "[INTAKE:emergency_confirmed=severe_acs_with_dyspnea]"
            ),
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        state = _make_state(
            messages=[HumanMessage(content="vang, dang dau du doi lam")],
            intake_tracker={
                "phase": "hpi",
                "complaint_category": None,
                "message_count": 3,
                "cc": "chest pain",
                "hpi": {f: None for f in ["onset", "location", "duration", "character",
                                           "aggravating", "alleviating", "timing", "severity"]},
                "hpi_additional": {},
                "relevant_oldcarts": ["onset", "location", "duration", "character",
                                       "aggravating", "alleviating", "timing", "severity"],
                "red_flags_checked": [],
                "red_flags_found": [],
                "red_flag_screening_done": False,
                "ros_systems": {},
                "pmh": None, "pmh_complete": False,
                "medications": None, "medications_complete": False,
                "allergies": None, "allergies_complete": False,
                "social_family": None, "social_family_complete": False,
                "pmh_prefilled": False, "medications_prefilled": False,
                "allergies_prefilled": False, "social_family_prefilled": False,
                "summary_confirmed": False,
                "emergency_detected_reason": None,
                "suspected_emergency": {
                    "reason": "chest_pain_active",
                    "confirmation_questions_asked": 1,
                    "source": "llm",
                },
            },
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)
        result = await intake_node(state, mock_gateway, phi)
        # asked was 1 at start, incremented to 2 in Step 1b, then confirmed → escalate
        assert result["is_emergency"] is True
        assert "\u26a0\ufe0f" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_emergency_confirmed_too_early_no_escalation(self, mock_gateway, phi):
        """emergency_confirmed with <2 questions asked should NOT escalate."""
        response = LLMResponse(
            content=(
                "Based on your answers, this needs attention. "
                "[INTAKE:emergency_confirmed=possible_acs]"
            ),
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        state = _make_state(
            messages=[HumanMessage(content="vang, dau lam")],
            intake_tracker={
                "phase": "hpi",
                "complaint_category": None,
                "message_count": 1,
                "cc": "chest pain",
                "hpi": {f: None for f in ["onset", "location", "duration", "character",
                                           "aggravating", "alleviating", "timing", "severity"]},
                "hpi_additional": {},
                "relevant_oldcarts": ["onset", "location", "duration", "character",
                                       "aggravating", "alleviating", "timing", "severity"],
                "red_flags_checked": [],
                "red_flags_found": [],
                "red_flag_screening_done": False,
                "ros_systems": {},
                "pmh": None, "pmh_complete": False,
                "medications": None, "medications_complete": False,
                "allergies": None, "allergies_complete": False,
                "social_family": None, "social_family_complete": False,
                "pmh_prefilled": False, "medications_prefilled": False,
                "allergies_prefilled": False, "social_family_prefilled": False,
                "summary_confirmed": False,
                "emergency_detected_reason": None,
                "suspected_emergency": {
                    "reason": "chest_pain_active",
                    "confirmation_questions_asked": 0,
                    "source": "llm",
                },
            },
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)
        result = await intake_node(state, mock_gateway, phi)
        # asked was 0 at start, incremented to 1 — not enough, return LLM text
        assert result["is_emergency"] is False

    @pytest.mark.asyncio
    async def test_no_emergency_marker_returns_normal(self, mock_gateway, phi):
        """Without emergency marker, response should be normal."""
        normal_response = LLMResponse(
            content="Ban bi dau bung bao lau roi? [INTAKE:onset=asking]",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        state = _make_state(
            messages=[HumanMessage(content="toi bi dau bung 2 ngay")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=normal_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False


class TestNegationInIntakeAgent:
    """Negated INSTANT emergency keywords should not trigger emergency in intake_node."""

    @pytest.mark.asyncio
    async def test_negated_bat_tinh_not_emergency(self, mock_gateway, phi, mock_response):
        """'toi khong bi bat tinh' should NOT trigger INSTANT emergency."""
        state = _make_state(
            messages=[HumanMessage(content="toi không bị bất tỉnh")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False

    @pytest.mark.asyncio
    async def test_chest_pain_broad_keyword_sets_suspected(self, mock_gateway, phi, mock_response):
        """'dau nguc' triggers broad keyword → sets suspected, LLM continues."""
        state = _make_state(
            messages=[HumanMessage(content="toi bi \u0111au ng\u1ef1c nh\u1eb9")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        # Broad keyword sets suspected, does NOT immediately escalate
        assert result["is_emergency"] is False
        # LLM was called (conversation continues with confirmation questions)
        assert mock_gateway._call_with_retry.call_count >= 1

    @pytest.mark.asyncio
    async def test_trauma_fall_sets_suspected(self, mock_gateway, phi, mock_response):
        """'roi tu lau 2' should trigger broad keyword → sets suspected, LLM continues."""
        state = _make_state(
            messages=[HumanMessage(content="toi bi roi tu lau 2")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False
        assert mock_gateway._call_with_retry.call_count >= 1

    @pytest.mark.asyncio
    async def test_traffic_accident_sets_suspected(self, mock_gateway, phi, mock_response):
        """'tai nan xe' should trigger broad keyword → sets suspected, LLM continues."""
        state = _make_state(
            messages=[HumanMessage(content="toi bi tai nan xe may")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False


class TestSafetyClassifierIntegration:
    """Tests that the safety classifier catches emergencies keywords miss."""

    @pytest.mark.asyncio
    async def test_novel_emergency_caught_by_classifier_sets_suspected(self, mock_gateway, phi):
        """Battery ingestion: no keyword match, classifier sets suspected."""
        state = _make_state(
            messages=[HumanMessage(content="con toi 2 tuoi nuot phai cuc pin")]
        )
        # Primary LLM: normal response, no emergency markers
        primary_response = LLMResponse(
            content="Chao ban, con ban nuot pin khi nao? [INTAKE:risk_level=low] [INTAKE:risk_reasoning=gathering info]",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        # Safety classifier: critical emergency
        classifier_response = LLMResponse(
            content='{"risk_level":"critical","is_emergency":true,"reasoning":"battery ingestion in child","category":"toxic_ingestion"}',
            model="gpt-4o-mini",
            usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(
            side_effect=[primary_response, classifier_response]
        )
        result = await intake_node(state, mock_gateway, phi)
        # Safety classifier sets suspected, does NOT immediately escalate
        assert result["is_emergency"] is False
        # LLM text returned to patient (with markers stripped)
        assert "nuot pin" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_broad_keyword_sets_suspected_llm_continues(self, mock_gateway, phi, mock_response):
        """Broad keyword match sets suspected — LLM still called for response."""
        state = _make_state(
            messages=[HumanMessage(content="toi bi roi tu lau 2")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        # LLM IS called — broad keyword sets suspected, conversation continues
        assert mock_gateway._call_with_retry.call_count >= 1
        assert result["is_emergency"] is False

    @pytest.mark.asyncio
    async def test_classifier_runs_when_llm_reports_high(self, mock_gateway, phi):
        """If primary LLM reports high risk, classifier still runs as safety net."""
        state = _make_state(
            messages=[HumanMessage(content="toi cam thay rat met va hoa mat")]
        )
        primary_response = LLMResponse(
            content="Ban co bi ngat hoac mat y thuc khong? [INTAKE:risk_level=high] [INTAKE:risk_reasoning=fatigue with dizziness]",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        # Classifier returns non-emergency (just high risk, not is_emergency)
        classifier_response = LLMResponse(
            content='{"risk_level":"high","is_emergency":false,"reasoning":"fatigue, needs assessment","category":"general"}',
            model="gpt-4o-mini",
            usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(
            side_effect=[primary_response, classifier_response]
        )
        result = await intake_node(state, mock_gateway, phi)
        # 2 LLM calls: primary + classifier (classifier now runs for high risk)
        assert mock_gateway._call_with_retry.call_count == 2


class TestSuspectedEmergencyFlow:
    """Tests that broad keywords and classifier set suspected (not immediate)."""

    @pytest.mark.asyncio
    async def test_broad_keyword_sets_suspected_not_immediate(self, mock_gateway, phi, mock_response):
        """Broad keyword 'dau nguc' sets suspected — LLM asks confirmation questions."""
        state = _make_state(
            messages=[HumanMessage(content="toi bi \u0111au ng\u1ef1c")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False
        # LLM is called to ask confirmation questions
        assert mock_gateway._call_with_retry.call_count >= 1

    @pytest.mark.asyncio
    async def test_broad_keyword_negated_no_emergency(self, mock_gateway, phi, mock_response):
        """'khong bi dau nguc' (negated) should NOT trigger emergency."""
        state = _make_state(
            messages=[HumanMessage(content="toi kh\u00f4ng b\u1ecb \u0111au ng\u1ef1c")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False

    @pytest.mark.asyncio
    async def test_kho_tho_sets_suspected_not_immediate(self, mock_gateway, phi, mock_response):
        """'kho tho' (difficulty breathing) sets suspected — LLM continues."""
        state = _make_state(
            messages=[HumanMessage(content="toi b\u1ecb kh\u00f3 th\u1edf")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False
        assert mock_gateway._call_with_retry.call_count >= 1

    @pytest.mark.asyncio
    async def test_safety_classifier_sets_suspected(self, mock_gateway, phi):
        """Safety classifier is_emergency=True sets suspected (not immediate)."""
        state = _make_state(
            messages=[HumanMessage(content="con toi 2 tuoi nuot phai cuc pin")]
        )
        primary_response = LLMResponse(
            content="Con ban nuot pin khi nao? [INTAKE:risk_level=low] [INTAKE:risk_reasoning=gathering info]",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        classifier_response = LLMResponse(
            content='{"risk_level":"critical","is_emergency":true,"reasoning":"battery ingestion in child","category":"toxic_ingestion"}',
            model="gpt-4o-mini",
            usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(
            side_effect=[primary_response, classifier_response]
        )
        result = await intake_node(state, mock_gateway, phi)
        # Sets suspected, does NOT immediately escalate
        assert result["is_emergency"] is False


class TestConversationContextKeywordScan:
    """Tests for Step 1a.6: conversation-context keyword scan."""

    @pytest.mark.asyncio
    async def test_ai_asks_kho_tho_patient_confirms(self, mock_gateway, phi):
        """AI asks 'bạn có khó thở không?' + patient says 'có' → emergency."""
        state = _make_state(
            messages=[
                HumanMessage(content="toi bi sot cao"),
                AIMessage(content="Ban co bi kho tho khong?"),
                HumanMessage(content="co"),
            ],
        )
        mock_gateway._call_with_retry = AsyncMock()
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is True
        assert "\u26a0\ufe0f" in result["messages"][0].content
        # Should NOT call LLM — caught before LLM step
        assert mock_gateway._call_with_retry.call_count == 0

    @pytest.mark.asyncio
    async def test_ai_asks_kho_tho_patient_denies(self, mock_gateway, phi, mock_response):
        """AI asks 'bạn có khó thở không?' + patient says 'không' → no emergency."""
        state = _make_state(
            messages=[
                HumanMessage(content="toi bi sot"),
                AIMessage(content="Ban co bi kho tho khong?"),
                HumanMessage(content="khong"),
            ],
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False

    @pytest.mark.asyncio
    async def test_ai_asks_dau_nguc_patient_says_vang(self, mock_gateway, phi):
        """AI asks about dau nguc + patient says 'vang' → emergency."""
        state = _make_state(
            messages=[
                HumanMessage(content="toi thay kho chiu o nguc"),
                AIMessage(content="Ban co dau nguc khong?"),
                HumanMessage(content="vang, dau lam"),
            ],
        )
        mock_gateway._call_with_retry = AsyncMock()
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is True

    @pytest.mark.asyncio
    async def test_no_keyword_in_context_no_emergency(self, mock_gateway, phi, mock_response):
        """Normal conversation without emergency keywords in context."""
        state = _make_state(
            messages=[
                HumanMessage(content="toi bi dau bung"),
                AIMessage(content="Dau bung bat dau tu khi nao?"),
                HumanMessage(content="2 ngay truoc"),
            ],
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False


class TestSymptomComboEscalation:
    """Tests for Step 6.56c: symptom accumulation emergency check."""

    @pytest.mark.asyncio
    async def test_fever_plus_breathing_triggers_emergency(self, mock_gateway, phi):
        """Fever + breathing difficulty accumulated across turns → emergency."""
        from app.agents.tools.intake_tracker import IntakeTracker

        tracker = IntakeTracker()
        tracker.phase = "hpi"
        tracker.cc = "sot cao"
        tracker.add_symptom("sot")
        tracker.add_symptom("kho tho")

        state = _make_state(
            messages=[HumanMessage(content="bi ngay bay gio")],
            intake_tracker=tracker.to_dict(),
        )
        response = LLMResponse(
            content="[INTAKE:risk_level=high] [INTAKE:risk_reasoning=fever+dyspnea] Tinh trang cua ban nghiem trong.",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        # Classifier also runs but returns non-emergency JSON
        classifier_response = LLMResponse(
            content='{"risk_level":"high","is_emergency":false,"reasoning":"needs assessment","category":"respiratory"}',
            model="gpt-4o-mini",
            usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(
            side_effect=[response, classifier_response]
        )
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is True
        assert "\u26a0\ufe0f" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_chest_pain_plus_breathing_triggers_emergency(self, mock_gateway, phi):
        """Chest pain + SOB combo → emergency."""
        from app.agents.tools.intake_tracker import IntakeTracker

        tracker = IntakeTracker()
        tracker.phase = "hpi"
        tracker.cc = "dau nguc"
        tracker.add_symptom("dau nguc")
        tracker.add_symptom("kho tho")

        state = _make_state(
            messages=[HumanMessage(content="toi bi ca hai")],
            intake_tracker=tracker.to_dict(),
        )
        response = LLMResponse(
            content="[INTAKE:risk_level=high] [INTAKE:risk_reasoning=chest pain+SOB] Can gap bac si.",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        classifier_response = LLMResponse(
            content='{"risk_level":"high","is_emergency":false,"reasoning":"chest+breathing","category":"cardiac"}',
            model="gpt-4o-mini",
            usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(
            side_effect=[response, classifier_response]
        )
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is True

    @pytest.mark.asyncio
    async def test_single_symptom_no_combo_emergency(self, mock_gateway, phi):
        """Single symptom without dangerous combo does not trigger."""
        from app.agents.tools.intake_tracker import IntakeTracker

        tracker = IntakeTracker()
        tracker.phase = "hpi"
        tracker.cc = "dau bung"
        tracker.add_symptom("dau bung")

        state = _make_state(
            messages=[HumanMessage(content="dau bung 2 ngay roi")],
            intake_tracker=tracker.to_dict(),
        )
        response = LLMResponse(
            content="[INTAKE:risk_level=low] [INTAKE:risk_reasoning=abdominal pain] Dau o vi tri nao?",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False


class TestHistoryPhaseAutoAdvance:
    """Tests for auto-advance through PMH \u2192 medications \u2192 allergies \u2192 social_family \u2192 summary."""

    @pytest.mark.asyncio
    async def test_pmh_advances_to_medications(self, mock_gateway, phi):
        """When PMH is completed, phase should auto-advance to medications."""
        from app.agents.tools.intake_tracker import IntakeTracker

        tracker = IntakeTracker()
        tracker.phase = "pmh"
        tracker.cc = "headache"
        tracker.red_flag_screening_done = True
        for f in ["onset", "location", "duration", "character", "aggravating", "severity"]:
            tracker.hpi[f] = "value"
        tracker.ros_systems["neurological"] = "headaches"
        tracker.ros_systems["constitutional"] = "no fever"

        state = _make_state(
            messages=[HumanMessage(content="khong co benh nen")],
            intake_tracker=tracker.to_dict(),
        )

        response = LLMResponse(
            content="[INTAKE:risk_level=low] [INTAKE:risk_reasoning=routine] Da ghi nhan. [INTAKE:pmh=khong co benh nen]",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)

        result = await intake_node(state, mock_gateway, phi)
        tracker_data = result["intake_tracker"]
        assert tracker_data["pmh_complete"] is True
        assert tracker_data["phase"] == "medications"

    @pytest.mark.asyncio
    async def test_medications_advances_to_allergies(self, mock_gateway, phi):
        """When medications is completed, phase should auto-advance to allergies."""
        from app.agents.tools.intake_tracker import IntakeTracker

        tracker = IntakeTracker()
        tracker.phase = "medications"
        tracker.cc = "headache"
        tracker.red_flag_screening_done = True
        for f in ["onset", "location", "duration", "character", "aggravating", "severity"]:
            tracker.hpi[f] = "value"
        tracker.ros_systems["neurological"] = "headaches"
        tracker.ros_systems["constitutional"] = "no fever"
        tracker.pmh = "none"
        tracker.pmh_complete = True

        state = _make_state(
            messages=[HumanMessage(content="toi dang uong paracetamol")],
            intake_tracker=tracker.to_dict(),
        )

        response = LLMResponse(
            content="[INTAKE:risk_level=low] [INTAKE:risk_reasoning=routine] Da ghi nhan. [INTAKE:medications=paracetamol]",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)

        result = await intake_node(state, mock_gateway, phi)
        tracker_data = result["intake_tracker"]
        assert tracker_data["medications_complete"] is True
        assert tracker_data["phase"] == "allergies"

    @pytest.mark.asyncio
    async def test_allergies_advances_to_social_family(self, mock_gateway, phi):
        """When allergies is completed, phase should auto-advance to social_family."""
        from app.agents.tools.intake_tracker import IntakeTracker

        tracker = IntakeTracker()
        tracker.phase = "allergies"
        tracker.cc = "headache"
        tracker.red_flag_screening_done = True
        for f in ["onset", "location", "duration", "character", "aggravating", "severity"]:
            tracker.hpi[f] = "value"
        tracker.ros_systems["neurological"] = "headaches"
        tracker.ros_systems["constitutional"] = "no fever"
        tracker.pmh = "none"
        tracker.pmh_complete = True
        tracker.medications = "paracetamol"
        tracker.medications_complete = True

        state = _make_state(
            messages=[HumanMessage(content="khong di ung gi")],
            intake_tracker=tracker.to_dict(),
        )

        response = LLMResponse(
            content="[INTAKE:risk_level=low] [INTAKE:risk_reasoning=routine] Da ghi nhan. [INTAKE:allergies=NKDA]",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)

        result = await intake_node(state, mock_gateway, phi)
        tracker_data = result["intake_tracker"]
        assert tracker_data["allergies_complete"] is True
        assert tracker_data["phase"] == "social_family"

    @pytest.mark.asyncio
    async def test_social_family_advances_to_summary(self, mock_gateway, phi):
        """When social_family is completed and demographics present, phase advances to summary."""
        from app.agents.tools.intake_tracker import IntakeTracker

        tracker = IntakeTracker()
        tracker.phase = "social_family"
        tracker.age = "45"
        tracker.gender = "male"
        tracker.cc = "headache"
        tracker.red_flag_screening_done = True
        for f in ["onset", "location", "duration", "character", "aggravating", "severity"]:
            tracker.hpi[f] = "value"
        tracker.ros_systems["neurological"] = "headaches"
        tracker.ros_systems["constitutional"] = "no fever"
        tracker.pmh = "none"
        tracker.pmh_complete = True
        tracker.medications = "paracetamol"
        tracker.medications_complete = True
        tracker.allergies = "NKDA"
        tracker.allergies_complete = True

        state = _make_state(
            messages=[HumanMessage(content="khong hut thuoc, khong uong ruou")],
            intake_tracker=tracker.to_dict(),
        )

        response = LLMResponse(
            content="[INTAKE:risk_level=low] [INTAKE:risk_reasoning=routine] Da ghi nhan. [INTAKE:social_family=khong hut thuoc, khong uong ruou]",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)

        result = await intake_node(state, mock_gateway, phi)
        tracker_data = result["intake_tracker"]
        assert tracker_data["social_family_complete"] is True
        assert tracker_data["phase"] == "summary"
