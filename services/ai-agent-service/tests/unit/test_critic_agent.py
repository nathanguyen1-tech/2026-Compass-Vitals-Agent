"""Tests for Critic Agent — Safety validation of treatment orders."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from langchain_core.messages import AIMessage

from app.agents.critic_agent import (
    _build_orders_context,
    _parse_critic_response,
    critic_node,
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
    """Create a test CareFlowState with proposer data."""
    state = {
        "patient_id": "patient-1",
        "case_id": "case-1",
        "organization_id": "org-1",
        "messages": [],
        "intake_data": {"chief_complaint": "abdominal pain"},
        "intake_complete": True,
        "is_emergency": False,
        "detected_language": "vi",
        "cultural_expressions": [],
        "screening_result": {
            "severity": "urgent",
            "clinical_impression": "Suspected appendicitis",
            "key_findings": ["RLQ pain"],
            "red_flags": [],
        },
        "severity": "urgent",
        "differential_diagnoses": [
            {"name": "Acute Appendicitis", "confidence": 65},
        ],
        "confidence_score": 0.65,
        "order_recommendations": [
            {
                "type": "medication",
                "drug": "Acetaminophen",
                "dosage": "500mg",
                "frequency": "Every 6 hours",
                "duration": "48 hours",
                "route": "oral",
                "rationale": "Pain management",
            },
            {
                "type": "lab",
                "test_name": "CBC",
                "rationale": "Rule out infection",
                "urgency": "stat",
            },
            {
                "type": "imaging",
                "imaging_type": "Abdominal Ultrasound",
                "rationale": "Rule out appendicitis",
                "urgency": "stat",
            },
        ],
        "drug_interactions": [],
        "allergy_alerts": [],
        "critic_validation": None,
        "critic_approved": False,
        "critic_issues": [],
        "_critic_loops": 0,
    }
    state.update(overrides)
    return state


def _critic_response(status="approved", issues=None, safety_score=92):
    """Create a mock critic LLM response."""
    if issues is None:
        issues = []
    data = {
        "status": status,
        "overall_safety_score": safety_score,
        "summary": "All orders validated successfully" if status == "approved" else "Issues found",
        "summary_vi": "Tất cả đơn thuốc đã được xác nhận" if status == "approved" else "Phát hiện vấn đề",
        "issues": issues,
        "approved_orders": ["Acetaminophen 500mg q6h", "CBC stat", "Abdominal US"],
        "modifications_required": [],
    }
    return json.dumps(data, ensure_ascii=False)


# === Test _build_orders_context ===


class TestBuildOrdersContext:
    def test_includes_severity(self):
        state = _make_state()
        context = _build_orders_context(state)
        assert "SEVERITY: urgent" in context

    def test_includes_orders(self):
        state = _make_state()
        context = _build_orders_context(state)
        assert "ORDERS TO VALIDATE:" in context
        assert "Acetaminophen" in context
        assert "CBC" in context

    def test_includes_differential_diagnoses(self):
        state = _make_state()
        context = _build_orders_context(state)
        assert "Acute Appendicitis" in context

    def test_includes_flagged_interactions(self):
        state = _make_state(
            drug_interactions=[
                {
                    "drug_pair": ["DrugA", "DrugB"],
                    "severity": "major",
                    "description": "Dangerous combo",
                }
            ]
        )
        context = _build_orders_context(state)
        assert "FLAGGED DRUG INTERACTIONS:" in context
        assert "DrugA + DrugB" in context


# === Test _parse_critic_response ===


class TestParseCriticResponse:
    def test_parses_valid_json(self):
        response = _critic_response(status="approved")
        parsed = _parse_critic_response(response)
        assert parsed["status"] == "approved"
        assert parsed["overall_safety_score"] == 92

    def test_parses_rejected(self):
        issues = [
            {
                "severity": "critical",
                "category": "drug_interaction",
                "description": "Dangerous interaction",
                "recommendation": "Remove drug",
            }
        ]
        response = _critic_response(status="rejected", issues=issues, safety_score=30)
        parsed = _parse_critic_response(response)
        assert parsed["status"] == "rejected"
        assert len(parsed["issues"]) == 1
        assert parsed["issues"][0]["severity"] == "critical"

    def test_fallback_on_invalid_json(self):
        parsed = _parse_critic_response("Not valid JSON")
        assert parsed["status"] == "needs_modification"
        assert parsed["overall_safety_score"] == 50


# === Test critic_node ===


class TestCriticNodeApproved:
    @pytest.mark.asyncio
    async def test_approved_sets_critic_approved_true(self, mock_gateway, phi):
        state = _make_state()
        mock_response = LLMResponse(
            content=_critic_response(status="approved"),
            model="gpt-4",
            usage={"prompt_tokens": 300, "completion_tokens": 150, "total_tokens": 450},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await critic_node(state, mock_gateway, phi)
            assert result["critic_approved"] is True
            assert result["critic_validation"]["status"] == "approved"
            assert result["needs_human_review"] is False

    @pytest.mark.asyncio
    async def test_approved_returns_confidence_score(self, mock_gateway, phi):
        state = _make_state()
        mock_response = LLMResponse(
            content=_critic_response(status="approved", safety_score=92),
            model="gpt-4",
            usage={"prompt_tokens": 300, "completion_tokens": 150, "total_tokens": 450},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await critic_node(state, mock_gateway, phi)
            assert result["confidence_score"] == 0.92


class TestCriticNodeRejected:
    @pytest.mark.asyncio
    async def test_rejected_sets_critic_approved_false(self, mock_gateway, phi):
        state = _make_state()
        issues = [
            {
                "severity": "critical",
                "category": "drug_interaction",
                "description": "Dangerous interaction between DrugA and DrugB",
                "recommendation": "Remove DrugA",
            }
        ]
        mock_response = LLMResponse(
            content=_critic_response(status="rejected", issues=issues, safety_score=30),
            model="gpt-4",
            usage={"prompt_tokens": 300, "completion_tokens": 150, "total_tokens": 450},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await critic_node(state, mock_gateway, phi)
            assert result["critic_approved"] is False
            assert len(result["critic_issues"]) == 1
            assert result["needs_human_review"] is True

    @pytest.mark.asyncio
    async def test_needs_modification(self, mock_gateway, phi):
        state = _make_state()
        issues = [
            {
                "severity": "warning",
                "category": "dosage",
                "description": "Dosage may be too high",
                "recommendation": "Consider reducing to 250mg",
            }
        ]
        mock_response = LLMResponse(
            content=_critic_response(status="needs_modification", issues=issues, safety_score=75),
            model="gpt-4",
            usage={"prompt_tokens": 300, "completion_tokens": 150, "total_tokens": 450},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await critic_node(state, mock_gateway, phi)
            assert result["critic_approved"] is False
            assert result["critic_issues"][0]["severity"] == "warning"


class TestCriticNodeLoopTracking:
    @pytest.mark.asyncio
    async def test_increments_loop_count(self, mock_gateway, phi):
        state = _make_state(_critic_loops=0)
        mock_response = LLMResponse(
            content=_critic_response(status="approved"),
            model="gpt-4",
            usage={"prompt_tokens": 300, "completion_tokens": 150, "total_tokens": 450},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await critic_node(state, mock_gateway, phi)
            assert result["_critic_loops"] == 1

    @pytest.mark.asyncio
    async def test_needs_human_review_after_max_loops(self, mock_gateway, phi):
        state = _make_state(_critic_loops=1)  # Will become 2 after this run
        mock_response = LLMResponse(
            content=_critic_response(status="approved"),
            model="gpt-4",
            usage={"prompt_tokens": 300, "completion_tokens": 150, "total_tokens": 450},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await critic_node(state, mock_gateway, phi)
            assert result["_critic_loops"] == 2
            assert result["needs_human_review"] is True

    @pytest.mark.asyncio
    async def test_includes_messages(self, mock_gateway, phi):
        state = _make_state()
        mock_response = LLMResponse(
            content=_critic_response(),
            model="gpt-4",
            usage={"prompt_tokens": 300, "completion_tokens": 150, "total_tokens": 450},
            finish_reason="stop",
        )
        with patch.object(
            mock_gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await critic_node(state, mock_gateway, phi)
            assert len(result["messages"]) == 1
            assert isinstance(result["messages"][0], AIMessage)
