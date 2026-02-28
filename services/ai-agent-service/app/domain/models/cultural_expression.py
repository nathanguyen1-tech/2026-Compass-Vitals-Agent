"""cultural_expressions table — Vietnamese cultural health expression mappings."""

import uuid
from decimal import Decimal

from sqlalchemy import ARRAY, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin


class CulturalExpression(Base, TimestampMixin):
    __tablename__ = "cultural_expressions"

    expression_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vietnamese_text: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    variants: Mapped[list] = mapped_column(JSON, default=list)
    medical_meaning: Mapped[str] = mapped_column(Text, nullable=False)
    medical_terms: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    context_clues: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    region: Mapped[str] = mapped_column(String(20), default="all")
