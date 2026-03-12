"""patient_screenings table — preventive care & cognitive assessments."""

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class PatientScreening(Base, TimestampMixin):
    __tablename__ = "patient_screenings"

    screening_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    patient_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # mammogram, colonoscopy, pap_smear, psa, bone_density,
    # eye_exam, dental_exam, cognitive_assessment, other
    screening_type: Mapped[str] = mapped_column(String(50), nullable=False)
    screening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    result: Mapped[str | None] = mapped_column(String(100), nullable=True)  # normal/abnormal/pending
    provider: Mapped[str | None] = mapped_column(String(200), nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
