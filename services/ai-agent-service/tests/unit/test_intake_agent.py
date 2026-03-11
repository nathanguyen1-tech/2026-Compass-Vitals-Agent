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
    async def test_legacy_emergency_detected_treated_as_suspected(self, mock_gateway, phi):
        """Legacy emergency_detected marker should be treated as suspected (not instant trigger)."""
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
        # Should NOT be emergency yet — treated as suspected
        assert result["is_emergency"] is False
        # Tracker should have suspected_emergency set
        tracker_data = result["intake_tracker"]
        assert tracker_data["suspected_emergency"] is not None
        assert tracker_data["suspected_emergency"]["reason"] == "probable_acs_indirect_description"

    @pytest.mark.asyncio
    async def test_emergency_suspected_does_not_trigger(self, mock_gateway, phi):
        """emergency_suspected marker should NOT trigger emergency — starts confirmation."""
        response = LLMResponse(
            content=(
                "Ban dang bi dau nguc NGAY BAY GIO khong? "
                "[INTAKE:emergency_suspected=chest_pain_description]"
            ),
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        state = _make_state(
            messages=[HumanMessage(content="toi bi dau nguc")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False
        assert result["intake_tracker"]["suspected_emergency"] is not None

    @pytest.mark.asyncio
    async def test_emergency_confirmed_after_enough_questions(self, mock_gateway, phi):
        """emergency_confirmed should trigger after 2+ confirmation questions."""
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
            # Pre-seed tracker with suspected_emergency and 2 questions asked
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
                    "confirmation_questions_asked": 1,  # Will be incremented to 2 in Step 1b
                    "source": "llm",
                },
            },
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is True

    @pytest.mark.asyncio
    async def test_emergency_confirmed_too_early_keeps_investigating(self, mock_gateway, phi):
        """emergency_confirmed with < 2 questions should NOT trigger — keep investigating."""
        response = LLMResponse(
            content=(
                "This sounds serious. [INTAKE:emergency_confirmed=acs_possible]"
            ),
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        state = _make_state(
            messages=[HumanMessage(content="vang toi dau nguc")],
            intake_tracker={
                "phase": "cc",
                "complaint_category": None,
                "message_count": 1,
                "cc": None,
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
                    "reason": "chest_pain",
                    "confirmation_questions_asked": 0,  # Will be incremented to 1
                    "source": "llm",
                },
            },
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)
        result = await intake_node(state, mock_gateway, phi)
        # Should NOT be emergency — not enough questions yet
        assert result["is_emergency"] is False

    @pytest.mark.asyncio
    async def test_emergency_cleared_continues_normal(self, mock_gateway, phi):
        """emergency_cleared should clear suspected_emergency and continue."""
        response = LLMResponse(
            content=(
                "Good, that sounds like it resolved. Let's continue. "
                "[INTAKE:emergency_cleared=mild_past_resolved]"
            ),
            model="gpt-4o-mini",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
        state = _make_state(
            messages=[HumanMessage(content="khong, hom qua thoi, bay gio het roi")],
            intake_tracker={
                "phase": "hpi",
                "complaint_category": None,
                "message_count": 3,
                "cc": "chest discomfort",
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
                    "reason": "chest_pain_possible",
                    "confirmation_questions_asked": 1,
                    "source": "llm",
                },
            },
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False
        assert result["intake_tracker"]["suspected_emergency"] is None

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
    async def test_chest_pain_not_instant_goes_to_llm(self, mock_gateway, phi, mock_response):
        """'dau nguc' is NOT in INSTANT list — should go through LLM, not instant trigger."""
        state = _make_state(
            messages=[HumanMessage(content="toi bi đau ngực nhẹ")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        # Should NOT be instant emergency — LLM handles this
        assert result["is_emergency"] is False
