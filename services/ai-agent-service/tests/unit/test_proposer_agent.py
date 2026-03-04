"""Tests for Proposer Agent — Treatment recommendations."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.proposer_agent import (
    _build_screening_context,
    _parse_proposer_response,
    proposer_node,
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
    """Create a test CareFlowState with screening data."""
    state = {
        "patient_id": "patient-1",
        "case_id": "case-1",
        "organization_id": "org-1",
        "messages": [
            HumanMessage(content="Tôi bị đau bụng phải dưới 2 ngày"),
        ],
        "intake_data": {"chief_complaint": "Đau bụng phải dưới"},
        "intake_complete": True,
        "is_emergency": False,
        "detected_language": "vi",
        "cultural_expressions": [],
        "screening_result": {
            "severity": "urgent",
            "clinical_impression": "Nghi ngờ viêm ruột thừa cấp",
            "key_findings": ["Đau bụng phải dưới", "Mức độ 7/10"],
            "red_flags": ["rebound tenderness"],
        },
        "severity": "urgent",
        "differential_diagnoses": [
            {"name": "Acute Appendicitis", "confidence": 65, "reasoning": "RLQ pain"},
            {"name": "Ovarian Cyst", "confidence": 20, "reasoning": "RLQ pain"},
            {"name": "Gastroenteritis", "confidence": 15, "reasoning": "Common cause"},
        ],
        "confidence_score": 0.65,
        "order_recommendations": [],
        "drug_interactions": [],
        "allergy_alerts": [],
        "critic_issues": [],
    }
    state.update(overrides)
    return state


def _proposer_response():
    """Create a mock proposer LLM response."""
    data = {
        "medications": [
            {
                "drug": "Acetaminophen",
                "drug_vi": "Paracetamol",
                "dosage": "500mg",
                "frequency": "Every 6 hours",
                "frequency_vi": "Mỗi 6 giờ",
                "duration": "48 hours",
                "route": "oral",
                "rationale": "Pain management pending diagnosis",
            }
        ],
        "lab_orders": [
            {
                "test_name": "CBC",
                "test_name_vi": "Công thức máu",
                "rationale": "Rule out infection",
                "urgency": "stat",
            },
            {
                "test_name": "CMP",
                "test_name_vi": "Metabolic panel",
                "rationale": "Check organ function",
                "urgency": "stat",
            },
        ],
        "imaging": [
            {
                "type": "Abdominal Ultrasound",
                "type_vi": "Siêu âm ổ bụng",
                "rationale": "Rule out appendicitis",
                "urgency": "stat",
            }
        ],
        "monitoring_plan": {
            "follow_up_interval": "24 hours",
            "follow_up_interval_vi": "Sau 24 giờ",
            "warning_signs": ["Fever > 38.5C", "Worsening pain"],
            "warning_signs_vi": ["Sốt > 38.5°C", "Đau tăng"],
            "instructions": "Rest, clear liquids, monitor temperature",
            "instructions_vi": "Nghỉ ngơi, uống nước, theo dõi nhiệt độ",
        },
        "drug_interactions": [],
        "allergy_alerts": [],
    }
    return json.dumps(data, ensure_ascii=False)


# === Test _build_screening_context ===


class TestBuildScreeningContext:
    def test_includes_severity(self):
        state = _make_state()
        context = _build_screening_context(state)
        assert "SEVERITY: urgent" in context

    def test_includes_clinical_impression(self):
        state = _make_state()
        context = _build_screening_context(state)
        assert "viêm ruột thừa" in context

    def test_includes_differential_diagnoses(self):
        state = _make_state()
        context = _build_screening_context(state)
        assert "Acute Appendicitis" in context
        assert "65%" in context

    def test_includes_red_flags(self):
        state = _make_state()
        context = _build_screening_context(state)
        assert "rebound tenderness" in context


# === Test _parse_proposer_response ===


class TestParseProposerResponse:
    def test_parses_valid_json(self):
        response = _proposer_response()
        parsed = _parse_proposer_response(response)
        assert len(parsed["medications"]) == 1
        assert len(parsed["lab_orders"]) == 2
        assert len(parsed["imaging"]) == 1

    def test_fallback_on_invalid_json(self):
        parsed = _parse_proposer_response("Not valid JSON")
        assert parsed["medications"] == []
        assert parsed["lab_orders"] == []


# === Test proposer_node ===


class TestProposerNode:
    @pytest.mark.asyncio
    async def test_returns_order_recommendations(self, mock_gateway, phi):
        state = _make_state()
        mock_response = LLMResponse(
            content=_proposer_response(),
            model="gpt-4",
            usage={"prompt_tokens": 300, "completion_tokens": 200, "total_tokens": 500},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await proposer_node(state, mock_gateway, phi)
            # 1 medication + 2 labs + 1 imaging + 1 monitoring = 5 recommendations
            assert len(result["order_recommendations"]) == 5
            types = [r["type"] for r in result["order_recommendations"]]
            assert "medication" in types
            assert "lab" in types
            assert "imaging" in types
            assert "monitoring" in types

    @pytest.mark.asyncio
    async def test_includes_messages(self, mock_gateway, phi):
        state = _make_state()
        mock_response = LLMResponse(
            content=_proposer_response(),
            model="gpt-4",
            usage={"prompt_tokens": 300, "completion_tokens": 200, "total_tokens": 500},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await proposer_node(state, mock_gateway, phi)
            assert len(result["messages"]) == 1
            assert isinstance(result["messages"][0], AIMessage)

    @pytest.mark.asyncio
    async def test_includes_critic_feedback_in_rerun(self, mock_gateway, phi):
        state = _make_state(
            critic_issues=[
                {
                    "severity": "critical",
                    "description": "Missing CBC order",
                    "recommendation": "Add CBC",
                }
            ]
        )
        mock_response = LLMResponse(
            content=_proposer_response(),
            model="gpt-4",
            usage={"prompt_tokens": 300, "completion_tokens": 200, "total_tokens": 500},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ) as mock_call:
            await proposer_node(state, mock_gateway, phi)
            # Verify critic feedback was included in the LLM messages
            call_args = mock_call.call_args
            messages = call_args[0][1]  # Second positional arg is messages
            system_content = messages[0]["content"]
            assert "PREVIOUS CRITIC FEEDBACK" in system_content
            assert "Missing CBC order" in system_content
