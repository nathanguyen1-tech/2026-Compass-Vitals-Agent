"""patients table — core patient profile from onboarding."""

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    patient_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    organization_id: Mapped[str] = mapped_column(
        String(26), nullable=False, index=True
    )

    # --- Thông tin cá nhân ---
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)  # male/female/other
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(10), server_default="vi")  # vi/en

    # --- Onboarding status ---
    onboarding_phase: Mapped[int] = mapped_column(server_default="0")  # 0-4
    onboarding_status: Mapped[str] = mapped_column(
        String(20), server_default="pending"  # pending/in_progress/completed
    )
