"""Patient profile & onboarding — 12 tables for SERVICE-02 onboarding data.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ULID = 26-char lowercase string (matches PHP Str::lower(Str::ulid()))
ULID = sa.String(26)

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================
    # GĐ1: Thông tin cơ bản & Y tế thiết yếu
    # ==========================================

    # --- patients ---
    op.create_table(
        "patients",
        sa.Column("patient_id", ULID, primary_key=True),
        sa.Column("organization_id", ULID, nullable=False, index=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("gender", sa.String(20), nullable=False),
        sa.Column("date_of_birth", sa.Date, nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("preferred_language", sa.String(10), server_default="vi"),
        sa.Column("onboarding_phase", sa.Integer, server_default="0"),
        sa.Column("onboarding_status", sa.String(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- patient_medical_conditions ---
    op.create_table(
        "patient_medical_conditions",
        sa.Column("condition_id", ULID, primary_key=True),
        sa.Column(
            "patient_id", ULID,
            sa.ForeignKey("patients.patient_id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("condition_name", sa.String(200), nullable=False),
        sa.Column("condition_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("diagnosed_year", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- patient_medications ---
    op.create_table(
        "patient_medications",
        sa.Column("medication_id", ULID, primary_key=True),
        sa.Column(
            "patient_id", ULID,
            sa.ForeignKey("patients.patient_id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("drug_name", sa.String(200), nullable=False),
        sa.Column("dosage", sa.String(100), nullable=True),
        sa.Column("frequency", sa.String(100), nullable=True),
        sa.Column("route", sa.String(50), nullable=True),
        sa.Column("medication_type", sa.String(30), server_default="prescription"),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("is_current", sa.Boolean, server_default="true"),
        sa.Column("prescribed_by", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- patient_allergies ---
    op.create_table(
        "patient_allergies",
        sa.Column("allergy_id", ULID, primary_key=True),
        sa.Column(
            "patient_id", ULID,
            sa.ForeignKey("patients.patient_id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("allergen", sa.String(200), nullable=False),
        sa.Column("allergy_type", sa.String(30), nullable=False),
        sa.Column("reaction", sa.String(200), nullable=True),
        sa.Column("severity", sa.String(20), server_default="mild"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ==========================================
    # GĐ2: Lịch sử y tế & Xã hội mở rộng
    # ==========================================

    # --- patient_surgeries ---
    op.create_table(
        "patient_surgeries",
        sa.Column("surgery_id", ULID, primary_key=True),
        sa.Column(
            "patient_id", ULID,
            sa.ForeignKey("patients.patient_id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("procedure_name", sa.String(300), nullable=False),
        sa.Column("surgery_year", sa.Integer, nullable=True),
        sa.Column("hospital", sa.String(300), nullable=True),
        sa.Column("complications", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- patient_family_histories ---
    op.create_table(
        "patient_family_histories",
        sa.Column("family_history_id", ULID, primary_key=True),
        sa.Column(
            "patient_id", ULID,
            sa.ForeignKey("patients.patient_id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("condition", sa.String(200), nullable=False),
        sa.Column("relation", sa.String(50), nullable=False),
        sa.Column("age_of_onset", sa.Integer, nullable=True),
        sa.Column("is_deceased", sa.Boolean, server_default="false"),
        sa.Column("cause_of_death", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- patient_vital_signs ---
    op.create_table(
        "patient_vital_signs",
        sa.Column("vital_id", ULID, primary_key=True),
        sa.Column(
            "patient_id", ULID,
            sa.ForeignKey("patients.patient_id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("height_cm", sa.Numeric(5, 1), nullable=True),
        sa.Column("weight_kg", sa.Numeric(5, 1), nullable=True),
        sa.Column("bmi", sa.Numeric(4, 1), nullable=True),
        sa.Column("bp_systolic", sa.Integer, nullable=True),
        sa.Column("bp_diastolic", sa.Integer, nullable=True),
        sa.Column("heart_rate", sa.Integer, nullable=True),
        sa.Column("temperature_c", sa.Numeric(4, 1), nullable=True),
        sa.Column("spo2", sa.Integer, nullable=True),
        sa.Column("source", sa.String(30), server_default="manual"),
        sa.Column("measured_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- patient_social_history ---
    op.create_table(
        "patient_social_history",
        sa.Column("social_history_id", ULID, primary_key=True),
        sa.Column(
            "patient_id", ULID,
            sa.ForeignKey("patients.patient_id", ondelete="CASCADE"),
            nullable=False, unique=True,
        ),
        sa.Column("occupation", sa.String(200), nullable=True),
        sa.Column("work_environment", sa.String(200), nullable=True),
        sa.Column("chemical_exposure", sa.Boolean, server_default="false"),
        sa.Column("chemical_exposure_details", sa.Text, nullable=True),
        sa.Column("smoking_status", sa.String(20), server_default="never"),
        sa.Column("cigarettes_per_day", sa.Integer, nullable=True),
        sa.Column("smoking_years", sa.Integer, nullable=True),
        sa.Column("wants_to_quit", sa.Boolean, nullable=True),
        sa.Column("alcohol_status", sa.String(20), server_default="never"),
        sa.Column("alcohol_frequency", sa.String(100), nullable=True),
        sa.Column("alcohol_type", sa.String(100), nullable=True),
        sa.Column("alcohol_amount", sa.String(100), nullable=True),
        sa.Column("substance_use", sa.Boolean, server_default="false"),
        sa.Column("substance_details", sa.Text, nullable=True),
        sa.Column("hospitalization_history", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ==========================================
    # GĐ3: Đánh giá lối sống
    # ==========================================

    # --- patient_lifestyle ---
    op.create_table(
        "patient_lifestyle",
        sa.Column("lifestyle_id", ULID, primary_key=True),
        sa.Column(
            "patient_id", ULID,
            sa.ForeignKey("patients.patient_id", ondelete="CASCADE"),
            nullable=False, unique=True,
        ),
        sa.Column("nutrition", postgresql.JSON, nullable=True),
        sa.Column("exercise", postgresql.JSON, nullable=True),
        sa.Column("sleep", postgresql.JSON, nullable=True),
        sa.Column("mental_health", postgresql.JSON, nullable=True),
        sa.Column("functional_status", postgresql.JSON, nullable=True),
        sa.Column("sdoh", postgresql.JSON, nullable=True),
        sa.Column("reproductive_health", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- patient_vaccinations ---
    op.create_table(
        "patient_vaccinations",
        sa.Column("vaccination_id", ULID, primary_key=True),
        sa.Column(
            "patient_id", ULID,
            sa.ForeignKey("patients.patient_id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("vaccine_name", sa.String(200), nullable=False),
        sa.Column("date_administered", sa.Date, nullable=True),
        sa.Column("dose_number", sa.Integer, nullable=True),
        sa.Column("provider", sa.String(200), nullable=True),
        sa.Column("lot_number", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ==========================================
    # GĐ4: Upload hồ sơ & Đánh giá chuyên sâu
    # ==========================================

    # --- patient_documents ---
    op.create_table(
        "patient_documents",
        sa.Column("document_id", ULID, primary_key=True),
        sa.Column(
            "patient_id", ULID,
            sa.ForeignKey("patients.patient_id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("doc_type", sa.String(30), nullable=False, index=True),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("metadata_json", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- patient_screenings ---
    op.create_table(
        "patient_screenings",
        sa.Column("screening_id", ULID, primary_key=True),
        sa.Column(
            "patient_id", ULID,
            sa.ForeignKey("patients.patient_id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("screening_type", sa.String(50), nullable=False),
        sa.Column("screening_date", sa.Date, nullable=True),
        sa.Column("result", sa.String(100), nullable=True),
        sa.Column("provider", sa.String(200), nullable=True),
        sa.Column("next_due_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop in reverse order (children before parent)
    op.drop_table("patient_screenings")
    op.drop_table("patient_documents")
    op.drop_table("patient_vaccinations")
    op.drop_table("patient_lifestyle")
    op.drop_table("patient_social_history")
    op.drop_table("patient_vital_signs")
    op.drop_table("patient_family_histories")
    op.drop_table("patient_surgeries")
    op.drop_table("patient_allergies")
    op.drop_table("patient_medications")
    op.drop_table("patient_medical_conditions")
    op.drop_table("patients")
