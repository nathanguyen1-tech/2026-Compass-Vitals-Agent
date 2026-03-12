"""patient_documents table — uploaded medical files (hồ sơ y tế upload)."""

from sqlalchemy import BigInteger, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class PatientDocument(Base, TimestampMixin):
    __tablename__ = "patient_documents"

    document_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    patient_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # lab_result, imaging (ECG/ultrasound/xray/ct/mri), prescription,
    # medical_record, vaccination_record, wearable_data, other
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # S3 key or local path
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # bytes
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Flexible metadata: {"test_date": "2025-01-01", "lab_name": "...", "results_summary": "..."}
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
