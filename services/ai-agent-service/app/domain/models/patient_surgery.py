"""patient_surgeries table — surgical history (tiền sử phẫu thuật)."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class PatientSurgery(Base, TimestampMixin):
    __tablename__ = "patient_surgeries"

    surgery_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    patient_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    procedure_name: Mapped[str] = mapped_column(String(300), nullable=False)
    surgery_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hospital: Mapped[str | None] = mapped_column(String(300), nullable=True)
    complications: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
