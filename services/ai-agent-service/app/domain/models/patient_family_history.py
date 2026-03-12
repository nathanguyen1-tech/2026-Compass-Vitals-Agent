"""patient_family_histories table — family medical history (tiền sử gia đình)."""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class PatientFamilyHistory(Base, TimestampMixin):
    __tablename__ = "patient_family_histories"

    family_history_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    patient_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # heart_disease, diabetes, hypertension, stroke, cancer,
    # alzheimer, osteoporosis, autoimmune, mental_disorder, other
    condition: Mapped[str] = mapped_column(String(200), nullable=False)
    # father, mother, sibling, paternal_grandparent, maternal_grandparent, other
    relation: Mapped[str] = mapped_column(String(50), nullable=False)
    age_of_onset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_deceased: Mapped[bool] = mapped_column(Boolean, server_default="false")
    cause_of_death: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
