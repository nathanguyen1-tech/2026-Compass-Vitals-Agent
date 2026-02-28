"""screening_results table — stores clinical screening outcomes."""

import uuid
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin


class ScreeningResult(Base, TimestampMixin):
    __tablename__ = "screening_results"

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    clinical_assessment: Mapped[str] = mapped_column(Text, nullable=False)
    differential_diagnoses: Mapped[list] = mapped_column(JSON, default=list)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    confidence_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_llm_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
