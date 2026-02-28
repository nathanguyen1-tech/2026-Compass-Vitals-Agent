"""Chat API request/response schemas."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    language: str = "auto"  # "vi", "en", "auto"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent_state: str
    is_complete: bool
    detected_language: str
    is_emergency: bool = False
    cultural_expressions: list[dict] = []
