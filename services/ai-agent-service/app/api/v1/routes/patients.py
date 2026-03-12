"""Patient registration API — inserts data into all 12 patient tables."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.patients import PatientRegisterRequest, PatientRegisterResponse
from app.database.engine import get_db
from app.domain.models import (
    Patient,
    PatientMedicalCondition,
    PatientMedication,
    PatientAllergy,
    PatientSurgery,
    PatientFamilyHistory,
    PatientVitalSign,
    PatientSocialHistory,
    PatientLifestyle,
    PatientVaccination,
    PatientDocument,
    PatientScreening,
)

logger = structlog.get_logger()

router = APIRouter()


@router.post("/patients", response_model=PatientRegisterResponse)
async def register_patient(
    body: PatientRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new patient with all onboarding data (12 tables)."""

    # Default organization_id for now (will come from auth token later)
    org_id = "01jd00000000000000000org01"

    # --- 1. patients ---
    patient = Patient(
        organization_id=org_id,
        **body.patient.model_dump(),
    )
    db.add(patient)
    await db.flush()  # get patient_id

    pid = patient.patient_id
    logger.info("patient_created", patient_id=pid, username=body.patient.username)

    # --- 2. medical_conditions ---
    for item in body.medical_conditions:
        db.add(PatientMedicalCondition(patient_id=pid, **item.model_dump()))

    # --- 3. medications ---
    for item in body.medications:
        db.add(PatientMedication(patient_id=pid, **item.model_dump()))

    # --- 4. allergies ---
    for item in body.allergies:
        db.add(PatientAllergy(patient_id=pid, **item.model_dump()))

    # --- 5. surgeries ---
    for item in body.surgeries:
        db.add(PatientSurgery(patient_id=pid, **item.model_dump()))

    # --- 6. family_histories ---
    for item in body.family_histories:
        db.add(PatientFamilyHistory(patient_id=pid, **item.model_dump()))

    # --- 7. vital_signs ---
    if body.vital_signs:
        data = body.vital_signs.model_dump(exclude_none=True)
        if data:  # at least one measurement provided
            db.add(PatientVitalSign(patient_id=pid, **data))

    # --- 8. social_history ---
    if body.social_history:
        db.add(PatientSocialHistory(patient_id=pid, **body.social_history.model_dump()))

    # --- 9. lifestyle ---
    if body.lifestyle:
        db.add(PatientLifestyle(patient_id=pid, **body.lifestyle.model_dump()))

    # --- 10. vaccinations ---
    for item in body.vaccinations:
        db.add(PatientVaccination(patient_id=pid, **item.model_dump()))

    # --- 11. documents ---
    for item in body.documents:
        db.add(PatientDocument(patient_id=pid, **item.model_dump()))

    # --- 12. screenings ---
    for item in body.screenings:
        db.add(PatientScreening(patient_id=pid, **item.model_dump()))

    # Update onboarding status
    patient.onboarding_phase = 4
    patient.onboarding_status = "completed"

    # commit handled by get_db() context manager
    logger.info("patient_registration_complete", patient_id=pid)

    return PatientRegisterResponse(patient_id=pid, username=body.patient.username)
