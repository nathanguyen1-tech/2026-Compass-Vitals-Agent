"""LLM Logs API endpoints — observability dashboard backend.

GET /logs          — paginated list with filters
GET /logs/stats    — summary statistics
GET /logs/filters  — available filter values for UI dropdowns
GET /logs/{log_id} — detailed view of a single log entry
"""

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.api.v1.schemas.logs import (
    LogEntryDetail,
    LogFiltersResponse,
    LogListResponse,
    LogStatsResponse,
)
from app.domain.services.llm_log_store import log_store

logger = structlog.get_logger()
router = APIRouter()


@router.get("/logs", response_model=LogListResponse)
async def list_logs(
    model: str | None = Query(None, description="Filter by model name"),
    agent_type: str | None = Query(None, description="Filter by agent type"),
    status: str | None = Query(None, description="Filter by status (success/error)"),
    case_id: str | None = Query(None, description="Filter by case ID"),
    session_id: str | None = Query(None, description="Filter by session ID"),
    limit: int = Query(50, ge=1, le=500, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List LLM call logs with optional filters, newest first."""
    entries, total = log_store.query(
        model=model,
        agent_type=agent_type,
        status=status,
        case_id=case_id,
        session_id=session_id,
        limit=limit,
        offset=offset,
    )
    return LogListResponse(
        entries=[
            {
                "id": e.id,
                "timestamp": e.timestamp,
                "model": e.model,
                "agent_type": e.agent_type,
                "case_id": e.case_id,
                "session_id": e.session_id,
                "total_tokens": e.total_tokens,
                "latency_ms": e.latency_ms,
                "status": e.status,
                "finish_reason": e.finish_reason,
            }
            for e in entries
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


# IMPORTANT: /logs/stats and /logs/filters BEFORE /logs/{log_id}
@router.get("/logs/stats", response_model=LogStatsResponse)
async def get_log_stats():
    """Summary statistics for the dashboard header cards."""
    return LogStatsResponse(**log_store.get_stats())


@router.get("/logs/filters", response_model=LogFiltersResponse)
async def get_log_filters():
    """Available filter values for the UI dropdowns."""
    return LogFiltersResponse(
        models=log_store.get_distinct_models(),
        agent_types=log_store.get_distinct_agent_types(),
    )


@router.get("/logs/{log_id}", response_model=LogEntryDetail)
async def get_log_detail(log_id: str):
    """Full details of a single log entry (including request/response)."""
    entry = log_store.get_by_id(log_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return LogEntryDetail(**entry.model_dump())
