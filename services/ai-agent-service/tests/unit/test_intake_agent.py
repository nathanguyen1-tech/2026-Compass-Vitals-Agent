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
    async def test_detects_emergency_dau_nguc(self, mock_gateway, phi):
        state = _make_state(
            messages=[HumanMessage(content="Tôi bị đau ngực rất nặng, khó thở")]
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
    """Tests for Tier 3 LLM-detected emergency via [INTAKE:emergency_detected=...] marker."""

    @pytest.mark.asyncio
    async def test_llm_emergency_marker_triggers_emergency(self, mock_gateway, phi):
        """When LLM emits emergency_detected marker, intake should return emergency."""
        llm_response_with_marker = LLMResponse(
            content=(
                "I understand you're feeling pressure on your chest. "
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
        assert result["is_emergency"] is True
        assert "KHẨN CẤP" in result["messages"][0].content or "EMERGENCY" in result["messages"][0].content

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
    """Negated emergency keywords should not trigger emergency in intake_node."""

    @pytest.mark.asyncio
    async def test_negated_chest_pain_not_emergency(self, mock_gateway, phi, mock_response):
        """'toi khong bi dau nguc' should NOT trigger emergency."""
        state = _make_state(
            messages=[HumanMessage(content="toi không bị đau ngực")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False
