"""Tests for SOAP Note Generator — GPT-4 clinical narrative."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.soap_note_generator import (
    _build_soap_context,
    _parse_soap_response,
    generate_soap_note,
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
    )


def _soap_response(safety_concerns=None):
    """Create a mock SOAP LLM JSON response."""
    data = {
        "subjective": {
            "content": "Patient presents with acute right lower quadrant abdominal pain, onset 2 days ago.",
            "content_vi": "Benh nhan den voi dau bung duoi ben phai cap tinh, khoi phat 2 ngay truoc.",
        },
        "objective": {
            "content": "No vital signs available — telemedicine encounter. Screening identified RLQ tenderness.",
            "content_vi": "Khong co sinh hieu — kham tu xa. Sang loc xac dinh dau RLQ.",
        },
        "assessment": {
            "content": "Clinical impression: Suspected acute appendicitis. Severity: urgent. "
            "Differential: Acute Appendicitis (65%), Mesenteric Lymphadenitis (20%).",
            "content_vi": "An tuong lam sang: Nghi ngo viem ruot thua cap. Muc do: khan cap.",
        },
        "plan": {
            "content": "1. Acetaminophen 500mg PO q6h PRN pain. 2. CBC with differential (urgent). "
            "3. CT Abdomen/Pelvis with contrast (urgent). Critic validation: Approved (safety score 92/100).",
            "content_vi": "1. Acetaminophen 500mg uong moi 6 gio khi dau. 2. CTM (khan). "
            "3. CT bung/chau co can quang (khan).",
        },
        "safety_concerns": safety_concerns or [],
    }
    return json.dumps(data, ensure_ascii=False)


def _make_state(**overrides):
    """Create a complete post-flow CareFlowState."""
    state = {
        "patient_id": "patient-1",
        "case_id": "case-1",
        "organization_id": "org-1",
        "messages": [
            HumanMessage(content="Toi bi dau bung"),
            AIMessage(content="Ban bi dau o vi tri nao?"),
        ],
        "intake_data": {
            "chief_complaint": "abdominal pain",
            "onset": "2 days ago",
            "severity": "7/10",
        },
        "intake_complete": True,
        "intake_tracker": None,
        "is_emergency": False,
        "detected_language": "vi",
        "cultural_expressions": [
            {"original": "nong trong", "medical_meaning": "internal heat"}
        ],
        "screening_result": {
            "severity": "urgent",
            "clinical_impression": "Suspected appendicitis",
            "key_findings": ["RLQ pain", "rebound tenderness"],
            "red_flags": [],
            "differential_diagnoses": [],
        },
        "severity": "urgent",
        "differential_diagnoses": [
            {
                "name": "Acute Appendicitis",
                "name_vi": "Viem ruot thua cap",
                "confidence": 65,
                "reasoning": "RLQ pain with rebound",
            },
            {
                "name": "Mesenteric Lymphadenitis",
                "name_vi": "Viem hach mac treo",
                "confidence": 20,
                "reasoning": "Less likely",
            },
        ],
        "confidence_score": 0.65,
        "order_recommendations": [
            {
                "type": "medication",
                "drug": "Acetaminophen",
                "dosage": "500mg",
                "frequency": "q6h",
            },
            {
                "type": "lab",
                "test_name": "CBC",
                "rationale": "Evaluate for infection",
                "urgency": "urgent",
            },
        ],
        "drug_interactions": [],
        "allergy_alerts": [],
        "critic_validation": {
            "status": "approved",
            "overall_safety_score": 92,
            "summary": "All orders validated",
            "issues": [],
        },
        "critic_approved": True,
        "critic_issues": [],
        "needs_human_review": False,
        "human_review_reason": None,
    }
    state.update(overrides)
    return state


# ── _build_soap_context ──


class TestBuildSoapContext:
    def test_includes_intake_data(self):
        state = _make_state()
        ctx = _build_soap_context(state)
        assert "chief_complaint: abdominal pain" in ctx
        assert "onset: 2 days ago" in ctx

    def test_includes_screening_result(self):
        state = _make_state()
        ctx = _build_soap_context(state)
        assert "Suspected appendicitis" in ctx
        assert "RLQ pain" in ctx

    def test_includes_differential_diagnoses(self):
        state = _make_state()
        ctx = _build_soap_context(state)
        assert "Acute Appendicitis" in ctx
        assert "65%" in ctx

    def test_includes_order_recommendations(self):
        state = _make_state()
        ctx = _build_soap_context(state)
        assert "Acetaminophen" in ctx
        assert "CBC" in ctx

    def test_includes_critic_validation(self):
        state = _make_state()
        ctx = _build_soap_context(state)
        assert "approved" in ctx
        assert "92" in ctx

    def test_includes_cultural_expressions(self):
        state = _make_state()
        ctx = _build_soap_context(state)
        assert "nong trong" in ctx
        assert "internal heat" in ctx

    def test_includes_conversation_excerpts(self):
        state = _make_state()
        ctx = _build_soap_context(state)
        assert "[Patient]:" in ctx
        assert "dau bung" in ctx

    def test_includes_drug_interactions(self):
        state = _make_state(
            drug_interactions=[
                {
                    "drug_pair": ["DrugA", "DrugB"],
                    "severity": "major",
                    "description": "Serious interaction",
                }
            ]
        )
        ctx = _build_soap_context(state)
        assert "DrugA + DrugB" in ctx
        assert "major" in ctx

    def test_includes_emergency_flag(self):
        state = _make_state(is_emergency=True)
        ctx = _build_soap_context(state)
        assert "EMERGENCY CASE" in ctx

    def test_includes_human_review_flag(self):
        state = _make_state(
            needs_human_review=True,
            human_review_reason="Critic rejected: 2 critical issues",
        )
        ctx = _build_soap_context(state)
        assert "NEEDS HUMAN REVIEW" in ctx
        assert "Critic rejected" in ctx

    def test_handles_empty_state(self):
        state = {
            "case_id": "empty",
            "severity": None,
            "detected_language": "vi",
            "intake_data": None,
            "intake_tracker": None,
            "messages": [],
            "cultural_expressions": [],
            "screening_result": None,
            "differential_diagnoses": [],
            "order_recommendations": [],
            "drug_interactions": [],
            "allergy_alerts": [],
            "critic_validation": None,
            "is_emergency": False,
            "needs_human_review": False,
        }
        ctx = _build_soap_context(state)
        assert "CASE ID: empty" in ctx

    def test_includes_allergy_alerts(self):
        state = _make_state(allergy_alerts=["Penicillin cross-reactivity"])
        ctx = _build_soap_context(state)
        assert "Penicillin cross-reactivity" in ctx

    def test_includes_critic_issues(self):
        state = _make_state(
            critic_validation={
                "status": "needs_modification",
                "overall_safety_score": 70,
                "summary": "Issues found",
                "issues": [
                    {
                        "severity": "warning",
                        "category": "dosage",
                        "description": "Dosage high for elderly",
                    }
                ],
            }
        )
        ctx = _build_soap_context(state)
        assert "warning" in ctx
        assert "Dosage high for elderly" in ctx


# ── _parse_soap_response ──


class TestParseSoapResponse:
    def test_parses_valid_json(self):
        raw = _soap_response()
        parsed = _parse_soap_response(raw)
        assert "subjective" in parsed
        assert "objective" in parsed
        assert "assessment" in parsed
        assert "plan" in parsed

    def test_strips_markdown_fences(self):
        raw = f"```json\n{_soap_response()}\n```"
        parsed = _parse_soap_response(raw)
        assert "subjective" in parsed

    def test_fallback_on_invalid_json(self):
        parsed = _parse_soap_response("This is not JSON at all")
        assert parsed["subjective"]["content"] == "This is not JSON at all"
        assert "parsing failed" in parsed["safety_concerns"][0]

    def test_safety_concerns_preserved(self):
        raw = _soap_response(safety_concerns=["Drug interaction risk"])
        parsed = _parse_soap_response(raw)
        assert "Drug interaction risk" in parsed["safety_concerns"]


# ── generate_soap_note ──


class TestGenerateSoapNote:
    @pytest.mark.asyncio
    async def test_returns_soap_note_response(self, mock_gateway, phi):
        state = _make_state()
        mock_llm_response = LLMResponse(
            content=_soap_response(),
            model="gpt-4",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
            finish_reason="stop",
        )
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_soap_note(state, "session-1", mock_gateway, phi)

        assert result.case_id == "case-1"
        assert result.session_id == "session-1"
        assert result.generated_at

    @pytest.mark.asyncio
    async def test_all_four_sections_populated(self, mock_gateway, phi):
        state = _make_state()
        mock_llm_response = LLMResponse(
            content=_soap_response(),
            model="gpt-4",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
            finish_reason="stop",
        )
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_soap_note(state, "s1", mock_gateway, phi)

        assert "abdominal pain" in result.subjective.content
        assert "telemedicine" in result.objective.content
        assert "appendicitis" in result.assessment.content.lower()
        assert "Acetaminophen" in result.plan.content

    @pytest.mark.asyncio
    async def test_vietnamese_translations(self, mock_gateway, phi):
        state = _make_state()
        mock_llm_response = LLMResponse(
            content=_soap_response(),
            model="gpt-4",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
            finish_reason="stop",
        )
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_soap_note(state, "s1", mock_gateway, phi)

        assert result.subjective.content_vi
        assert result.plan.content_vi

    @pytest.mark.asyncio
    async def test_metadata_populated(self, mock_gateway, phi):
        state = _make_state()
        mock_llm_response = LLMResponse(
            content=_soap_response(),
            model="gpt-4",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
            finish_reason="stop",
        )
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_soap_note(state, "s1", mock_gateway, phi)

        assert result.severity == "urgent"
        assert result.primary_diagnosis == "Acute Appendicitis"
        assert result.confidence_score == 0.65

    @pytest.mark.asyncio
    async def test_critic_safety_score_normalized(self, mock_gateway, phi):
        state = _make_state()
        mock_llm_response = LLMResponse(
            content=_soap_response(),
            model="gpt-4",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
            finish_reason="stop",
        )
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_soap_note(state, "s1", mock_gateway, phi)

        # 92 / 100.0 = 0.92
        assert result.critic_safety_score == 0.92

    @pytest.mark.asyncio
    async def test_includes_safety_concerns(self, mock_gateway, phi):
        state = _make_state()
        mock_llm_response = LLMResponse(
            content=_soap_response(safety_concerns=["Renal function check needed"]),
            model="gpt-4",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
            finish_reason="stop",
        )
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_soap_note(state, "s1", mock_gateway, phi)

        assert "Renal function check needed" in result.safety_concerns

    @pytest.mark.asyncio
    async def test_emergency_case(self, mock_gateway, phi):
        state = _make_state(is_emergency=True, severity="emergency")
        mock_llm_response = LLMResponse(
            content=_soap_response(),
            model="gpt-4",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
            finish_reason="stop",
        )
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_soap_note(state, "s1", mock_gateway, phi)

        assert result.severity == "emergency"

    @pytest.mark.asyncio
    async def test_needs_human_review(self, mock_gateway, phi):
        state = _make_state(
            needs_human_review=True,
            human_review_reason="Critic rejected: critical safety issue",
        )
        mock_llm_response = LLMResponse(
            content=_soap_response(),
            model="gpt-4",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
            finish_reason="stop",
        )
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_soap_note(state, "s1", mock_gateway, phi)

        assert result.needs_human_review is True
        assert "critical safety issue" in result.human_review_reason

    @pytest.mark.asyncio
    async def test_phi_deidentification_called(self, mock_gateway, phi):
        state = _make_state()
        mock_llm_response = LLMResponse(
            content=_soap_response(),
            model="gpt-4",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
            finish_reason="stop",
        )
        with (
            patch.object(phi, "deidentify", wraps=phi.deidentify) as mock_deident,
            patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response),
        ):
            await generate_soap_note(state, "s1", mock_gateway, phi)

        mock_deident.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_called_with_soap_agent_type(self, mock_gateway, phi):
        state = _make_state()
        mock_llm_response = LLMResponse(
            content=_soap_response(),
            model="gpt-4",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
            finish_reason="stop",
        )
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response) as mock_gen:
            await generate_soap_note(state, "s1", mock_gateway, phi)

        call_kwargs = mock_gen.call_args
        assert call_kwargs.kwargs["agent_type"] == "soap"
        assert call_kwargs.kwargs["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_no_differential_diagnoses(self, mock_gateway, phi):
        state = _make_state(differential_diagnoses=[])
        mock_llm_response = LLMResponse(
            content=_soap_response(),
            model="gpt-4",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
            finish_reason="stop",
        )
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_soap_note(state, "s1", mock_gateway, phi)

        assert result.primary_diagnosis == ""
