"""Patient repository — data access layer for patient and related tables."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


class PatientRepository:
    """Handles all DB operations for the patient aggregate."""

    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Patient ────────────────────────────────────────────────

    async def find_by_username(self, username: str) -> Patient | None:
        result = await self._db.execute(
            select(Patient).where(Patient.username == username)
        )
        return result.scalar_one_or_none()

    async def find_by_id(self, patient_id: str) -> Patient | None:
        result = await self._db.execute(
            select(Patient).where(Patient.patient_id == patient_id)
        )
        return result.scalar_one_or_none()

    async def create(self, patient: Patient) -> Patient:
        self._db.add(patient)
        await self._db.flush()
        return patient

    # ── Child records (bulk) ───────────────────────────────────

    async def add_medical_conditions(self, items: list[PatientMedicalCondition]):
        for item in items:
            self._db.add(item)

    async def add_medications(self, items: list[PatientMedication]):
        for item in items:
            self._db.add(item)

    async def add_allergies(self, items: list[PatientAllergy]):
        for item in items:
            self._db.add(item)

    async def add_surgeries(self, items: list[PatientSurgery]):
        for item in items:
            self._db.add(item)

    async def add_family_histories(self, items: list[PatientFamilyHistory]):
        for item in items:
            self._db.add(item)

    async def add_vital_sign(self, item: PatientVitalSign):
        self._db.add(item)

    async def add_social_history(self, item: PatientSocialHistory):
        self._db.add(item)

    async def add_lifestyle(self, item: PatientLifestyle):
        self._db.add(item)

    async def add_vaccinations(self, items: list[PatientVaccination]):
        for item in items:
            self._db.add(item)

    async def add_documents(self, items: list[PatientDocument]):
        for item in items:
            self._db.add(item)

    async def add_screenings(self, items: list[PatientScreening]):
        for item in items:
            self._db.add(item)

    # ── Child records (read) ───────────────────────────────────

    async def get_medical_conditions(self, patient_id: str) -> list[PatientMedicalCondition]:
        result = await self._db.execute(
            select(PatientMedicalCondition).where(PatientMedicalCondition.patient_id == patient_id)
        )
        return list(result.scalars().all())

    async def get_medications(self, patient_id: str) -> list[PatientMedication]:
        result = await self._db.execute(
            select(PatientMedication).where(PatientMedication.patient_id == patient_id)
        )
        return list(result.scalars().all())

    async def get_allergies(self, patient_id: str) -> list[PatientAllergy]:
        result = await self._db.execute(
            select(PatientAllergy).where(PatientAllergy.patient_id == patient_id)
        )
        return list(result.scalars().all())

    async def get_surgeries(self, patient_id: str) -> list[PatientSurgery]:
        result = await self._db.execute(
            select(PatientSurgery).where(PatientSurgery.patient_id == patient_id)
        )
        return list(result.scalars().all())

    async def get_family_histories(self, patient_id: str) -> list[PatientFamilyHistory]:
        result = await self._db.execute(
            select(PatientFamilyHistory).where(PatientFamilyHistory.patient_id == patient_id)
        )
        return list(result.scalars().all())

    async def get_latest_vital_sign(self, patient_id: str) -> PatientVitalSign | None:
        result = await self._db.execute(
            select(PatientVitalSign)
            .where(PatientVitalSign.patient_id == patient_id)
            .order_by(PatientVitalSign.created_at.desc())
        )
        return result.scalars().first()

    async def get_social_history(self, patient_id: str) -> PatientSocialHistory | None:
        result = await self._db.execute(
            select(PatientSocialHistory).where(PatientSocialHistory.patient_id == patient_id)
        )
        return result.scalars().first()

    async def get_lifestyle(self, patient_id: str) -> PatientLifestyle | None:
        result = await self._db.execute(
            select(PatientLifestyle).where(PatientLifestyle.patient_id == patient_id)
        )
        return result.scalars().first()

    async def get_vaccinations(self, patient_id: str) -> list[PatientVaccination]:
        result = await self._db.execute(
            select(PatientVaccination).where(PatientVaccination.patient_id == patient_id)
        )
        return list(result.scalars().all())

    async def get_documents(self, patient_id: str) -> list[PatientDocument]:
        result = await self._db.execute(
            select(PatientDocument).where(PatientDocument.patient_id == patient_id)
        )
        return list(result.scalars().all())

    async def get_screenings(self, patient_id: str) -> list[PatientScreening]:
        result = await self._db.execute(
            select(PatientScreening).where(PatientScreening.patient_id == patient_id)
        )
        return list(result.scalars().all())
