"""Patient service — business logic for patient registration and profile lookup."""

import structlog

from app.api.v1.schemas.patients import (
    PatientRegisterRequest,
    PatientRegisterResponse,
    PatientProfileResponse,
    MedicalConditionOut,
    MedicationOut,
    AllergyOut,
    SurgeryOut,
    FamilyHistoryOut,
    VitalSignsOut,
    SocialHistoryOut,
    LifestyleOut,
    VaccinationOut,
    ScreeningOut,
)
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
from app.domain.repositories.patient_repository import PatientRepository

logger = structlog.get_logger()

# Default org — will come from auth token later
DEFAULT_ORG_ID = "01jd00000000000000000org01"


class PatientService:
    """Orchestrates patient registration and profile retrieval."""

    def __init__(self, repo: PatientRepository):
        self._repo = repo

    # ── Registration ───────────────────────────────────────────

    async def register(self, body: PatientRegisterRequest) -> PatientRegisterResponse:
        """Create patient + all child records in a single transaction."""

        patient = Patient(
            organization_id=DEFAULT_ORG_ID,
            **body.patient.model_dump(),
        )
        await self._repo.create(patient)
        pid = patient.patient_id
        logger.info("patient_created", patient_id=pid, username=body.patient.username)

        # Child 1:N records
        if body.medical_conditions:
            await self._repo.add_medical_conditions([
                PatientMedicalCondition(patient_id=pid, **c.model_dump())
                for c in body.medical_conditions
            ])

        if body.medications:
            await self._repo.add_medications([
                PatientMedication(patient_id=pid, **m.model_dump())
                for m in body.medications
            ])

        if body.allergies:
            await self._repo.add_allergies([
                PatientAllergy(patient_id=pid, **a.model_dump())
                for a in body.allergies
            ])

        if body.surgeries:
            await self._repo.add_surgeries([
                PatientSurgery(patient_id=pid, **s.model_dump())
                for s in body.surgeries
            ])

        if body.family_histories:
            await self._repo.add_family_histories([
                PatientFamilyHistory(patient_id=pid, **f.model_dump())
                for f in body.family_histories
            ])

        # 1:1 records
        if body.vital_signs:
            data = body.vital_signs.model_dump(exclude_none=True)
            if data:
                await self._repo.add_vital_sign(
                    PatientVitalSign(patient_id=pid, **data)
                )

        if body.social_history:
            await self._repo.add_social_history(
                PatientSocialHistory(patient_id=pid, **body.social_history.model_dump())
            )

        if body.lifestyle:
            await self._repo.add_lifestyle(
                PatientLifestyle(patient_id=pid, **body.lifestyle.model_dump())
            )

        if body.vaccinations:
            await self._repo.add_vaccinations([
                PatientVaccination(patient_id=pid, **v.model_dump())
                for v in body.vaccinations
            ])

        if body.documents:
            await self._repo.add_documents([
                PatientDocument(patient_id=pid, **d.model_dump())
                for d in body.documents
            ])

        if body.screenings:
            await self._repo.add_screenings([
                PatientScreening(patient_id=pid, **s.model_dump())
                for s in body.screenings
            ])

        # Mark onboarding complete
        patient.onboarding_phase = 4
        patient.onboarding_status = "completed"

        logger.info("patient_registration_complete", patient_id=pid)
        return PatientRegisterResponse(patient_id=pid, username=body.patient.username)

    # ── Profile lookup ─────────────────────────────────────────

    async def get_profile_by_username(self, username: str) -> PatientProfileResponse | None:
        """Fetch full patient profile by username. Returns None if not found."""

        patient = await self._repo.find_by_username(username)
        if not patient:
            return None

        pid = patient.patient_id

        conditions = await self._repo.get_medical_conditions(pid)
        medications = await self._repo.get_medications(pid)
        allergies = await self._repo.get_allergies(pid)
        surgeries = await self._repo.get_surgeries(pid)
        family_histories = await self._repo.get_family_histories(pid)
        vital_sign = await self._repo.get_latest_vital_sign(pid)
        social_history = await self._repo.get_social_history(pid)
        lifestyle = await self._repo.get_lifestyle(pid)
        vaccinations = await self._repo.get_vaccinations(pid)
        screenings = await self._repo.get_screenings(pid)

        return PatientProfileResponse(
            patient_id=patient.patient_id,
            username=patient.username,
            first_name=patient.first_name,
            last_name=patient.last_name,
            gender=patient.gender,
            date_of_birth=patient.date_of_birth,
            phone=patient.phone,
            email=patient.email,
            preferred_language=patient.preferred_language,
            onboarding_phase=patient.onboarding_phase,
            onboarding_status=patient.onboarding_status,
            medical_conditions=[
                MedicalConditionOut(
                    condition_name=c.condition_name, condition_type=c.condition_type,
                    severity=c.severity, diagnosed_year=c.diagnosed_year,
                    status=c.status, notes=c.notes,
                ) for c in conditions
            ],
            medications=[
                MedicationOut(
                    drug_name=m.drug_name, dosage=m.dosage, frequency=m.frequency,
                    route=m.route, medication_type=m.medication_type,
                    start_date=m.start_date, is_current=m.is_current,
                    prescribed_by=m.prescribed_by, notes=m.notes,
                ) for m in medications
            ],
            allergies=[
                AllergyOut(
                    allergen=a.allergen, allergy_type=a.allergy_type,
                    reaction=a.reaction, severity=a.severity, notes=a.notes,
                ) for a in allergies
            ],
            surgeries=[
                SurgeryOut(
                    procedure_name=s.procedure_name, surgery_year=s.surgery_year,
                    hospital=s.hospital, complications=s.complications, notes=s.notes,
                ) for s in surgeries
            ],
            family_histories=[
                FamilyHistoryOut(
                    condition=f.condition, relation=f.relation,
                    age_of_onset=f.age_of_onset, is_deceased=f.is_deceased,
                    cause_of_death=f.cause_of_death, notes=f.notes,
                ) for f in family_histories
            ],
            vital_signs=self._map_vital_sign(vital_sign),
            social_history=SocialHistoryOut(
                occupation=social_history.occupation,
                work_environment=social_history.work_environment,
                chemical_exposure=social_history.chemical_exposure,
                smoking_status=social_history.smoking_status,
                alcohol_status=social_history.alcohol_status,
                substance_use=social_history.substance_use,
            ) if social_history else None,
            lifestyle=LifestyleOut(
                nutrition=lifestyle.nutrition,
                exercise=lifestyle.exercise,
                sleep=lifestyle.sleep,
                mental_health=lifestyle.mental_health,
                functional_status=lifestyle.functional_status,
                sdoh=lifestyle.sdoh,
                reproductive_health=lifestyle.reproductive_health,
            ) if lifestyle else None,
            vaccinations=[
                VaccinationOut(
                    vaccine_name=v.vaccine_name, date_administered=v.date_administered,
                    dose_number=v.dose_number, provider=v.provider,
                ) for v in vaccinations
            ],
            screenings=[
                ScreeningOut(
                    screening_type=s.screening_type, screening_date=s.screening_date,
                    result=s.result, provider=s.provider, next_due_date=s.next_due_date,
                ) for s in screenings
            ],
        )

    # ── Private helpers ────────────────────────────────────────

    @staticmethod
    def _map_vital_sign(vs) -> VitalSignsOut | None:
        if not vs:
            return None
        return VitalSignsOut(
            height_cm=float(vs.height_cm) if vs.height_cm else None,
            weight_kg=float(vs.weight_kg) if vs.weight_kg else None,
            bmi=float(vs.bmi) if vs.bmi else None,
            bp_systolic=vs.bp_systolic,
            bp_diastolic=vs.bp_diastolic,
            heart_rate=vs.heart_rate,
            temperature_c=float(vs.temperature_c) if vs.temperature_c else None,
            spo2=vs.spo2,
            source=vs.source,
        )
