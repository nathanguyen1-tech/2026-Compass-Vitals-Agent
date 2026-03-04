"""Tests for Screening Agent — Clinical assessment and severity classification."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.screening_agent import (
    _build_intake_summary,
    _parse_screening_response,
    screening_node,
)
from app.domain.services.llm_gateway import LLMGateway, LLMResponse
from app.domain.services.phi_deidentifier import PHIDeidentifier


@pytest.fixture
def phi():
    key = Fernet.generate_key().decode()
    return PHIDeidentifier(encryption_key=key)


@pytest.fixture
def mock_gateway(phi):
    return LLMGateway(
        openai_api_key="test-key",
        phi_deidentifier=phi,
        primary_model="gpt-4",
        screening_model="gpt-4o-mini",
    )


def _make_state(**overrides):
    """Create a test CareFlowState with intake data."""
    state = {
        "patient_id": "patient-1",
        "case_id": "case-1",
        "organization_id": "org-1",
        "messages": [
            HumanMessage(content="Tôi bị đau bụng phải dưới 2 ngày"),
            AIMessage(content="Bạn có thể mô tả cơn đau?"),
            HumanMessage(content="Đau kiểu chuốc, mức độ 7/10"),
        ],
        "intake_data": {
            "chief_complaint": "Đau bụng phải dưới",
            "onset": "2 ngày trước",
            "location": "Bụng phải dưới",
            "duration": "2 ngày",
            "character": "Đau chuốc",
            "severity": "7/10",
        },
        "intake_complete": True,
        "is_emergency": False,
        "detected_language": "vi",
        "cultural_expressions": [],
        "screening_result": None,
        "severity": None,
        "differential_diagnoses": [],
        "confidence_score": None,
    }
    state.update(overrides)
    return state


def _screening_response(severity="urgent", diagnoses=None):
    """Create a mock screening LLM response."""
    if diagnoses is None:
        diagnoses = [
            {
                "name": "Acute Appendicitis",
                "name_vi": "Viêm ruột thừa cấp",
                "confidence": 65,
                "reasoning": "Right lower quadrant pain, acute onset",
                "red_flags": ["rebound tenderness"],
            },
            {
                "name": "Ovarian Cyst",
                "name_vi": "U nang buồng trứng",
                "confidence": 20,
                "reasoning": "RLQ pain in reproductive age",
                "red_flags": [],
            },
            {
                "name": "Gastroenteritis",
                "name_vi": "Viêm dạ dày ruột",
                "confidence": 15,
                "reasoning": "Abdominal pain, common cause",
                "red_flags": [],
            },
        ]

    data = {
        "severity": severity,
        "clinical_impression": "Đau bụng phải dưới cấp tính, nghi ngờ viêm ruột thừa",
        "key_findings": ["Đau bụng phải dưới", "Cấp tính 2 ngày", "Mức độ 7/10"],
        "red_flags": ["rebound tenderness"] if severity != "routine" else [],
        "differential_diagnoses": diagnoses,
        "recommended_urgency": "Cần khám trong 24 giờ",
    }
    return json.dumps(data, ensure_ascii=False)


# === Test _build_intake_summary ===


class TestBuildIntakeSummary:
    def test_includes_intake_data(self):
        state = _make_state()
        summary = _build_intake_summary(state)
        assert "STRUCTURED INTAKE DATA:" in summary
        assert "chief_complaint" in summary
        assert "Đau bụng phải dưới" in summary

    def test_includes_conversation_history(self):
        state = _make_state()
        summary = _build_intake_summary(state)
        assert "CONVERSATION HISTORY:" in summary
        assert "[Patient]:" in summary
        assert "[Intake Agent]:" in summary

    def test_includes_cultural_expressions(self):
        state = _make_state(
            cultural_expressions=[
                {"original": "bị nóng trong", "medical_meaning": "Internal inflammation"}
            ]
        )
        summary = _build_intake_summary(state)
        assert "CULTURAL EXPRESSIONS DETECTED:" in summary
        assert "bị nóng trong" in summary

    def test_handles_empty_state(self):
        state = _make_state(intake_data=None, messages=[], cultural_expressions=[])
        summary = _build_intake_summary(state)
        assert summary == "No intake data available."


# === Test _parse_screening_response ===


class TestParseScreeningResponse:
    def test_parses_valid_json(self):
        response = _screening_response()
        parsed = _parse_screening_response(response)
        assert parsed["severity"] == "urgent"
        assert len(parsed["differential_diagnoses"]) == 3

    def test_strips_markdown_fences(self):
        response = "```json\n" + _screening_response() + "\n```"
        parsed = _parse_screening_response(response)
        assert parsed["severity"] == "urgent"

    def test_fallback_on_invalid_json(self):
        parsed = _parse_screening_response("This is not JSON at all")
        assert parsed["severity"] == "routine"
        assert parsed["clinical_impression"] == "This is not JSON at all"
        assert parsed["differential_diagnoses"] == []


# === Test screening_node ===


class TestScreeningNodeEmergencyBypass:
    @pytest.mark.asyncio
    async def test_bypasses_when_emergency_flagged(self, mock_gateway, phi):
        state = _make_state(is_emergency=True)
        result = await screening_node(state, mock_gateway, phi)
        assert result["severity"] == "emergency"
        assert result["screening_result"]["severity"] == "emergency"
        assert result["confidence_score"] == 1.0


class TestScreeningNodeNormalFlow:
    @pytest.mark.asyncio
    async def test_returns_severity(self, mock_gateway, phi):
        state = _make_state()
        mock_response = LLMResponse(
            content=_screening_response(severity="urgent"),
            model="gpt-4",
            usage={"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await screening_node(state, mock_gateway, phi)
            assert result["severity"] == "urgent"
            assert len(result["differential_diagnoses"]) == 3

    @pytest.mark.asyncio
    async def test_returns_confidence_score(self, mock_gateway, phi):
        state = _make_state()
        mock_response = LLMResponse(
            content=_screening_response(),
            model="gpt-4",
            usage={"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await screening_node(state, mock_gateway, phi)
            assert result["confidence_score"] == 0.65  # 65/100

    @pytest.mark.asyncio
    async def test_emergency_severity_sets_is_emergency(self, mock_gateway, phi):
        state = _make_state()
        mock_response = LLMResponse(
            content=_screening_response(severity="emergency"),
            model="gpt-4",
            usage={"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await screening_node(state, mock_gateway, phi)
            assert result["severity"] == "emergency"
            assert result["is_emergency"] is True

    @pytest.mark.asyncio
    async def test_routine_severity(self, mock_gateway, phi):
        state = _make_state()
        mock_response = LLMResponse(
            content=_screening_response(severity="routine"),
            model="gpt-4",
            usage={"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await screening_node(state, mock_gateway, phi)
            assert result["severity"] == "routine"
            assert result["is_emergency"] is False

    @pytest.mark.asyncio
    async def test_includes_messages(self, mock_gateway, phi):
        state = _make_state()
        mock_response = LLMResponse(
            content=_screening_response(),
            model="gpt-4",
            usage={"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await screening_node(state, mock_gateway, phi)
            assert len(result["messages"]) == 1
            assert isinstance(result["messages"][0], AIMessage)
