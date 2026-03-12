"""patient_vital_signs table — vital signs measurements (time series)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, generate_ulid


class PatientVitalSign(Base):
    __tablename__ = "patient_vital_signs"

    vital_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    patient_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # --- Measurements ---
    height_cm: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    bmi: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    bp_systolic: Mapped[int | None] = mapped_column(nullable=True)  # mmHg
    bp_diastolic: Mapped[int | None] = mapped_column(nullable=True)  # mmHg
    heart_rate: Mapped[int | None] = mapped_column(nullable=True)  # bpm
    temperature_c: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    spo2: Mapped[int | None] = mapped_column(nullable=True)  # %

    # --- Context ---
    source: Mapped[str] = mapped_column(
        String(30), server_default="manual"  # manual/wearable/device
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
