"""patient_medical_conditions table — chronic/past medical conditions (bệnh sử cá nhân)."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class PatientMedicalCondition(Base, TimestampMixin):
    __tablename__ = "patient_medical_conditions"

    condition_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    patient_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    condition_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # hypertension, diabetes, cardiovascular, cholesterol, asthma,
    # liver_disease, kidney_disease, cancer, autoimmune, mental_disorder, other
    condition_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)  # mild/moderate/severe
    diagnosed_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), server_default="active")  # active/resolved/managed
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
