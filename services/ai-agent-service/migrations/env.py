"""Alembic environment configuration — reads DB URL from app.config."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.domain.models.base import Base

# Import ALL models so Base.metadata knows about them
from app.domain.models.agent_session import AgentSession  # noqa: F401
from app.domain.models.screening_result import ScreeningResult  # noqa: F401
from app.domain.models.cultural_expression import CulturalExpression  # noqa: F401
from app.domain.models.phi_mapping import PHIMapping  # noqa: F401

# Patient profile & onboarding (SERVICE-02)
from app.domain.models.patient import Patient  # noqa: F401
from app.domain.models.patient_medical_condition import PatientMedicalCondition  # noqa: F401
from app.domain.models.patient_medication import PatientMedication  # noqa: F401
from app.domain.models.patient_allergy import PatientAllergy  # noqa: F401
from app.domain.models.patient_surgery import PatientSurgery  # noqa: F401
from app.domain.models.patient_family_history import PatientFamilyHistory  # noqa: F401
from app.domain.models.patient_vital_sign import PatientVitalSign  # noqa: F401
from app.domain.models.patient_social_history import PatientSocialHistory  # noqa: F401
from app.domain.models.patient_lifestyle import PatientLifestyle  # noqa: F401
from app.domain.models.patient_vaccination import PatientVaccination  # noqa: F401
from app.domain.models.patient_document import PatientDocument  # noqa: F401
from app.domain.models.patient_screening import PatientScreening  # noqa: F401

config = context.config

# Set sqlalchemy.url from our app config (sync driver for Alembic)
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL script without DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to DB and applies changes."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
