"""patient_social_history table — occupation, smoking, alcohol, substances (1:1 with patient)."""

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class PatientSocialHistory(Base, TimestampMixin):
    __tablename__ = "patient_social_history"

    social_history_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    patient_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )

    # --- Nghề nghiệp ---
    occupation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    work_environment: Mapped[str | None] = mapped_column(String(200), nullable=True)
    chemical_exposure: Mapped[bool] = mapped_column(Boolean, server_default="false")
    chemical_exposure_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Hút thuốc ---
    smoking_status: Mapped[str] = mapped_column(
        String(20), server_default="never"  # never/current/former
    )
    cigarettes_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smoking_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wants_to_quit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # --- Rượu bia ---
    alcohol_status: Mapped[str] = mapped_column(
        String(20), server_default="never"  # never/occasional/regular/heavy
    )
    alcohol_frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    alcohol_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    alcohol_amount: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # --- Chất kích thích ---
    substance_use: Mapped[bool] = mapped_column(Boolean, server_default="false")
    substance_details: Mapped[str | None] = mapped_column(Text, nullable=True)  # encrypted/sensitive

    # --- Tiền sử nhập viện (JSON array) ---
    # [{"year": 2023, "reason": "...", "hospital": "...", "duration_days": 5}]
    hospitalization_history: Mapped[list | None] = mapped_column(JSON, nullable=True)
