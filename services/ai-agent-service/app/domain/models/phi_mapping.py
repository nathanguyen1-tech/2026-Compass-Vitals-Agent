"""phi_mappings table — encrypted PHI de-identification mappings."""

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base


class PHIMapping(Base):
    __tablename__ = "phi_mappings"

    mapping_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    encrypted_mapping: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    phi_types_found: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
