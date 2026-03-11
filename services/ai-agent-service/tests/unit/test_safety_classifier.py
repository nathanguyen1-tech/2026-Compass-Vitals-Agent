"""Tests for Safety Classifier — LLM-based emergency triage (Layer 1.5)."""

from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet

from app.agents.tools.safety_classifier import (
    SafetyClassification,
    classify_safety,
    should_run_classifier,
)
from app.domain.services.llm_gateway import LLMGateway, LLMResponse
from app.domain.services.phi_deidentifier import PHIDeidentifier


# === Smart Gate Tests ===


class TestShouldRunClassifier:
    """Tests for the smart gating logic."""

    def test_always_runs_on_first_message(self):
        assert should_run_classifier(
            keyword_detected=False, llm_risk_level=None, message_count=1
        ) is True

    def test_runs_on_first_message_even_with_low_risk(self):
        assert should_run_classifier(
            keyword_detected=False, llm_risk_level="low", message_count=1
        ) is True

    def test_skips_when_keyword_detected(self):
        assert should_run_classifier(
            keyword_detected=True, llm_risk_level=None, message_count=3
        ) is False

    def test_skips_when_llm_reports_high(self):
        assert should_run_classifier(
            keyword_detected=False, llm_risk_level="high", message_count=3
        ) is False

    def test_skips_when_llm_reports_moderate(self):
        assert should_run_classifier(
            keyword_detected=False, llm_risk_level="moderate", message_count=3
        ) is False

    def test_skips_when_llm_reports_critical(self):
        assert should_run_classifier(
            keyword_detected=False, llm_risk_level="critical", message_count=3
        ) is False

    def test_runs_when_llm_reports_low(self):
        assert should_run_classifier(
            keyword_detected=False, llm_risk_level="low", message_count=3
        ) is True

    def test_runs_when_llm_risk_missing(self):
        assert should_run_classifier(
            keyword_detected=False, llm_risk_level=None, message_count=3
        ) is True

    def test_skips_when_keyword_detected_and_first_message(self):
        """Keywords take priority even on first message."""
        assert should_run_classifier(
            keyword_detected=True, llm_risk_level=None, message_count=1
        ) is False


# === classify_safety Tests ===


@pytest.fixture
def phi():
    key = Fernet.generate_key().decode()
    return PHIDeidentifier(encryption_key=key)


@pytest.fixture
def mock_gateway(phi):
    return LLMGateway(openai_api_key="test-key", phi_deidentifier=phi)


class TestClassifySafety:
    """Tests for the classify_safety async function."""

    @pytest.mark.asyncio
    async def test_returns_none_without_gateway(self):
        result = await classify_safety("some text", llm_gateway=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_battery_ingestion_detected(self, mock_gateway):
        """'con toi nuot phai pin' should be classified as critical."""
        mock_response = LLMResponse(
            content='{"risk_level":"critical","is_emergency":true,"reasoning":"battery ingestion in child","category":"toxic_ingestion"}',
            model="gpt-4o-mini",
            usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await classify_safety(
            "con toi nuot phai pin",
            llm_gateway=mock_gateway,
            case_id="test",
        )
        assert result is not None
        assert result.is_emergency is True
        assert result.risk_level == "critical"
        assert result.category == "toxic_ingestion"

    @pytest.mark.asyncio
    async def test_bee_sting_face_swollen(self, mock_gateway):
        """'bi ong dot sung ca mat' should be high/critical."""
        mock_response = LLMResponse(
            content='{"risk_level":"high","is_emergency":true,"reasoning":"bee sting with facial swelling suggests anaphylaxis","category":"anaphylaxis"}',
            model="gpt-4o-mini",
            usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await classify_safety(
            "toi bi ong dot sung ca mat",
            llm_gateway=mock_gateway,
            case_id="test",
        )
        assert result is not None
        assert result.is_emergency is True
        assert result.risk_level in ("high", "critical")

    @pytest.mark.asyncio
    async def test_normal_message_low_risk(self, mock_gateway):
        """Normal headache should not trigger."""
        mock_response = LLMResponse(
            content='{"risk_level":"low","is_emergency":false,"reasoning":"routine headache","category":"none"}',
            model="gpt-4o-mini",
            usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await classify_safety(
            "toi bi dau dau 2 ngay",
            llm_gateway=mock_gateway,
            case_id="test",
        )
        assert result is not None
        assert result.is_emergency is False
        assert result.risk_level == "low"

    @pytest.mark.asyncio
    async def test_malformed_json_returns_none(self, mock_gateway):
        """If LLM returns garbage, fail-open (return None)."""
        mock_response = LLMResponse(
            content="This is not valid JSON at all",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await classify_safety(
            "some text",
            llm_gateway=mock_gateway,
            case_id="test",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_handles_markdown_fenced_json(self, mock_gateway):
        """LLM sometimes wraps JSON in markdown code fences."""
        mock_response = LLMResponse(
            content='```json\n{"risk_level":"high","is_emergency":true,"reasoning":"fall from height","category":"trauma"}\n```',
            model="gpt-4o-mini",
            usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await classify_safety(
            "toi roi tu tang 3",
            llm_gateway=mock_gateway,
            case_id="test",
        )
        assert result is not None
        assert result.risk_level == "high"

    @pytest.mark.asyncio
    async def test_with_conversation_summary(self, mock_gateway):
        """Passing conversation summary and complaint should not error."""
        mock_response = LLMResponse(
            content='{"risk_level":"low","is_emergency":false,"reasoning":"context helps","category":"none"}',
            model="gpt-4o-mini",
            usage={"prompt_tokens": 80, "completion_tokens": 30, "total_tokens": 110},
            finish_reason="stop",
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await classify_safety(
            "vang, dung roi",
            conversation_summary="Patient reported mild stomach pain",
            complaint_category="abdominal_gi",
            llm_gateway=mock_gateway,
            case_id="test",
        )
        assert result is not None
        assert result.risk_level == "low"

    @pytest.mark.asyncio
    async def test_llm_exception_returns_none(self, mock_gateway):
        """If LLM call throws exception, fail-open."""
        mock_gateway._call_with_retry = AsyncMock(
            side_effect=Exception("API Error")
        )
        result = await classify_safety(
            "some text",
            llm_gateway=mock_gateway,
            case_id="test",
        )
        assert result is None


# === SafetyClassification Model Tests ===


class TestSafetyClassificationModel:
    def test_valid_classification(self):
        c = SafetyClassification(
            risk_level="high",
            is_emergency=True,
            reasoning="fall from height",
            category="trauma",
        )
        assert c.risk_level == "high"
        assert c.is_emergency is True

    def test_from_dict(self):
        data = {
            "risk_level": "critical",
            "is_emergency": True,
            "reasoning": "battery ingestion",
            "category": "toxic_ingestion",
        }
        c = SafetyClassification(**data)
        assert c.category == "toxic_ingestion"
