"""patient_medications table — current medications (thuốc đang dùng)."""

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class PatientMedication(Base, TimestampMixin):
    __tablename__ = "patient_medications"

    medication_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    patient_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    drug_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "500mg"
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "2 times/day"
    route: Mapped[str | None] = mapped_column(String(50), nullable=True)  # oral/injection/topical
    # prescription, otc, vitamin, herbal, sleep_aid, painkiller
    medication_type: Mapped[str] = mapped_column(String(30), server_default="prescription")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(server_default="true")
    prescribed_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
