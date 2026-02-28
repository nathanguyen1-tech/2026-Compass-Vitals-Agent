"""Tests for LLM Gateway — PHI gate, provider selection, retry."""

from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet

from app.core.exceptions import PHIAccessError
from app.domain.services.llm_gateway import LLMGateway, LLMResponse, OpenAIProvider
from app.domain.services.phi_deidentifier import PHIDeidentifier


@pytest.fixture
def phi():
    key = Fernet.generate_key().decode()
    return PHIDeidentifier(encryption_key=key)


@pytest.fixture
def gateway(phi):
    return LLMGateway(
        openai_api_key="test-key",
        phi_deidentifier=phi,
        primary_model="gpt-4",
        screening_model="gpt-4o-mini",
    )


@pytest.fixture
def mock_response():
    return LLMResponse(
        content="Xin chào! Bạn có thể mô tả triệu chứng?",
        model="gpt-4o-mini",
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        finish_reason="stop",
    )


class TestPHIVerificationGate:
    def test_blocks_phi_in_messages(self, gateway):
        messages = [{"role": "user", "content": "Bệnh nhân Nguyễn Văn An bị sốt"}]
        with pytest.raises(PHIAccessError):
            gateway._verify_no_phi(messages, "case-123")

    def test_allows_clean_messages(self, gateway):
        messages = [{"role": "user", "content": "Tôi bị đau bụng 2 ngày"}]
        gateway._verify_no_phi(messages, "case-123")  # Should not raise

    def test_blocks_ssn(self, gateway):
        messages = [{"role": "user", "content": "SSN: 123-45-6789"}]
        with pytest.raises(PHIAccessError):
            gateway._verify_no_phi(messages, "case-123")

    def test_blocks_email(self, gateway):
        messages = [{"role": "user", "content": "Email patient@test.com"}]
        with pytest.raises(PHIAccessError):
            gateway._verify_no_phi(messages, "case-123")


class TestProviderSelection:
    def test_intake_uses_screening_model(self, gateway):
        provider = gateway._select_provider("intake")
        assert provider is gateway.screening

    def test_screening_uses_primary_model(self, gateway):
        provider = gateway._select_provider("screening")
        assert provider is gateway.primary

    def test_proposer_uses_primary_model(self, gateway):
        provider = gateway._select_provider("proposer")
        assert provider is gateway.primary

    def test_critic_uses_primary_model(self, gateway):
        provider = gateway._select_provider("critic")
        assert provider is gateway.primary


class TestGenerate:
    @pytest.mark.asyncio
    async def test_blocks_phi_before_llm_call(self, gateway):
        messages = [{"role": "user", "content": "Bệnh nhân Nguyễn Văn An"}]
        with pytest.raises(PHIAccessError):
            await gateway.generate(messages, agent_type="intake", case_id="case-1")

    @pytest.mark.asyncio
    async def test_calls_llm_with_clean_messages(self, gateway, mock_response):
        messages = [{"role": "user", "content": "Tôi bị đau bụng"}]
        with patch.object(
            gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await gateway.generate(messages, agent_type="intake", case_id="case-1")
            assert result.content == "Xin chào! Bạn có thể mô tả triệu chứng?"
            assert result.model == "gpt-4o-mini"
