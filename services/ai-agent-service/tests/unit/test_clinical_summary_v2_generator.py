"""Tests for Clinical Summary v2 Generator — GPT-4 clinical narrative."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.clinical_summary_v2_generator import (
    _build_clinical_summary_context,
    _parse_clinical_summary_response,
    generate_clinical_summary_v2,
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


def _v2_response(data_quality_notes=None):
    """Create a mock Clinical Summary v2 LLM JSON response."""
    data = {
        "hpi": {
            "content": "Patient is a middle-aged individual with a PMH of DM2 on metformin. "
            "No known drug allergies (NKDA). Social history: Non-smoker. "
            "Family history: Not reported.",
            "content_vi": "Benh nhan trung nien co tien su DM2 dang uong metformin. "
            "Khong di ung thuoc (NKDA). Tien su xa hoi: Khong hut thuoc.",
        },
        "chief_complaint": {
            "content": "Patient presents with epigastric abdominal pain of 3 days duration. "
            "The pain is described as a dull, pressing sensation in the epigastric region. "
            "Aggravated by eating. Associated with nausea. No fever reported. "
            "Severity rated 6/10.",
            "content_vi": "Benh nhan den voi dau bung vung thuong vi 3 ngay. "
            "Dau am i, cam giac de ep o vung thuong vi. Tang khi an. "
            "Kem buon non. Khong sot. Muc do 6/10.",
        },
        "ros": {
            "content": "Constitutional: Denies fever, chills, weight loss. "
            "Gastrointestinal: Positive for epigastric pain and nausea. "
            "Denies vomiting, diarrhea, constipation, melena, hematochezia. "
            "Cardiovascular: Not assessed. "
            "Respiratory: Not assessed.",
            "content_vi": "Toan than: Khong sot, khong lanh run, khong sut can. "
            "Tieu hoa: Co dau thuong vi va buon non. "
            "Khong non, khong tieu chay, khong tao bon. "
            "Tim mach: Chua danh gia. Ho hap: Chua danh gia.",
        },
        "data_quality_notes": data_quality_notes or [],
    }
    return json.dumps(data, ensure_ascii=False)


def _make_state(**overrides):
    """Create a complete post-screening CareFlowState."""
    state = {
        "patient_id": "patient-1",
        "case_id": "case-1",
        "organization_id": "org-1",
        "messages": [
            HumanMessage(content="Toi bi dau bung vung thuong vi 3 ngay"),
            AIMessage(content="Ban co buon non khong?"),
            HumanMessage(content="Co buon non, khong sot"),
        ],
        "intake_data": {
            "chief_complaint": "epigastric abdominal pain",
            "onset": "3 days ago",
            "severity": "6/10",
            "character": "dull pressing",
            "aggravating": "eating",
            "pmh": "DM2",
            "medications": "metformin",
            "allergies": "NKDA",
        },
        "intake_complete": True,
        "intake_tracker": {
            "phase": "complete",
            "complaint_category": "abdominal_gi",
            "message_count": 6,
            "cc": "dau bung vung thuong vi",
            "hpi": {
                "onset": "3 days ago",
                "location": "epigastric",
                "duration": "3 days",
                "character": "dull pressing",
                "aggravating": "eating",
                "alleviating": None,
                "timing": None,
                "severity": "6/10",
            },
            "hpi_additional": {},
            "relevant_oldcarts": [
                "onset", "location", "duration", "character",
                "aggravating", "alleviating", "timing", "severity",
            ],
            "red_flags_checked": ["sudden_severe_pain"],
            "red_flags_found": [],
            "red_flag_screening_done": True,
            "ros_systems": {
                "gastrointestinal": "positive: nausea, epigastric pain; negative: vomiting, diarrhea",
                "constitutional": "negative: fever, weight loss",
            },
            "pmh": "DM2",
            "pmh_complete": True,
            "medications": "metformin",
            "medications_complete": True,
            "allergies": "NKDA",
            "allergies_complete": True,
            "social_family": "Non-smoker",
            "social_family_complete": True,
            "pmh_prefilled": False,
            "medications_prefilled": False,
            "allergies_prefilled": False,
            "social_family_prefilled": False,
            "summary_confirmed": True,
            "emergency_detected_reason": None,
        },
        "is_emergency": False,
        "detected_language": "vi",
        "cultural_expressions": [
            {"original": "nong trong", "medical_meaning": "internal heat sensation"}
        ],
        "screening_result": {
            "severity": "urgent",
            "clinical_impression": "Epigastric pain with nausea, possible gastritis or PUD",
            "key_findings": ["epigastric pain", "nausea", "DM2 on metformin"],
            "red_flags": [],
        },
        "severity": "urgent",
        "differential_diagnoses": [
            {
                "name": "Gastritis",
                "name_vi": "Viem da day",
                "confidence": 45,
                "reasoning": "Epigastric pain aggravated by eating",
            },
            {
                "name": "Peptic Ulcer Disease",
                "name_vi": "Loet da day",
                "confidence": 35,
                "reasoning": "Chronic epigastric pain with nausea",
            },
        ],
        "confidence_score": 0.45,
        "needs_human_review": False,
        "human_review_reason": None,
    }
    state.update(overrides)
    return state


# ── Context Builder Tests ──


class TestBuildClinicalSummaryContext:
    def test_includes_chief_complaint_from_tracker(self):
        ctx = _build_clinical_summary_context(_make_state())
        assert "dau bung vung thuong vi" in ctx

    def test_includes_chief_complaint_from_intake_data(self):
        ctx = _build_clinical_summary_context(
            _make_state(intake_tracker=None)
        )
        assert "epigastric abdominal pain" in ctx

    def test_includes_complaint_category(self):
        ctx = _build_clinical_summary_context(_make_state())
        assert "abdominal_gi" in ctx

    def test_includes_oldcarts_from_tracker(self):
        ctx = _build_clinical_summary_context(_make_state())
        assert "3 days ago" in ctx
        assert "epigastric" in ctx
        assert "dull pressing" in ctx
        assert "6/10" in ctx

    def test_includes_oldcarts_from_intake_data(self):
        ctx = _build_clinical_summary_context(
            _make_state(intake_tracker=None)
        )
        assert "3 days ago" in ctx
        assert "eating" in ctx

    def test_includes_pmh(self):
        ctx = _build_clinical_summary_context(_make_state())
        assert "DM2" in ctx

    def test_includes_medications(self):
        ctx = _build_clinical_summary_context(_make_state())
        assert "metformin" in ctx

    def test_includes_allergies(self):
        ctx = _build_clinical_summary_context(_make_state())
        assert "NKDA" in ctx

    def test_includes_social_family(self):
        ctx = _build_clinical_summary_context(_make_state())
        assert "Non-smoker" in ctx

    def test_includes_ros_systems(self):
        ctx = _build_clinical_summary_context(_make_state())
        assert "gastrointestinal" in ctx
        assert "constitutional" in ctx

    def test_includes_red_flags(self):
        state = _make_state()
        state["intake_tracker"]["red_flags_found"] = ["hematemesis"]
        ctx = _build_clinical_summary_context(state)
        assert "hematemesis" in ctx

    def test_includes_cultural_expressions(self):
        ctx = _build_clinical_summary_context(_make_state())
        assert "nong trong" in ctx
        assert "internal heat" in ctx

    def test_includes_screening_result(self):
        ctx = _build_clinical_summary_context(_make_state())
        assert "possible gastritis" in ctx
        assert "epigastric pain" in ctx

    def test_includes_differential_diagnoses(self):
        ctx = _build_clinical_summary_context(_make_state())
        assert "Gastritis" in ctx
        assert "45%" in ctx

    def test_excludes_raw_conversation_excerpts(self):
        """Conversation excerpts excluded to prevent PHI leakage."""
        ctx = _build_clinical_summary_context(_make_state())
        assert "[Patient]" not in ctx
        assert "CONVERSATION EXCERPTS" not in ctx

    def test_includes_emergency_flag(self):
        ctx = _build_clinical_summary_context(_make_state(is_emergency=True))
        assert "EMERGENCY CASE" in ctx

    def test_handles_empty_state(self):
        ctx = _build_clinical_summary_context({
            "case_id": "x",
            "messages": [],
            "intake_data": None,
            "intake_tracker": None,
            "cultural_expressions": [],
        })
        assert "CASE ID: x" in ctx
        assert "Not assessed" in ctx or "Not reported" in ctx

    def test_does_not_include_order_recommendations(self):
        state = _make_state()
        state["order_recommendations"] = [{"type": "medication", "drug": "Omeprazole"}]
        ctx = _build_clinical_summary_context(state)
        assert "ORDER RECOMMENDATIONS" not in ctx

    def test_does_not_include_critic_validation(self):
        state = _make_state()
        state["critic_validation"] = {"status": "approved"}
        ctx = _build_clinical_summary_context(state)
        assert "CRITIC VALIDATION" not in ctx


# ── JSON Parser Tests ──


class TestParseClinicalSummaryResponse:
    def test_parses_valid_json(self):
        parsed = _parse_clinical_summary_response(_v2_response())
        assert "hpi" in parsed
        assert "chief_complaint" in parsed
        assert "ros" in parsed
        assert parsed["hpi"]["content"]
        assert parsed["chief_complaint"]["content"]

    def test_strips_markdown_fences(self):
        wrapped = f"```json\n{_v2_response()}\n```"
        parsed = _parse_clinical_summary_response(wrapped)
        assert "hpi" in parsed
        assert parsed["hpi"]["content"]

    def test_fallback_on_invalid_json(self):
        parsed = _parse_clinical_summary_response("This is not JSON at all")
        assert "hpi" in parsed
        assert "chief_complaint" in parsed
        assert "ros" in parsed
        assert "parsing failed" in parsed["data_quality_notes"][0].lower()

    def test_data_quality_notes_preserved(self):
        resp = _v2_response(data_quality_notes=["No family history collected"])
        parsed = _parse_clinical_summary_response(resp)
        assert "No family history collected" in parsed["data_quality_notes"]


# ── Generator Tests ──


class TestGenerateClinicalSummaryV2:
    @pytest.fixture
    def mock_llm_response(self):
        return LLMResponse(
            content=_v2_response(),
            model="gpt-4",
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
            finish_reason="stop",
        )

    @pytest.mark.asyncio
    async def test_returns_clinical_summary_v2_response(self, phi, mock_gateway, mock_llm_response):
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_clinical_summary_v2(
                _make_state(), "session-1", mock_gateway, phi
            )
        from app.api.v1.schemas.clinical_summary_v2 import ClinicalSummaryV2Response
        assert isinstance(result, ClinicalSummaryV2Response)

    @pytest.mark.asyncio
    async def test_all_three_sections_populated(self, phi, mock_gateway, mock_llm_response):
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_clinical_summary_v2(
                _make_state(), "session-1", mock_gateway, phi
            )
        assert result.hpi.content
        assert result.chief_complaint.content
        assert result.ros.content

    @pytest.mark.asyncio
    async def test_vietnamese_translations(self, phi, mock_gateway, mock_llm_response):
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_clinical_summary_v2(
                _make_state(), "session-1", mock_gateway, phi
            )
        assert result.hpi.content_vi
        assert result.chief_complaint.content_vi
        assert result.ros.content_vi

    @pytest.mark.asyncio
    async def test_metadata_populated(self, phi, mock_gateway, mock_llm_response):
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_clinical_summary_v2(
                _make_state(), "session-1", mock_gateway, phi
            )
        assert result.case_id == "case-1"
        assert result.session_id == "session-1"
        assert result.severity == "urgent"
        assert result.primary_diagnosis == "Gastritis"
        assert result.detected_language == "vi"
        assert result.generated_at

    @pytest.mark.asyncio
    async def test_red_flags_from_tracker(self, phi, mock_gateway, mock_llm_response):
        state = _make_state()
        state["intake_tracker"]["red_flags_found"] = ["hematemesis"]
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_clinical_summary_v2(state, "s1", mock_gateway, phi)
        assert "hematemesis" in result.red_flags

    @pytest.mark.asyncio
    async def test_red_flags_from_screening(self, phi, mock_gateway, mock_llm_response):
        state = _make_state(intake_tracker=None)
        state["intake_data"]["red_flags_found"] = None
        state["screening_result"]["red_flags"] = ["peritoneal_signs"]
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_clinical_summary_v2(state, "s1", mock_gateway, phi)
        assert "peritoneal_signs" in result.red_flags

    @pytest.mark.asyncio
    async def test_emergency_case(self, phi, mock_gateway, mock_llm_response):
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_clinical_summary_v2(
                _make_state(is_emergency=True), "s1", mock_gateway, phi
            )
        assert result.is_emergency is True

    @pytest.mark.asyncio
    async def test_needs_human_review(self, phi, mock_gateway, mock_llm_response):
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_clinical_summary_v2(
                _make_state(needs_human_review=True, human_review_reason="Low confidence"),
                "s1", mock_gateway, phi,
            )
        assert result.needs_human_review is True
        assert result.human_review_reason == "Low confidence"

    @pytest.mark.asyncio
    async def test_phi_deidentification_called(self, phi, mock_gateway, mock_llm_response):
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response), \
             patch.object(phi, "deidentify", wraps=phi.deidentify) as mock_deid:
            await generate_clinical_summary_v2(
                _make_state(), "s1", mock_gateway, phi
            )
        mock_deid.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_called_with_clinical_summary_agent_type(self, phi, mock_gateway, mock_llm_response):
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response) as mock_gen:
            await generate_clinical_summary_v2(
                _make_state(), "s1", mock_gateway, phi
            )
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["agent_type"] == "clinical_summary"
        assert call_kwargs["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_no_differential_diagnoses(self, phi, mock_gateway, mock_llm_response):
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await generate_clinical_summary_v2(
                _make_state(differential_diagnoses=[]), "s1", mock_gateway, phi
            )
        assert result.primary_diagnosis == ""

    @pytest.mark.asyncio
    async def test_data_quality_notes_populated(self, phi, mock_gateway):
        resp_with_notes = LLMResponse(
            content=_v2_response(data_quality_notes=["Missing social history"]),
            model="gpt-4",
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
            finish_reason="stop",
        )
        with patch.object(mock_gateway, "generate", new_callable=AsyncMock, return_value=resp_with_notes):
            result = await generate_clinical_summary_v2(
                _make_state(), "s1", mock_gateway, phi
            )
        assert "Missing social history" in result.data_quality_notes
