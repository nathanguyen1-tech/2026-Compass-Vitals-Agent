"""agent_sessions table — tracks AI agent conversation sessions."""

import uuid

from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin


class AgentSession(Base, TimestampMixin):
    __tablename__ = "agent_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    state_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    messages: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
