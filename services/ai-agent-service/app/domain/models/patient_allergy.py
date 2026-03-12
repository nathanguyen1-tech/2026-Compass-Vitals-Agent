"""patient_allergies table — allergies (dị ứng)."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class PatientAllergy(Base, TimestampMixin):
    __tablename__ = "patient_allergies"

    allergy_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    patient_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    allergen: Mapped[str] = mapped_column(String(200), nullable=False)
    # drug, food, latex, pollen, dust, environmental, other
    allergy_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reaction: Mapped[str | None] = mapped_column(String(200), nullable=True)  # rash, anaphylaxis, etc.
    severity: Mapped[str] = mapped_column(String(20), server_default="mild")  # mild/moderate/severe
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
