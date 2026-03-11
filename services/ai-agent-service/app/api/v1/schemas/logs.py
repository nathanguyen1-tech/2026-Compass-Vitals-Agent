"""LLM Logs API schemas — request/response models for observability dashboard."""

from pydantic import BaseModel


class LogEntryBrief(BaseModel):
    """Abbreviated log entry for list view (excludes full request/response)."""

    id: str
    timestamp: str
    model: str
    agent_type: str
    case_id: str
    session_id: str
    total_tokens: int
    latency_ms: float
    status: str
    finish_reason: str


class LogEntryDetail(BaseModel):
    """Full log entry including request messages and response content."""

    id: str
    timestamp: str
    model: str
    agent_type: str
    case_id: str
    session_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    status: str
    error_message: str
    request_messages: list[dict]
    response_content: str
    finish_reason: str
    temperature: float
    max_tokens: int


class LogListResponse(BaseModel):
    """Paginated list of log entries."""

    entries: list[LogEntryBrief]
    total: int
    limit: int
    offset: int


class LogStatsResponse(BaseModel):
    """Summary statistics for the logs dashboard."""

    total_requests: int
    total_tokens: int
    avg_latency_ms: float
    error_count: int
    error_rate: float
    by_model: dict
    by_agent_type: dict


class LogFiltersResponse(BaseModel):
    """Available filter values for the UI dropdowns."""

    models: list[str]
    agent_types: list[str]
