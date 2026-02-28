"""Custom exception hierarchy cho ai-agent-service."""


class CompassBaseException(Exception):
    """Base exception cho toàn bộ service."""

    def __init__(self, message: str, code: str, details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class ValidationError(CompassBaseException):
    """Input validation failures."""


class AuthorizationError(CompassBaseException):
    """RBAC violations."""


class PHIAccessError(CompassBaseException):
    """PHI access policy violations — BLOCK ngay."""


class ClinicalSafetyError(CompassBaseException):
    """HIGHEST PRIORITY — patient safety risk. Trigger immediate MD notification."""


class LLMError(CompassBaseException):
    """LLM call failures."""


class LLMTimeoutError(LLMError):
    """LLM request timeout."""


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""


class LLMHallucinationError(LLMError):
    """Phát hiện hallucination trong LLM response."""
