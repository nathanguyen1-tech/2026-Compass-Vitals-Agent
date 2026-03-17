"""Sessions API — GET /api/v1/sessions (lịch sử các phiên chat)."""

import structlog
from fastapi import APIRouter, HTTPException

from app.api.v1.schemas.sessions import SessionSummary
from app.db.engine import AsyncSessionLocal
from app.domain.models.agent_session import AgentSession
from app.domain.repositories.agent_session_repository import AgentSessionRepository

logger = structlog.get_logger()
router = APIRouter()


def _to_summary(row: AgentSession) -> SessionSummary:
    """Convert AgentSession ORM row → SessionSummary Pydantic model."""
    snapshot = row.state_snapshot or {}
    messages = row.messages or []

    soap_note_ready = "_soap_note" in snapshot
    care_plan_ready = "_care_plan" in snapshot

    primary_diagnosis: str | None = None
    if soap_note_ready:
        soap = snapshot.get("_soap_note", {})
        primary_diagnosis = soap.get("primary_diagnosis")

    severity: str | None = snapshot.get("severity")

    return SessionSummary(
        session_id=str(row.session_id),
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
        status=row.status or "active",
        soap_note_ready=soap_note_ready,
        care_plan_ready=care_plan_ready,
        primary_diagnosis=primary_diagnosis,
        severity=severity,
        message_count=len(messages),
    )


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Trả về danh sách messages của một session để hiển thị lại lịch sử chat."""
    try:
        async with AsyncSessionLocal() as db:
            repo = AgentSessionRepository(db)
            row = await repo.get(session_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"session_id": session_id, "messages": row.messages or []}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("sessions.get_messages_failed", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(limit: int = 50, offset: int = 0):
    """Trả về danh sách sessions mới nhất, dùng cho trang /history."""
    try:
        async with AsyncSessionLocal() as db:
            repo = AgentSessionRepository(db)
            rows = await repo.list_recent(limit=limit, offset=offset)
        return [_to_summary(row) for row in rows]
    except Exception as e:
        logger.warning("sessions.list_failed", error=str(e))
        return []
