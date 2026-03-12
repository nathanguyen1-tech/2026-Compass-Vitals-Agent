"""Domain models — SQLAlchemy ORM tables."""

from app.domain.models.base import Base, TimestampMixin, generate_uuid
from app.domain.models.agent_session import AgentSession
from app.domain.models.screening_result import ScreeningResult
from app.domain.models.cultural_expression import CulturalExpression
from app.domain.models.phi_mapping import PHIMapping

# Patient profile & onboarding (SERVICE-02)
from app.domain.models.patient import Patient
from app.domain.models.patient_medical_condition import PatientMedicalCondition
from app.domain.models.patient_medication import PatientMedication
from app.domain.models.patient_allergy import PatientAllergy
from app.domain.models.patient_surgery import PatientSurgery
from app.domain.models.patient_family_history import PatientFamilyHistory
from app.domain.models.patient_vital_sign import PatientVitalSign
from app.domain.models.patient_social_history import PatientSocialHistory
from app.domain.models.patient_lifestyle import PatientLifestyle
from app.domain.models.patient_vaccination import PatientVaccination
from app.domain.models.patient_document import PatientDocument
from app.domain.models.patient_screening import PatientScreening

__all__ = [
    "Base",
    "TimestampMixin",
    "generate_uuid",
    "AgentSession",
    "ScreeningResult",
    "CulturalExpression",
    "PHIMapping",
    "Patient",
    "PatientMedicalCondition",
    "PatientMedication",
    "PatientAllergy",
    "PatientSurgery",
    "PatientFamilyHistory",
    "PatientVitalSign",
    "PatientSocialHistory",
    "PatientLifestyle",
    "PatientVaccination",
    "PatientDocument",
    "PatientScreening",
]
