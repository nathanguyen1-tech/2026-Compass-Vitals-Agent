"""Patient controller — thin route layer, delegates to PatientService."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.patients import (
    PatientRegisterRequest,
    PatientRegisterResponse,
    PatientProfileResponse,
)
from app.database.engine import get_db
from app.domain.repositories.patient_repository import PatientRepository
from app.domain.services.patient_service import PatientService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db)) -> PatientService:
    """Build service with repository — injected per request."""
    return PatientService(repo=PatientRepository(db))


@router.post("/patients", response_model=PatientRegisterResponse)
async def register_patient(
    body: PatientRegisterRequest,
    svc: PatientService = Depends(_get_service),
):
    """Register a new patient with all onboarding data (12 tables)."""
    return await svc.register(body)


@router.get("/patients/{username}", response_model=PatientProfileResponse)
async def get_patient_by_username(
    username: str,
    svc: PatientService = Depends(_get_service),
):
    """Fetch full patient profile by username."""
    profile = await svc.get_profile_by_username(username)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient not found")
    return profile
