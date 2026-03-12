"""Pydantic schemas for patient registration (SERVICE-02 onboarding)."""

from datetime import date

from pydantic import BaseModel


# --- 1:N child items ---

class MedicalConditionIn(BaseModel):
    condition_name: str
    condition_type: str
    severity: str | None = None
    diagnosed_year: int | None = None
    status: str = "active"
    notes: str | None = None


class MedicationIn(BaseModel):
    drug_name: str
    dosage: str | None = None
    frequency: str | None = None
    route: str | None = None
    medication_type: str = "prescription"
    start_date: date | None = None
    is_current: bool = True
    prescribed_by: str | None = None
    notes: str | None = None


class AllergyIn(BaseModel):
    allergen: str
    allergy_type: str
    reaction: str | None = None
    severity: str = "mild"
    notes: str | None = None


class SurgeryIn(BaseModel):
    procedure_name: str
    surgery_year: int | None = None
    hospital: str | None = None
    complications: str | None = None
    notes: str | None = None


class FamilyHistoryIn(BaseModel):
    condition: str
    relation: str
    age_of_onset: int | None = None
    is_deceased: bool = False
    cause_of_death: str | None = None
    notes: str | None = None


class VitalSignsIn(BaseModel):
    height_cm: float | None = None
    weight_kg: float | None = None
    bmi: float | None = None
    bp_systolic: int | None = None
    bp_diastolic: int | None = None
    heart_rate: int | None = None
    temperature_c: float | None = None
    spo2: int | None = None
    source: str = "manual"


class SocialHistoryIn(BaseModel):
    occupation: str | None = None
    work_environment: str | None = None
    chemical_exposure: bool = False
    chemical_exposure_details: str | None = None
    smoking_status: str = "never"
    cigarettes_per_day: int | None = None
    smoking_years: int | None = None
    wants_to_quit: bool | None = None
    alcohol_status: str = "never"
    alcohol_frequency: str | None = None
    alcohol_type: str | None = None
    alcohol_amount: str | None = None
    substance_use: bool = False
    substance_details: str | None = None


class LifestyleIn(BaseModel):
    nutrition: dict | None = None
    exercise: dict | None = None
    sleep: dict | None = None
    mental_health: dict | None = None
    functional_status: dict | None = None
    sdoh: dict | None = None
    reproductive_health: dict | None = None


class VaccinationIn(BaseModel):
    vaccine_name: str
    date_administered: date | None = None
    dose_number: int | None = None
    provider: str | None = None
    lot_number: str | None = None
    notes: str | None = None


class DocumentIn(BaseModel):
    doc_type: str
    file_name: str
    file_path: str
    file_size: int | None = None
    mime_type: str | None = None
    description: str | None = None
    metadata_json: dict | None = None


class ScreeningIn(BaseModel):
    screening_type: str
    screening_date: date | None = None
    result: str | None = None
    provider: str | None = None
    next_due_date: date | None = None
    notes: str | None = None


# --- Patient core ---

class PatientIn(BaseModel):
    username: str
    first_name: str
    last_name: str
    gender: str
    date_of_birth: date
    phone: str | None = None
    email: str | None = None
    preferred_language: str = "vi"


# --- Full registration payload ---

class PatientRegisterRequest(BaseModel):
    patient: PatientIn
    medical_conditions: list[MedicalConditionIn] = []
    medications: list[MedicationIn] = []
    allergies: list[AllergyIn] = []
    surgeries: list[SurgeryIn] = []
    family_histories: list[FamilyHistoryIn] = []
    vital_signs: VitalSignsIn | None = None
    social_history: SocialHistoryIn | None = None
    lifestyle: LifestyleIn | None = None
    vaccinations: list[VaccinationIn] = []
    screenings: list[ScreeningIn] = []
    documents: list[DocumentIn] = []


class PatientRegisterResponse(BaseModel):
    patient_id: str
    username: str
    message: str = "Patient registered successfully"
