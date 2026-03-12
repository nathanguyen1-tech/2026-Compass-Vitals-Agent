"""patient_vaccinations table — vaccination records (tiêm chủng)."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class PatientVaccination(Base, TimestampMixin):
    __tablename__ = "patient_vaccinations"

    vaccination_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    patient_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    vaccine_name: Mapped[str] = mapped_column(String(200), nullable=False)  # COVID-19, Flu, etc.
    date_administered: Mapped[date | None] = mapped_column(Date, nullable=True)
    dose_number: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1, 2, 3 (booster)
    provider: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lot_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
