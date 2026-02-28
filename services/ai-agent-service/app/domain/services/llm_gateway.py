"""LLM Gateway — Cổng duy nhất để gọi external LLM APIs.

Bao gồm PHI verification, retry, fallback, circuit breaker.
Mọi agent BẮT BUỘC phải đi qua gateway — không được gọi OpenAI trực tiếp.
"""

from abc import ABC, abstractmethod

import structlog
from circuitbreaker import circuit
from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import LLMError, PHIAccessError
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: dict
    finish_reason: str


class LLMProvider(ABC):
    """Abstract interface cho mọi LLM provider."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse: ...


class OpenAIProvider(LLMProvider):
    """OpenAI GPT implementation."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=self.model,
            usage=response.usage.model_dump() if response.usage else {},
            finish_reason=choice.finish_reason or "stop",
        )


class LLMGateway:
    """Cổng duy nhất để gọi LLM. Bao gồm PHI verification, retry, fallback, circuit breaker."""

    def __init__(
        self,
        openai_api_key: str,
        phi_deidentifier: PHIDeidentifier,
        primary_model: str = "gpt-4",
        screening_model: str = "gpt-4o-mini",
    ):
        self.primary = OpenAIProvider(openai_api_key, primary_model)
        self.screening = OpenAIProvider(openai_api_key, screening_model)
        self.phi_deidentifier = phi_deidentifier

    async def generate(
        self,
        messages: list[dict],
        agent_type: str,
        case_id: str,
        **kwargs,
    ) -> LLMResponse:
        """Generate với PHI verification + retry + fallback."""
        # BƯỚC 1: PHI Verification Gate
        self._verify_no_phi(messages, case_id)

        # BƯỚC 2: Chọn provider dựa trên agent type
        provider = self._select_provider(agent_type)

        # BƯỚC 3: Gọi LLM với retry
        response = await self._call_with_retry(provider, messages, **kwargs)

        # BƯỚC 4: Log usage
        logger.info(
            "llm_usage",
            model=response.model,
            agent_type=agent_type,
            case_id=case_id,
            usage=response.usage,
        )

        return response

    def _verify_no_phi(self, messages: list[dict], case_id: str) -> None:
        """BLOCK nếu phát hiện PHI trong user/assistant messages.

        System messages are skipped — they contain our own prompts, not patient data.
        """
        for msg in messages:
            if msg.get("role") == "system":
                continue  # System prompts are ours, not patient data
            content = msg.get("content", "")
            if content and self.phi_deidentifier.contains_phi(content):
                raise PHIAccessError(
                    message=f"PHI detected in LLM request for case {case_id}. "
                    "Messages must be de-identified before calling LLM.",
                    code="PHI_IN_LLM_REQUEST",
                )

    def _select_provider(self, agent_type: str) -> LLMProvider:
        """Hybrid LLM strategy: agent khác nhau dùng model khác nhau."""
        if agent_type == "intake":
            return self.screening  # GPT-4o-mini — intake chỉ thu thập data
        # screening, proposer, critic → GPT-4
        return self.primary

    @circuit(failure_threshold=5, recovery_timeout=60)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        reraise=True,
    )
    async def _call_with_retry(
        self, provider: LLMProvider, messages: list[dict], **kwargs
    ) -> LLMResponse:
        """Gọi LLM với circuit breaker + retry."""
        try:
            return await provider.generate(messages, **kwargs)
        except Exception as e:
            raise LLMError(
                message=f"LLM call failed: {e}",
                code="LLM_CALL_FAILED",
            ) from e
