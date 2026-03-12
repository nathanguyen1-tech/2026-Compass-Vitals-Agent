"""In-memory LLM log store — captures every LLM Gateway call for observability."""

import threading
from collections import deque

from pydantic import BaseModel


class LLMLogEntry(BaseModel):
    """Single LLM API call log entry."""

    id: str
    timestamp: str  # ISO 8601 UTC
    model: str
    agent_type: str
    case_id: str
    session_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    status: str  # "success" or "error"
    error_message: str
    request_messages: list[dict]
    response_content: str
    finish_reason: str
    temperature: float
    max_tokens: int


class LLMLogStore:
    """Thread-safe in-memory ring buffer for LLM call logs.

    Uses collections.deque(maxlen=N) so oldest entries are auto-evicted
    when capacity is reached. No risk of unbounded memory growth.
    """

    def __init__(self, max_entries: int = 10_000):
        self._entries: deque[LLMLogEntry] = deque(maxlen=max_entries)
        self._index: dict[str, LLMLogEntry] = {}
        self._lock = threading.Lock()

    def add(self, entry: LLMLogEntry) -> None:
        with self._lock:
            if len(self._entries) == self._entries.maxlen:
                evicted = self._entries[0]
                self._index.pop(evicted.id, None)
            self._entries.append(entry)
            self._index[entry.id] = entry

    def get_by_id(self, log_id: str) -> LLMLogEntry | None:
        return self._index.get(log_id)

    def query(
        self,
        model: str | None = None,
        agent_type: str | None = None,
        status: str | None = None,
        case_id: str | None = None,
        session_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LLMLogEntry], int]:
        """Query entries with optional filters. Returns (entries, total_matching)."""
        with self._lock:
            filtered = []
            for entry in reversed(self._entries):
                if model and entry.model != model:
                    continue
                if agent_type and entry.agent_type != agent_type:
                    continue
                if status and entry.status != status:
                    continue
                if case_id and entry.case_id != case_id:
                    continue
                if session_id and entry.session_id != session_id:
                    continue
                filtered.append(entry)

            total = len(filtered)
            page = filtered[offset : offset + limit]
            return page, total

    def get_stats(self) -> dict:
        with self._lock:
            entries = list(self._entries)

        if not entries:
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "avg_latency_ms": 0.0,
                "error_count": 0,
                "error_rate": 0.0,
                "by_model": {},
                "by_agent_type": {},
            }

        total = len(entries)
        total_tokens = sum(e.total_tokens for e in entries)
        avg_latency = sum(e.latency_ms for e in entries) / total
        error_count = sum(1 for e in entries if e.status == "error")

        by_model: dict[str, dict] = {}
        by_agent_type: dict[str, dict] = {}

        for e in entries:
            if e.model not in by_model:
                by_model[e.model] = {"count": 0, "tokens": 0, "errors": 0}
            by_model[e.model]["count"] += 1
            by_model[e.model]["tokens"] += e.total_tokens
            if e.status == "error":
                by_model[e.model]["errors"] += 1

            if e.agent_type not in by_agent_type:
                by_agent_type[e.agent_type] = {"count": 0, "tokens": 0, "avg_latency_ms": 0.0}
            by_agent_type[e.agent_type]["count"] += 1
            by_agent_type[e.agent_type]["tokens"] += e.total_tokens

        for at in by_agent_type:
            at_entries = [e for e in entries if e.agent_type == at]
            by_agent_type[at]["avg_latency_ms"] = round(
                sum(e.latency_ms for e in at_entries) / len(at_entries), 1
            )

        return {
            "total_requests": total,
            "total_tokens": total_tokens,
            "avg_latency_ms": round(avg_latency, 1),
            "error_count": error_count,
            "error_rate": round(error_count / total * 100, 1) if total > 0 else 0.0,
            "by_model": by_model,
            "by_agent_type": by_agent_type,
        }

    def get_distinct_models(self) -> list[str]:
        with self._lock:
            return list({e.model for e in self._entries})

    def get_distinct_agent_types(self) -> list[str]:
        with self._lock:
            return list({e.agent_type for e in self._entries})


# Module-level singleton
log_store = LLMLogStore()
