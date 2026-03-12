"""Initial schema — agent_sessions, screening_results, cultural_expressions, phi_mappings.

Revision ID: 0001
Revises: None
Create Date: 2026-03-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- agent_sessions ---
    op.create_table(
        "agent_sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("state_snapshot", postgresql.JSON, nullable=True),
        sa.Column("messages", postgresql.JSON, server_default="[]"),
        sa.Column("status", sa.String(20), server_default="active", index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # --- screening_results ---
    op.create_table(
        "screening_results",
        sa.Column("result_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("clinical_assessment", sa.Text, nullable=False),
        sa.Column("differential_diagnoses", postgresql.JSON, server_default="[]"),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("confidence_breakdown", postgresql.JSON, nullable=True),
        sa.Column("is_emergency", sa.Boolean, server_default="false"),
        sa.Column("raw_llm_response", postgresql.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # --- cultural_expressions ---
    op.create_table(
        "cultural_expressions",
        sa.Column("expression_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vietnamese_text", sa.String(200), nullable=False, unique=True),
        sa.Column("variants", postgresql.JSON, server_default="[]"),
        sa.Column("medical_meaning", sa.Text, nullable=False),
        sa.Column("medical_terms", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("context_clues", postgresql.JSON, server_default="[]"),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False),
        sa.Column("region", sa.String(20), server_default="'all'"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # --- phi_mappings ---
    op.create_table(
        "phi_mappings",
        sa.Column("mapping_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("encrypted_mapping", sa.LargeBinary, nullable=False),
        sa.Column("phi_types_found", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("phi_mappings")
    op.drop_table("cultural_expressions")
    op.drop_table("screening_results")
    op.drop_table("agent_sessions")
