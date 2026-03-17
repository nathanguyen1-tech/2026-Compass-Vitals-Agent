"""Repository cho AgentSession — CRUD operations với PostgreSQL."""

import json
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.agent_session import AgentSession

logger = structlog.get_logger()


class AgentSessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ─── Serialization helpers ────────────────────────────────────────────────

    @staticmethod
    def _serialize_messages(messages: list) -> list[dict]:
        """LangChain HumanMessage/AIMessage → [{"type": "human"|"ai", "content": "..."}]"""
        result = []
        for m in messages:
            if hasattr(m, "type") and hasattr(m, "content"):
                result.append({"type": m.type, "content": str(m.content)})
            elif isinstance(m, dict) and "type" in m:
                result.append(m)
        return result

    @staticmethod
    def _build_state_snapshot(session_dict: dict) -> dict:
        """Serialize everything except 'messages' (stored in its own column).
        Uses default=str to safely handle any non-serializable objects."""
        raw = {k: v for k, v in session_dict.items() if k != "messages"}
        # Round-trip through JSON to ensure full serializability
        try:
            return json.loads(json.dumps(raw, default=str))
        except Exception:
            return {}

    @staticmethod
    def deserialize_messages(raw: list[dict]) -> list:
        """[{"type": "human"|"ai", "content": "..."}] → LangChain objects."""
        from langchain_core.messages import AIMessage, HumanMessage

        result = []
        for m in raw or []:
            t = m.get("type", "")
            content = m.get("content", "")
            if t == "human":
                result.append(HumanMessage(content=content))
            elif t in ("ai", "AIMessage"):
                result.append(AIMessage(content=content))
        return result

    # ─── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, session_id: str, session_dict: dict) -> AgentSession:
        """Insert a new AgentSession row."""
        messages = self._serialize_messages(session_dict.get("messages", []))
        snapshot = self._build_state_snapshot(session_dict)

        row = AgentSession(
            session_id=uuid.UUID(session_id),
            patient_id=uuid.UUID(session_dict.get("patient_id") or str(uuid.uuid4())),
            case_id=uuid.UUID(session_dict.get("case_id") or str(uuid.uuid4())),
            organization_id=uuid.UUID(session_dict.get("organization_id") or str(uuid.uuid4())),
            agent_type="intake_v2",
            state_snapshot=snapshot,
            messages=messages,
            status="active",
        )
        self._db.add(row)
        await self._db.commit()
        await self._db.refresh(row)
        return row

    async def update(self, session_id: str, session_dict: dict) -> None:
        """Update state_snapshot and messages for an existing session."""
        result = await self._db.execute(
            select(AgentSession).where(AgentSession.session_id == uuid.UUID(session_id))
        )
        row = result.scalar_one_or_none()
        if row is None:
            # Race condition — just create it
            await self.create(session_id, session_dict)
            return

        row.messages = self._serialize_messages(session_dict.get("messages", []))
        row.state_snapshot = self._build_state_snapshot(session_dict)
        # Mark complete if intake is done and care plan exists
        if session_dict.get("_care_plan") or session_dict.get("_soap_note"):
            row.status = "complete"
        await self._db.commit()

    async def get(self, session_id: str) -> AgentSession | None:
        """Lookup by primary key. Returns None if not found."""
        try:
            result = await self._db.execute(
                select(AgentSession).where(AgentSession.session_id == uuid.UUID(session_id))
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.warning("repo.get_failed", session_id=session_id, error=str(e))
            return None

    async def list_recent(self, limit: int = 50, offset: int = 0) -> list[AgentSession]:
        """Return sessions ordered by created_at DESC."""
        from sqlalchemy import desc

        result = await self._db.execute(
            select(AgentSession)
            .order_by(desc(AgentSession.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
