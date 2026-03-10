"""Tests for Care Flow Graph — LangGraph orchestration of Screening → Proposer → Critic."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.care_flow_graph import build_care_flow_graph, route_after_critic
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


def _make_initial_state():
    """Create an initial CareFlowState after intake is complete."""
    return {
        "patient_id": "patient-1",
        "case_id": "case-1",
        "organization_id": "org-1",
        "messages": [
            HumanMessage(content="abdominal pain for 2 days"),
            AIMessage(content="Could you describe the pain?"),
            HumanMessage(content="sharp, 7/10, right lower"),
        ],
        "intake_data": {
            "chief_complaint": "abdominal pain",
            "onset": "2 days ago",
            "location": "right lower abdomen",
            "severity": "7/10",
        },
        "intake_complete": True,
        "is_emergency": False,
        "detected_language": "en",
        "cultural_expressions": [],
        "screening_result": None,
        "severity": None,
        "differential_diagnoses": [],
        "confidence_score": None,
        "order_recommendations": [],
        "drug_interactions": [],
        "allergy_alerts": [],
        "critic_validation": None,
        "critic_approved": False,
        "critic_issues": [],
        "_critic_loops": 0,
        "confidence_breakdown": None,
        "current_station": 0,
        "flow_type": None,
        "needs_human_review": False,
        "human_review_reason": None,
        "created_at": "2026-03-01T00:00:00Z",
        "updated_at": "2026-03-01T00:00:00Z",
        "correlation_id": "corr-1",
    }


def _screening_json():
    return json.dumps({
        "severity": "urgent",
        "clinical_impression": "Suspected appendicitis",
        "key_findings": ["RLQ pain", "7/10 severity"],
        "red_flags": [],
        "differential_diagnoses": [
            {"name": "Acute Appendicitis", "name_vi": "Viêm ruột thừa", "confidence": 65, "reasoning": "RLQ pain", "red_flags": []},
            {"name": "Ovarian Cyst", "name_vi": "U nang buồng trứng", "confidence": 20, "reasoning": "RLQ pain", "red_flags": []},
            {"name": "Gastroenteritis", "name_vi": "Viêm dạ dày", "confidence": 15, "reasoning": "Common", "red_flags": []},
        ],
        "recommended_urgency": "Within 24 hours",
    })


def _proposer_json():
    return json.dumps({
        "medications": [{"drug": "Acetaminophen", "drug_vi": "Paracetamol", "dosage": "500mg", "frequency": "q6h", "frequency_vi": "Mỗi 6 giờ", "duration": "48h", "route": "oral", "rationale": "Pain management"}],
        "lab_orders": [{"test_name": "CBC", "test_name_vi": "Công thức máu", "rationale": "Rule out infection", "urgency": "stat"}],
        "imaging": [{"type": "Abdominal US", "type_vi": "Siêu âm bụng", "rationale": "Rule out appendicitis", "urgency": "stat"}],
        "monitoring_plan": {"follow_up_interval": "24h", "warning_signs": ["Fever"], "instructions": "Rest"},
        "drug_interactions": [],
        "allergy_alerts": [],
    })


def _critic_approved_json():
    return json.dumps({
        "status": "approved",
        "overall_safety_score": 92,
        "summary": "All orders safe",
        "issues": [],
        "approved_orders": ["Acetaminophen", "CBC", "Abdominal US"],
        "modifications_required": [],
    })


def _critic_rejected_json():
    return json.dumps({
        "status": "rejected",
        "overall_safety_score": 30,
        "summary": "Critical issue found",
        "issues": [{"severity": "critical", "category": "dosage", "description": "Dosage too high", "recommendation": "Reduce to 250mg"}],
        "approved_orders": [],
        "modifications_required": [{"original": "Acetaminophen 500mg", "suggested": "Acetaminophen 250mg", "reason": "Too high"}],
    })


def _make_llm_response(content):
    return LLMResponse(
        content=content,
        model="gpt-4",
        usage={"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300},
        finish_reason="stop",
    )


# === Test route_after_critic ===


class TestRouteAfterCritic:
    def test_returns_end_when_approved(self):
        state = {"critic_approved": True, "_critic_loops": 1}
        assert route_after_critic(state) == "__end__"

    def test_returns_proposer_when_rejected(self):
        state = {"critic_approved": False, "_critic_loops": 1, "case_id": "c1"}
        assert route_after_critic(state) == "proposer"

    def test_returns_end_when_max_loops(self):
        state = {"critic_approved": False, "_critic_loops": 2, "case_id": "c1"}
        assert route_after_critic(state) == "__end__"

    def test_returns_end_when_over_max_loops(self):
        state = {"critic_approved": False, "_critic_loops": 5, "case_id": "c1"}
        assert route_after_critic(state) == "__end__"


# === Test build_care_flow_graph ===


class TestBuildCareFlowGraph:
    def test_graph_compiles(self, mock_gateway, phi):
        graph = build_care_flow_graph(mock_gateway, phi)
        assert graph is not None


# === Test full flow ===


class TestFullFlow:
    @pytest.mark.asyncio
    async def test_approved_flow(self, mock_gateway, phi):
        """Test full pipeline: screening → proposer → critic (approved)."""
        call_count = 0

        async def mock_call(provider, messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_llm_response(_screening_json())
            elif call_count == 2:
                return _make_llm_response(_proposer_json())
            else:
                return _make_llm_response(_critic_approved_json())

        graph = build_care_flow_graph(mock_gateway, phi)
        state = _make_initial_state()

        with patch.object(mock_gateway, "_call_with_retry", side_effect=mock_call):
            result = await graph.ainvoke(state)

        assert result["severity"] == "urgent"
        assert result["critic_approved"] is True
        assert len(result["differential_diagnoses"]) == 3
        assert len(result["order_recommendations"]) > 0
        assert call_count == 3  # screening + proposer + critic

    @pytest.mark.asyncio
    async def test_rejected_then_approved_flow(self, mock_gateway, phi):
        """Test critic reject → proposer re-run → critic approve."""
        call_count = 0

        async def mock_call(provider, messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_llm_response(_screening_json())
            elif call_count == 2:
                return _make_llm_response(_proposer_json())
            elif call_count == 3:
                return _make_llm_response(_critic_rejected_json())
            elif call_count == 4:
                return _make_llm_response(_proposer_json())  # Re-run
            else:
                return _make_llm_response(_critic_approved_json())  # Approve

        graph = build_care_flow_graph(mock_gateway, phi)
        state = _make_initial_state()

        with patch.object(mock_gateway, "_call_with_retry", side_effect=mock_call):
            result = await graph.ainvoke(state)

        assert result["critic_approved"] is True
        assert result["_critic_loops"] == 2
        assert call_count == 5  # screening + proposer + critic(reject) + proposer + critic(approve)
