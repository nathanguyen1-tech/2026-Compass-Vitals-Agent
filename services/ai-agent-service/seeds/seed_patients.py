"""Seeder — 10 demo patients with diverse profiles for ai_agent_db.

Usage:
    cd services/ai-agent-service
    python -m seeds.seed_patients
"""

import asyncio
from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.database.engine import async_engine, async_session_factory


def ulid() -> str:
    """Generate a 26-char lowercase ULID — matches PHP Str::lower(Str::ulid())."""
    return str(ULID()).lower()


# ── 10 Patients ────────────────────────────────────────────────────────────

ORG_ID = "01jd00000000000000000org01"

PATIENTS = [
    {
        "patient_id": "01jd0000000000000000pat001",
        "username": "nguyen.an",
        "first_name": "Nguyen Van",
        "last_name": "An",
        "gender": "male",
        "date_of_birth": date(1958, 3, 15),
        "phone": "+1-714-555-0101",
        "email": "an.nguyen@example.com",
        "preferred_language": "vi",
        "onboarding_phase": 4,
        "onboarding_status": "completed",
    },
    {
        "patient_id": "01jd0000000000000000pat002",
        "username": "tran.bich",
        "first_name": "Tran Thi",
        "last_name": "Bich",
        "gender": "female",
        "date_of_birth": date(1972, 7, 22),
        "phone": "+1-714-555-0102",
        "email": "bich.tran@example.com",
        "preferred_language": "vi",
        "onboarding_phase": 4,
        "onboarding_status": "completed",
    },
    {
        "patient_id": "01jd0000000000000000pat003",
        "username": "le.cuong",
        "first_name": "Le Hoang",
        "last_name": "Cuong",
        "gender": "male",
        "date_of_birth": date(1985, 11, 8),
        "phone": "+1-714-555-0103",
        "email": "cuong.le@example.com",
        "preferred_language": "en",
        "onboarding_phase": 3,
        "onboarding_status": "in_progress",
    },
    {
        "patient_id": "01jd0000000000000000pat004",
        "username": "pham.dung",
        "first_name": "Pham Thi",
        "last_name": "Dung",
        "gender": "female",
        "date_of_birth": date(1965, 1, 30),
        "phone": "+1-714-555-0104",
        "email": "dung.pham@example.com",
        "preferred_language": "vi",
        "onboarding_phase": 4,
        "onboarding_status": "completed",
    },
    {
        "patient_id": "01jd0000000000000000pat005",
        "username": "vo.em",
        "first_name": "Vo Minh",
        "last_name": "Em",
        "gender": "male",
        "date_of_birth": date(1990, 5, 12),
        "phone": "+1-714-555-0105",
        "email": "em.vo@example.com",
        "preferred_language": "en",
        "onboarding_phase": 2,
        "onboarding_status": "in_progress",
    },
    {
        "patient_id": "01jd0000000000000000pat006",
        "username": "huynh.fern",
        "first_name": "Huynh Thi",
        "last_name": "Fern",
        "gender": "female",
        "date_of_birth": date(1948, 9, 3),
        "phone": "+1-714-555-0106",
        "email": "fern.huynh@example.com",
        "preferred_language": "vi",
        "onboarding_phase": 4,
        "onboarding_status": "completed",
    },
    {
        "patient_id": "01jd0000000000000000pat007",
        "username": "dang.gia",
        "first_name": "Dang Quoc",
        "last_name": "Gia",
        "gender": "male",
        "date_of_birth": date(1978, 12, 25),
        "phone": "+1-714-555-0107",
        "email": "gia.dang@example.com",
        "preferred_language": "vi",
        "onboarding_phase": 4,
        "onboarding_status": "completed",
    },
    {
        "patient_id": "01jd0000000000000000pat008",
        "username": "bui.hanh",
        "first_name": "Bui Thi",
        "last_name": "Hanh",
        "gender": "female",
        "date_of_birth": date(1995, 4, 18),
        "phone": "+1-714-555-0108",
        "email": "hanh.bui@example.com",
        "preferred_language": "en",
        "onboarding_phase": 1,
        "onboarding_status": "in_progress",
    },
    {
        "patient_id": "01jd0000000000000000pat009",
        "username": "ngo.ich",
        "first_name": "Ngo Van",
        "last_name": "Ich",
        "gender": "male",
        "date_of_birth": date(1955, 6, 7),
        "phone": "+1-714-555-0109",
        "email": "ich.ngo@example.com",
        "preferred_language": "vi",
        "onboarding_phase": 4,
        "onboarding_status": "completed",
    },
    {
        "patient_id": "01jd0000000000000000pat010",
        "username": "ly.kim",
        "first_name": "Ly Thi",
        "last_name": "Kim",
        "gender": "female",
        "date_of_birth": date(1982, 10, 14),
        "phone": "+1-714-555-0110",
        "email": "kim.ly@example.com",
        "preferred_language": "vi",
        "onboarding_phase": 4,
        "onboarding_status": "completed",
    },
]

# ── Medical Conditions ─────────────────────────────────────────────────────

MEDICAL_CONDITIONS = [
    # Patient 1 — An (68y, male): hypertension + diabetes + cholesterol
    {"patient_idx": 0, "condition_name": "Hypertension", "condition_type": "hypertension", "severity": "moderate", "diagnosed_year": 2005, "status": "managed"},
    {"patient_idx": 0, "condition_name": "Type 2 Diabetes", "condition_type": "diabetes", "severity": "moderate", "diagnosed_year": 2010, "status": "managed"},
    {"patient_idx": 0, "condition_name": "Hypercholesterolemia", "condition_type": "cholesterol", "severity": "mild", "diagnosed_year": 2012, "status": "managed"},
    # Patient 2 — Bich (53y, female): asthma + thyroid
    {"patient_idx": 1, "condition_name": "Asthma", "condition_type": "asthma", "severity": "mild", "diagnosed_year": 1995, "status": "managed"},
    {"patient_idx": 1, "condition_name": "Hypothyroidism", "condition_type": "other", "severity": "mild", "diagnosed_year": 2018, "status": "active"},
    # Patient 3 — Cuong (40y, male): anxiety
    {"patient_idx": 2, "condition_name": "Generalized Anxiety Disorder", "condition_type": "mental_disorder", "severity": "moderate", "diagnosed_year": 2020, "status": "active"},
    # Patient 4 — Dung (61y, female): hypertension + osteoporosis + breast cancer (resolved)
    {"patient_idx": 3, "condition_name": "Hypertension", "condition_type": "hypertension", "severity": "moderate", "diagnosed_year": 2008, "status": "managed"},
    {"patient_idx": 3, "condition_name": "Osteoporosis", "condition_type": "other", "severity": "moderate", "diagnosed_year": 2019, "status": "active"},
    {"patient_idx": 3, "condition_name": "Breast Cancer Stage I", "condition_type": "cancer", "severity": "moderate", "diagnosed_year": 2016, "status": "resolved"},
    # Patient 5 — Em (35y, male): no chronic conditions (healthy)
    # Patient 6 — Fern (77y, female): heart failure + diabetes + Alzheimer
    {"patient_idx": 5, "condition_name": "Congestive Heart Failure", "condition_type": "cardiovascular", "severity": "severe", "diagnosed_year": 2015, "status": "active"},
    {"patient_idx": 5, "condition_name": "Type 2 Diabetes", "condition_type": "diabetes", "severity": "moderate", "diagnosed_year": 2000, "status": "managed"},
    {"patient_idx": 5, "condition_name": "Alzheimer's Disease", "condition_type": "other", "severity": "mild", "diagnosed_year": 2023, "status": "active"},
    # Patient 7 — Gia (47y, male): gout + fatty liver
    {"patient_idx": 6, "condition_name": "Gout", "condition_type": "other", "severity": "moderate", "diagnosed_year": 2019, "status": "active"},
    {"patient_idx": 6, "condition_name": "Non-alcoholic Fatty Liver", "condition_type": "liver_disease", "severity": "mild", "diagnosed_year": 2021, "status": "active"},
    # Patient 8 — Hanh (30y, female): migraine
    {"patient_idx": 7, "condition_name": "Chronic Migraine", "condition_type": "other", "severity": "moderate", "diagnosed_year": 2022, "status": "active"},
    # Patient 9 — Ich (70y, male): COPD + hypertension + kidney disease
    {"patient_idx": 8, "condition_name": "COPD", "condition_type": "asthma", "severity": "severe", "diagnosed_year": 2012, "status": "active"},
    {"patient_idx": 8, "condition_name": "Hypertension", "condition_type": "hypertension", "severity": "severe", "diagnosed_year": 1998, "status": "managed"},
    {"patient_idx": 8, "condition_name": "Chronic Kidney Disease Stage 3", "condition_type": "kidney_disease", "severity": "moderate", "diagnosed_year": 2020, "status": "active"},
    # Patient 10 — Kim (43y, female): lupus + depression
    {"patient_idx": 9, "condition_name": "Systemic Lupus Erythematosus", "condition_type": "autoimmune", "severity": "moderate", "diagnosed_year": 2015, "status": "active"},
    {"patient_idx": 9, "condition_name": "Major Depressive Disorder", "condition_type": "mental_disorder", "severity": "moderate", "diagnosed_year": 2017, "status": "managed"},
]

# ── Medications ────────────────────────────────────────────────────────────

MEDICATIONS = [
    # An — hypertension/diabetes/cholesterol meds
    {"patient_idx": 0, "drug_name": "Lisinopril", "dosage": "10mg", "frequency": "Once daily", "medication_type": "prescription"},
    {"patient_idx": 0, "drug_name": "Metformin", "dosage": "500mg", "frequency": "Twice daily", "medication_type": "prescription"},
    {"patient_idx": 0, "drug_name": "Atorvastatin", "dosage": "20mg", "frequency": "Once daily at night", "medication_type": "prescription"},
    # Bich — asthma + thyroid
    {"patient_idx": 1, "drug_name": "Albuterol Inhaler", "dosage": "2 puffs", "frequency": "As needed", "medication_type": "prescription"},
    {"patient_idx": 1, "drug_name": "Levothyroxine", "dosage": "50mcg", "frequency": "Once daily morning", "medication_type": "prescription"},
    {"patient_idx": 1, "drug_name": "Calcium + Vitamin D", "dosage": "600mg/400IU", "frequency": "Once daily", "medication_type": "vitamin"},
    # Cuong — anxiety
    {"patient_idx": 2, "drug_name": "Sertraline", "dosage": "50mg", "frequency": "Once daily", "medication_type": "prescription"},
    # Dung — hypertension + osteoporosis
    {"patient_idx": 3, "drug_name": "Amlodipine", "dosage": "5mg", "frequency": "Once daily", "medication_type": "prescription"},
    {"patient_idx": 3, "drug_name": "Alendronate", "dosage": "70mg", "frequency": "Once weekly", "medication_type": "prescription"},
    # Em — healthy, just vitamins
    {"patient_idx": 4, "drug_name": "Multivitamin", "dosage": "1 tablet", "frequency": "Once daily", "medication_type": "vitamin"},
    {"patient_idx": 4, "drug_name": "Fish Oil Omega-3", "dosage": "1000mg", "frequency": "Once daily", "medication_type": "vitamin"},
    # Fern — heart failure + diabetes + Alzheimer
    {"patient_idx": 5, "drug_name": "Furosemide", "dosage": "40mg", "frequency": "Once daily", "medication_type": "prescription"},
    {"patient_idx": 5, "drug_name": "Carvedilol", "dosage": "12.5mg", "frequency": "Twice daily", "medication_type": "prescription"},
    {"patient_idx": 5, "drug_name": "Insulin Glargine", "dosage": "20 units", "frequency": "Once daily at bedtime", "medication_type": "prescription"},
    {"patient_idx": 5, "drug_name": "Donepezil", "dosage": "5mg", "frequency": "Once daily at night", "medication_type": "prescription"},
    # Gia — gout
    {"patient_idx": 6, "drug_name": "Allopurinol", "dosage": "300mg", "frequency": "Once daily", "medication_type": "prescription"},
    {"patient_idx": 6, "drug_name": "Colchicine", "dosage": "0.6mg", "frequency": "As needed for flares", "medication_type": "prescription"},
    {"patient_idx": 6, "drug_name": "Tra Atiso (Artichoke tea)", "dosage": "1 cup", "frequency": "Daily", "medication_type": "herbal"},
    # Hanh — migraine
    {"patient_idx": 7, "drug_name": "Sumatriptan", "dosage": "50mg", "frequency": "As needed", "medication_type": "prescription"},
    {"patient_idx": 7, "drug_name": "Ibuprofen", "dosage": "400mg", "frequency": "As needed", "medication_type": "painkiller"},
    # Ich — COPD + hypertension + kidney
    {"patient_idx": 8, "drug_name": "Tiotropium Inhaler", "dosage": "18mcg", "frequency": "Once daily", "medication_type": "prescription"},
    {"patient_idx": 8, "drug_name": "Losartan", "dosage": "50mg", "frequency": "Once daily", "medication_type": "prescription"},
    {"patient_idx": 8, "drug_name": "Sodium Bicarbonate", "dosage": "650mg", "frequency": "Three times daily", "medication_type": "prescription"},
    # Kim — lupus + depression
    {"patient_idx": 9, "drug_name": "Hydroxychloroquine", "dosage": "200mg", "frequency": "Twice daily", "medication_type": "prescription"},
    {"patient_idx": 9, "drug_name": "Prednisone", "dosage": "5mg", "frequency": "Once daily", "medication_type": "prescription"},
    {"patient_idx": 9, "drug_name": "Escitalopram", "dosage": "10mg", "frequency": "Once daily", "medication_type": "prescription"},
]

# ── Allergies ──────────────────────────────────────────────────────────────

ALLERGIES = [
    {"patient_idx": 0, "allergen": "Penicillin", "allergy_type": "drug", "reaction": "Rash, hives", "severity": "moderate"},
    {"patient_idx": 1, "allergen": "Shellfish", "allergy_type": "food", "reaction": "Swelling, difficulty breathing", "severity": "severe"},
    {"patient_idx": 1, "allergen": "Dust mites", "allergy_type": "environmental", "reaction": "Sneezing, congestion", "severity": "mild"},
    {"patient_idx": 3, "allergen": "Sulfa drugs", "allergy_type": "drug", "reaction": "Skin rash", "severity": "moderate"},
    {"patient_idx": 5, "allergen": "Aspirin", "allergy_type": "drug", "reaction": "GI bleeding risk", "severity": "severe"},
    {"patient_idx": 5, "allergen": "Latex", "allergy_type": "environmental", "reaction": "Contact dermatitis", "severity": "mild"},
    {"patient_idx": 7, "allergen": "Pollen", "allergy_type": "environmental", "reaction": "Sneezing, watery eyes", "severity": "mild"},
    {"patient_idx": 8, "allergen": "Codeine", "allergy_type": "drug", "reaction": "Nausea, vomiting", "severity": "moderate"},
    {"patient_idx": 9, "allergen": "Ibuprofen", "allergy_type": "drug", "reaction": "Worsens lupus flares", "severity": "moderate"},
    {"patient_idx": 9, "allergen": "Peanuts", "allergy_type": "food", "reaction": "Anaphylaxis", "severity": "severe"},
]

# ── Surgeries ──────────────────────────────────────────────────────────────

SURGERIES = [
    {"patient_idx": 0, "procedure_name": "Coronary Artery Bypass (CABG)", "surgery_year": 2018, "hospital": "Hoag Memorial Hospital", "complications": None},
    {"patient_idx": 1, "procedure_name": "Appendectomy", "surgery_year": 2001, "hospital": "Cho Ray Hospital", "complications": None},
    {"patient_idx": 3, "procedure_name": "Lumpectomy (breast cancer)", "surgery_year": 2016, "hospital": "UCI Medical Center", "complications": None},
    {"patient_idx": 3, "procedure_name": "Total Knee Replacement (left)", "surgery_year": 2022, "hospital": "St. Joseph Hospital", "complications": "Post-op infection, resolved with antibiotics"},
    {"patient_idx": 5, "procedure_name": "Cataract Surgery (both eyes)", "surgery_year": 2020, "hospital": "UCI Medical Center", "complications": None},
    {"patient_idx": 6, "procedure_name": "Cholecystectomy (gallbladder)", "surgery_year": 2017, "hospital": "Garden Grove Hospital", "complications": None},
    {"patient_idx": 8, "procedure_name": "Hernia Repair", "surgery_year": 2008, "hospital": "Little Saigon Medical", "complications": None},
    {"patient_idx": 8, "procedure_name": "AV Fistula Creation (dialysis access)", "surgery_year": 2024, "hospital": "UCI Medical Center", "complications": None},
]

# ── Family Histories ───────────────────────────────────────────────────────

FAMILY_HISTORIES = [
    # An
    {"patient_idx": 0, "condition": "Heart disease", "relation": "father", "age_of_onset": 55, "is_deceased": True, "cause_of_death": "Myocardial infarction"},
    {"patient_idx": 0, "condition": "Type 2 Diabetes", "relation": "mother", "age_of_onset": 60, "is_deceased": False},
    # Bich
    {"patient_idx": 1, "condition": "Breast cancer", "relation": "mother", "age_of_onset": 58, "is_deceased": True, "cause_of_death": "Breast cancer"},
    {"patient_idx": 1, "condition": "Hypertension", "relation": "father", "age_of_onset": 50, "is_deceased": False},
    # Dung
    {"patient_idx": 3, "condition": "Breast cancer", "relation": "mother", "age_of_onset": 55, "is_deceased": True, "cause_of_death": "Breast cancer"},
    {"patient_idx": 3, "condition": "Stroke", "relation": "father", "age_of_onset": 65, "is_deceased": True, "cause_of_death": "Stroke"},
    # Fern
    {"patient_idx": 5, "condition": "Alzheimer's disease", "relation": "mother", "age_of_onset": 72, "is_deceased": True, "cause_of_death": "Complications of dementia"},
    {"patient_idx": 5, "condition": "Heart disease", "relation": "father", "age_of_onset": 60, "is_deceased": True, "cause_of_death": "Heart failure"},
    {"patient_idx": 5, "condition": "Type 2 Diabetes", "relation": "sibling", "age_of_onset": 55, "is_deceased": False},
    # Ich
    {"patient_idx": 8, "condition": "Lung cancer", "relation": "father", "age_of_onset": 62, "is_deceased": True, "cause_of_death": "Lung cancer"},
    {"patient_idx": 8, "condition": "Hypertension", "relation": "mother", "age_of_onset": 50, "is_deceased": False},
    # Kim
    {"patient_idx": 9, "condition": "Lupus", "relation": "mother", "age_of_onset": 35, "is_deceased": False},
    {"patient_idx": 9, "condition": "Depression", "relation": "sibling", "age_of_onset": 28, "is_deceased": False},
]

# ── Vital Signs ────────────────────────────────────────────────────────────

VITAL_SIGNS = [
    {"patient_idx": 0, "height_cm": 165, "weight_kg": 78, "bmi": 28.7, "bp_systolic": 142, "bp_diastolic": 88, "heart_rate": 76, "temperature_c": 36.8, "spo2": 97, "source": "manual"},
    {"patient_idx": 1, "height_cm": 158, "weight_kg": 55, "bmi": 22.0, "bp_systolic": 118, "bp_diastolic": 75, "heart_rate": 72, "temperature_c": 36.6, "spo2": 98, "source": "manual"},
    {"patient_idx": 2, "height_cm": 175, "weight_kg": 82, "bmi": 26.8, "bp_systolic": 125, "bp_diastolic": 80, "heart_rate": 80, "temperature_c": 36.7, "spo2": 99, "source": "wearable"},
    {"patient_idx": 3, "height_cm": 155, "weight_kg": 60, "bmi": 24.9, "bp_systolic": 138, "bp_diastolic": 85, "heart_rate": 74, "temperature_c": 36.5, "spo2": 97, "source": "manual"},
    {"patient_idx": 4, "height_cm": 172, "weight_kg": 70, "bmi": 23.7, "bp_systolic": 120, "bp_diastolic": 78, "heart_rate": 68, "temperature_c": 36.6, "spo2": 99, "source": "wearable"},
    {"patient_idx": 5, "height_cm": 150, "weight_kg": 52, "bmi": 23.1, "bp_systolic": 155, "bp_diastolic": 92, "heart_rate": 88, "temperature_c": 36.4, "spo2": 93, "source": "manual"},
    {"patient_idx": 6, "height_cm": 170, "weight_kg": 95, "bmi": 32.9, "bp_systolic": 135, "bp_diastolic": 82, "heart_rate": 78, "temperature_c": 36.7, "spo2": 98, "source": "manual"},
    {"patient_idx": 7, "height_cm": 162, "weight_kg": 52, "bmi": 19.8, "bp_systolic": 110, "bp_diastolic": 70, "heart_rate": 66, "temperature_c": 36.5, "spo2": 99, "source": "wearable"},
    {"patient_idx": 8, "height_cm": 168, "weight_kg": 72, "bmi": 25.5, "bp_systolic": 158, "bp_diastolic": 95, "heart_rate": 82, "temperature_c": 36.8, "spo2": 91, "source": "manual"},
    {"patient_idx": 9, "height_cm": 160, "weight_kg": 58, "bmi": 22.7, "bp_systolic": 122, "bp_diastolic": 78, "heart_rate": 74, "temperature_c": 36.6, "spo2": 98, "source": "manual"},
]

# ── Social History ─────────────────────────────────────────────────────────

SOCIAL_HISTORIES = [
    {
        "patient_idx": 0, "occupation": "Retired mechanic", "work_environment": "Auto repair shop (retired)",
        "chemical_exposure": True, "chemical_exposure_details": "Motor oil, brake fluid (30 years)",
        "smoking_status": "former", "cigarettes_per_day": None, "smoking_years": 20, "wants_to_quit": None,
        "alcohol_status": "occasional", "alcohol_frequency": "1-2 times/month", "alcohol_type": "Beer", "alcohol_amount": "1-2 cans",
        "substance_use": False,
        "hospitalization_history": [
            {"year": 2018, "reason": "CABG surgery", "hospital": "Hoag Memorial", "duration_days": 7},
        ],
    },
    {
        "patient_idx": 1, "occupation": "Nail salon owner", "work_environment": "Nail salon",
        "chemical_exposure": True, "chemical_exposure_details": "Acetone, nail chemicals (25 years)",
        "smoking_status": "never",
        "alcohol_status": "never",
        "substance_use": False,
        "hospitalization_history": [],
    },
    {
        "patient_idx": 2, "occupation": "Software engineer", "work_environment": "Office / remote",
        "chemical_exposure": False,
        "smoking_status": "never",
        "alcohol_status": "occasional", "alcohol_frequency": "Weekends", "alcohol_type": "Wine, craft beer", "alcohol_amount": "2-3 drinks",
        "substance_use": False,
        "hospitalization_history": [],
    },
    {
        "patient_idx": 3, "occupation": "Retired seamstress", "work_environment": "Garment factory (retired)",
        "chemical_exposure": True, "chemical_exposure_details": "Fabric dyes",
        "smoking_status": "never",
        "alcohol_status": "never",
        "substance_use": False,
        "hospitalization_history": [
            {"year": 2016, "reason": "Lumpectomy + chemo", "hospital": "UCI Medical Center", "duration_days": 3},
            {"year": 2022, "reason": "Knee replacement", "hospital": "St. Joseph Hospital", "duration_days": 5},
        ],
    },
    {
        "patient_idx": 4, "occupation": "Personal trainer", "work_environment": "Gym",
        "chemical_exposure": False,
        "smoking_status": "never",
        "alcohol_status": "occasional", "alcohol_frequency": "1-2 times/week", "alcohol_type": "Beer", "alcohol_amount": "1-2 drinks",
        "substance_use": False,
        "hospitalization_history": [],
    },
    {
        "patient_idx": 5, "occupation": "Retired (homemaker)", "work_environment": "Home",
        "chemical_exposure": False,
        "smoking_status": "never",
        "alcohol_status": "never",
        "substance_use": False,
        "hospitalization_history": [
            {"year": 2021, "reason": "Heart failure exacerbation", "hospital": "UCI Medical Center", "duration_days": 10},
            {"year": 2023, "reason": "Pneumonia", "hospital": "Garden Grove Hospital", "duration_days": 7},
        ],
    },
    {
        "patient_idx": 6, "occupation": "Restaurant owner", "work_environment": "Vietnamese restaurant kitchen",
        "chemical_exposure": False,
        "smoking_status": "current", "cigarettes_per_day": 10, "smoking_years": 25, "wants_to_quit": True,
        "alcohol_status": "regular", "alcohol_frequency": "Daily", "alcohol_type": "Beer, rice wine", "alcohol_amount": "3-4 drinks",
        "substance_use": False,
        "hospitalization_history": [
            {"year": 2019, "reason": "Acute gout attack", "hospital": "Garden Grove Hospital", "duration_days": 2},
        ],
    },
    {
        "patient_idx": 7, "occupation": "Marketing manager", "work_environment": "Office",
        "chemical_exposure": False,
        "smoking_status": "never",
        "alcohol_status": "occasional", "alcohol_frequency": "Social events", "alcohol_type": "Wine", "alcohol_amount": "1 glass",
        "substance_use": False,
        "hospitalization_history": [],
    },
    {
        "patient_idx": 8, "occupation": "Retired fisherman", "work_environment": "Fishing boats (retired)",
        "chemical_exposure": True, "chemical_exposure_details": "Diesel fumes, saltwater",
        "smoking_status": "former", "cigarettes_per_day": None, "smoking_years": 40, "wants_to_quit": None,
        "alcohol_status": "former", "alcohol_frequency": None, "alcohol_type": "Rice wine", "alcohol_amount": "Heavy (quit 2020)",
        "substance_use": False,
        "hospitalization_history": [
            {"year": 2022, "reason": "COPD exacerbation", "hospital": "Little Saigon Medical", "duration_days": 5},
            {"year": 2024, "reason": "AV fistula surgery", "hospital": "UCI Medical Center", "duration_days": 2},
        ],
    },
    {
        "patient_idx": 9, "occupation": "Accountant", "work_environment": "Office",
        "chemical_exposure": False,
        "smoking_status": "never",
        "alcohol_status": "never",
        "substance_use": False,
        "hospitalization_history": [
            {"year": 2021, "reason": "Lupus flare — nephritis", "hospital": "UCI Medical Center", "duration_days": 6},
        ],
    },
]

# ── Lifestyle ──────────────────────────────────────────────────────────────

LIFESTYLES = [
    {  # An — 68y diabetic, moderate lifestyle
        "patient_idx": 0,
        "nutrition": {"meals_per_day": 3, "vegetables_daily": True, "fast_food_freq": "rarely", "soda_freq": "never", "caffeine_cups": 2, "special_diet": "low-sodium, diabetic"},
        "exercise": {"gym": False, "walking_daily": True, "sitting_hours": 6, "exercise_minutes_per_week": 150},
        "sleep": {"hours_per_night": 6, "quality": "fair", "insomnia": True, "sleep_aids": False, "bedtime": "22:00", "wake_time": "05:00"},
        "mental_health": {"stress_level": 4, "stress_sources": ["health"], "mood": "good", "anxiety": False, "meditation": False, "social_support": "good"},
        "functional_status": {"self_care": "independent", "mobility": "independent", "daily_activities": "independent", "needs_assistance": False},
        "sdoh": {"housing_stable": True, "food_security": True, "transportation": True, "social_support": True, "financial_difficulty": False},
        "reproductive_health": None,
    },
    {  # Bich — 53y nail salon owner
        "patient_idx": 1,
        "nutrition": {"meals_per_day": 3, "vegetables_daily": True, "fast_food_freq": "monthly", "soda_freq": "rarely", "caffeine_cups": 3, "special_diet": "none"},
        "exercise": {"gym": False, "walking_daily": False, "sitting_hours": 8, "exercise_minutes_per_week": 60},
        "sleep": {"hours_per_night": 7, "quality": "good", "insomnia": False, "sleep_aids": False, "bedtime": "23:00", "wake_time": "06:30"},
        "mental_health": {"stress_level": 6, "stress_sources": ["work", "finance"], "mood": "fair", "anxiety": True, "meditation": False, "social_support": "good"},
        "functional_status": {"self_care": "independent", "mobility": "independent", "daily_activities": "independent", "needs_assistance": False},
        "sdoh": {"housing_stable": True, "food_security": True, "transportation": True, "social_support": True, "financial_difficulty": False},
        "reproductive_health": {"menstrual_status": "perimenopause", "pregnancies": 3, "menopause": False, "thyroid_condition": "hypothyroid", "hormone_therapy": False},
    },
    {  # Cuong — 40y software engineer, anxiety
        "patient_idx": 2,
        "nutrition": {"meals_per_day": 2, "vegetables_daily": False, "fast_food_freq": "weekly", "soda_freq": "weekly", "caffeine_cups": 4, "special_diet": "none"},
        "exercise": {"gym": True, "walking_daily": False, "sitting_hours": 10, "exercise_minutes_per_week": 180},
        "sleep": {"hours_per_night": 5, "quality": "poor", "insomnia": True, "sleep_aids": True, "bedtime": "01:00", "wake_time": "07:00"},
        "mental_health": {"stress_level": 8, "stress_sources": ["work", "relationships"], "mood": "fair", "anxiety": True, "meditation": True, "social_support": "limited"},
        "functional_status": {"self_care": "independent", "mobility": "independent", "daily_activities": "independent", "needs_assistance": False},
        "sdoh": {"housing_stable": True, "food_security": True, "transportation": True, "social_support": False, "financial_difficulty": False},
        "reproductive_health": None,
    },
    {  # Fern — 77y, heart failure, needs assistance
        "patient_idx": 5,
        "nutrition": {"meals_per_day": 3, "vegetables_daily": True, "fast_food_freq": "never", "soda_freq": "never", "caffeine_cups": 0, "special_diet": "low-sodium, heart-healthy"},
        "exercise": {"gym": False, "walking_daily": True, "sitting_hours": 8, "exercise_minutes_per_week": 60},
        "sleep": {"hours_per_night": 8, "quality": "fair", "insomnia": False, "sleep_aids": False, "bedtime": "21:00", "wake_time": "05:30"},
        "mental_health": {"stress_level": 5, "stress_sources": ["health", "memory"], "mood": "fair", "anxiety": True, "meditation": False, "social_support": "good"},
        "functional_status": {"self_care": "needs_some_help", "mobility": "uses_walker", "daily_activities": "needs_some_help", "needs_assistance": True},
        "sdoh": {"housing_stable": True, "food_security": True, "transportation": False, "social_support": True, "financial_difficulty": False},
        "reproductive_health": {"menstrual_status": "postmenopause", "pregnancies": 5, "menopause": True, "thyroid_condition": "none", "hormone_therapy": False},
    },
    {  # Gia — 47y restaurant owner, smoker, heavy drinker
        "patient_idx": 6,
        "nutrition": {"meals_per_day": 2, "vegetables_daily": True, "fast_food_freq": "rarely", "soda_freq": "daily", "caffeine_cups": 3, "special_diet": "none"},
        "exercise": {"gym": False, "walking_daily": False, "sitting_hours": 4, "exercise_minutes_per_week": 30},
        "sleep": {"hours_per_night": 5, "quality": "poor", "insomnia": False, "sleep_aids": False, "bedtime": "00:30", "wake_time": "06:00"},
        "mental_health": {"stress_level": 7, "stress_sources": ["work", "finance"], "mood": "fair", "anxiety": False, "meditation": False, "social_support": "good"},
        "functional_status": {"self_care": "independent", "mobility": "independent", "daily_activities": "independent", "needs_assistance": False},
        "sdoh": {"housing_stable": True, "food_security": True, "transportation": True, "social_support": True, "financial_difficulty": True},
        "reproductive_health": None,
    },
    {  # Ich — 70y, COPD, ex-smoker
        "patient_idx": 8,
        "nutrition": {"meals_per_day": 3, "vegetables_daily": True, "fast_food_freq": "never", "soda_freq": "never", "caffeine_cups": 1, "special_diet": "renal diet, low-protein"},
        "exercise": {"gym": False, "walking_daily": True, "sitting_hours": 7, "exercise_minutes_per_week": 90},
        "sleep": {"hours_per_night": 6, "quality": "fair", "insomnia": True, "sleep_aids": False, "bedtime": "22:00", "wake_time": "04:30"},
        "mental_health": {"stress_level": 6, "stress_sources": ["health", "finance"], "mood": "fair", "anxiety": True, "meditation": False, "social_support": "limited"},
        "functional_status": {"self_care": "independent", "mobility": "slow_but_independent", "daily_activities": "needs_some_help", "needs_assistance": True},
        "sdoh": {"housing_stable": True, "food_security": True, "transportation": False, "social_support": True, "financial_difficulty": True},
        "reproductive_health": None,
    },
    {  # Kim — 43y, lupus, accountant
        "patient_idx": 9,
        "nutrition": {"meals_per_day": 3, "vegetables_daily": True, "fast_food_freq": "monthly", "soda_freq": "rarely", "caffeine_cups": 2, "special_diet": "anti-inflammatory"},
        "exercise": {"gym": False, "walking_daily": True, "sitting_hours": 8, "exercise_minutes_per_week": 120},
        "sleep": {"hours_per_night": 7, "quality": "fair", "insomnia": True, "sleep_aids": True, "bedtime": "23:00", "wake_time": "06:30"},
        "mental_health": {"stress_level": 7, "stress_sources": ["health", "work"], "mood": "fair", "anxiety": True, "meditation": True, "social_support": "good"},
        "functional_status": {"self_care": "independent", "mobility": "independent", "daily_activities": "independent", "needs_assistance": False},
        "sdoh": {"housing_stable": True, "food_security": True, "transportation": True, "social_support": True, "financial_difficulty": False},
        "reproductive_health": {"menstrual_status": "irregular", "pregnancies": 1, "menopause": False, "thyroid_condition": "none", "hormone_therapy": False},
    },
]

# ── Vaccinations ───────────────────────────────────────────────────────────

VACCINATIONS = [
    {"patient_idx": 0, "vaccine_name": "COVID-19 Pfizer", "date_administered": date(2021, 4, 15), "dose_number": 1},
    {"patient_idx": 0, "vaccine_name": "COVID-19 Pfizer", "date_administered": date(2021, 5, 6), "dose_number": 2},
    {"patient_idx": 0, "vaccine_name": "COVID-19 Pfizer Booster", "date_administered": date(2022, 1, 10), "dose_number": 3},
    {"patient_idx": 0, "vaccine_name": "Influenza 2025-2026", "date_administered": date(2025, 10, 1), "dose_number": 1},
    {"patient_idx": 1, "vaccine_name": "COVID-19 Moderna", "date_administered": date(2021, 5, 20), "dose_number": 1},
    {"patient_idx": 1, "vaccine_name": "COVID-19 Moderna", "date_administered": date(2021, 6, 17), "dose_number": 2},
    {"patient_idx": 5, "vaccine_name": "COVID-19 Pfizer", "date_administered": date(2021, 3, 1), "dose_number": 1},
    {"patient_idx": 5, "vaccine_name": "COVID-19 Pfizer", "date_administered": date(2021, 3, 22), "dose_number": 2},
    {"patient_idx": 5, "vaccine_name": "Pneumococcal (Prevnar 20)", "date_administered": date(2023, 9, 15), "dose_number": 1},
    {"patient_idx": 5, "vaccine_name": "Influenza 2025-2026", "date_administered": date(2025, 9, 20), "dose_number": 1},
    {"patient_idx": 8, "vaccine_name": "COVID-19 Pfizer", "date_administered": date(2021, 6, 1), "dose_number": 1},
    {"patient_idx": 8, "vaccine_name": "Influenza 2025-2026", "date_administered": date(2025, 10, 5), "dose_number": 1},
    {"patient_idx": 9, "vaccine_name": "COVID-19 Moderna", "date_administered": date(2021, 4, 10), "dose_number": 1},
    {"patient_idx": 9, "vaccine_name": "COVID-19 Moderna", "date_administered": date(2021, 5, 8), "dose_number": 2},
    {"patient_idx": 9, "vaccine_name": "Influenza 2025-2026", "date_administered": date(2025, 10, 12), "dose_number": 1},
]

# ── Screenings (Preventive Care + Cognitive) ───────────────────────────────

SCREENINGS = [
    {"patient_idx": 1, "screening_type": "mammogram", "screening_date": date(2025, 6, 15), "result": "normal", "next_due_date": date(2026, 6, 15)},
    {"patient_idx": 1, "screening_type": "pap_smear", "screening_date": date(2024, 3, 10), "result": "normal", "next_due_date": date(2027, 3, 10)},
    {"patient_idx": 3, "screening_type": "mammogram", "screening_date": date(2025, 9, 1), "result": "normal", "next_due_date": date(2026, 9, 1)},
    {"patient_idx": 3, "screening_type": "colonoscopy", "screening_date": date(2023, 5, 20), "result": "normal", "next_due_date": date(2033, 5, 20)},
    {"patient_idx": 3, "screening_type": "bone_density", "screening_date": date(2025, 1, 10), "result": "abnormal", "next_due_date": date(2027, 1, 10), "notes": "T-score -2.8, osteoporosis confirmed"},
    {"patient_idx": 5, "screening_type": "cognitive_assessment", "screening_date": date(2025, 11, 1), "result": "abnormal", "next_due_date": date(2026, 5, 1), "notes": "MMSE score 22/30 — mild cognitive impairment"},
    {"patient_idx": 5, "screening_type": "eye_exam", "screening_date": date(2025, 8, 15), "result": "normal", "next_due_date": date(2026, 8, 15)},
    {"patient_idx": 8, "screening_type": "colonoscopy", "screening_date": date(2022, 7, 10), "result": "polyps removed", "next_due_date": date(2025, 7, 10), "notes": "2 adenomatous polyps removed"},
    {"patient_idx": 9, "screening_type": "eye_exam", "screening_date": date(2025, 4, 20), "result": "normal", "next_due_date": date(2026, 4, 20), "notes": "Hydroxychloroquine retinal screening — clear"},
    {"patient_idx": 9, "screening_type": "dental_exam", "screening_date": date(2025, 10, 5), "result": "normal", "next_due_date": date(2026, 4, 5)},
]


# ════════════════════════════════════════════════════════════════════════════
# Seed runner
# ════════════════════════════════════════════════════════════════════════════

async def seed():
    async with async_session_factory() as session:
        # Check if already seeded
        result = await session.execute(text("SELECT COUNT(*) FROM patients"))
        count = result.scalar()
        if count and count > 0:
            print(f"  Already seeded ({count} patients). Skipping. Use --force to re-seed.")
            return

        patient_ids = []

        # 1. Patients
        for p in PATIENTS:
            await session.execute(
                text("""
                    INSERT INTO patients (patient_id, organization_id, username, first_name, last_name, gender,
                        date_of_birth, phone, email, preferred_language, onboarding_phase, onboarding_status)
                    VALUES (:patient_id, :organization_id, :username, :first_name, :last_name, :gender,
                        :date_of_birth, :phone, :email, :preferred_language, :onboarding_phase, :onboarding_status)
                """),
                {**p, "organization_id": ORG_ID},
            )
            patient_ids.append(p["patient_id"])
        print(f"  Inserted {len(PATIENTS)} patients")

        # 2. Medical Conditions
        for mc in MEDICAL_CONDITIONS:
            pid = patient_ids[mc["patient_idx"]]
            await session.execute(
                text("""
                    INSERT INTO patient_medical_conditions (condition_id, patient_id, condition_name, condition_type, severity, diagnosed_year, status)
                    VALUES (:cid, :pid, :name, :type, :severity, :year, :status)
                """),
                {"cid": ulid(), "pid": pid, "name": mc["condition_name"], "type": mc["condition_type"],
                 "severity": mc.get("severity"), "year": mc.get("diagnosed_year"), "status": mc.get("status", "active")},
            )
        print(f"  Inserted {len(MEDICAL_CONDITIONS)} medical conditions")

        # 3. Medications
        for med in MEDICATIONS:
            pid = patient_ids[med["patient_idx"]]
            await session.execute(
                text("""
                    INSERT INTO patient_medications (medication_id, patient_id, drug_name, dosage, frequency, medication_type)
                    VALUES (:mid, :pid, :drug, :dosage, :freq, :type)
                """),
                {"mid": ulid(), "pid": pid, "drug": med["drug_name"], "dosage": med.get("dosage"),
                 "freq": med.get("frequency"), "type": med.get("medication_type", "prescription")},
            )
        print(f"  Inserted {len(MEDICATIONS)} medications")

        # 4. Allergies
        for a in ALLERGIES:
            pid = patient_ids[a["patient_idx"]]
            await session.execute(
                text("""
                    INSERT INTO patient_allergies (allergy_id, patient_id, allergen, allergy_type, reaction, severity)
                    VALUES (:aid, :pid, :allergen, :type, :reaction, :severity)
                """),
                {"aid": ulid(), "pid": pid, "allergen": a["allergen"], "type": a["allergy_type"],
                 "reaction": a.get("reaction"), "severity": a.get("severity", "mild")},
            )
        print(f"  Inserted {len(ALLERGIES)} allergies")

        # 5. Surgeries
        for s in SURGERIES:
            pid = patient_ids[s["patient_idx"]]
            await session.execute(
                text("""
                    INSERT INTO patient_surgeries (surgery_id, patient_id, procedure_name, surgery_year, hospital, complications)
                    VALUES (:sid, :pid, :proc, :year, :hospital, :comp)
                """),
                {"sid": ulid(), "pid": pid, "proc": s["procedure_name"], "year": s.get("surgery_year"),
                 "hospital": s.get("hospital"), "comp": s.get("complications")},
            )
        print(f"  Inserted {len(SURGERIES)} surgeries")

        # 6. Family Histories
        for fh in FAMILY_HISTORIES:
            pid = patient_ids[fh["patient_idx"]]
            await session.execute(
                text("""
                    INSERT INTO patient_family_histories (family_history_id, patient_id, condition, relation, age_of_onset, is_deceased, cause_of_death)
                    VALUES (:fhid, :pid, :condition, :relation, :age, :deceased, :cause)
                """),
                {"fhid": ulid(), "pid": pid, "condition": fh["condition"], "relation": fh["relation"],
                 "age": fh.get("age_of_onset"), "deceased": fh.get("is_deceased", False), "cause": fh.get("cause_of_death")},
            )
        print(f"  Inserted {len(FAMILY_HISTORIES)} family histories")

        # 7. Vital Signs
        for vs in VITAL_SIGNS:
            pid = patient_ids[vs["patient_idx"]]
            await session.execute(
                text("""
                    INSERT INTO patient_vital_signs (vital_id, patient_id, height_cm, weight_kg, bmi,
                        bp_systolic, bp_diastolic, heart_rate, temperature_c, spo2, source)
                    VALUES (:vid, :pid, :h, :w, :bmi, :sys, :dia, :hr, :temp, :spo2, :src)
                """),
                {"vid": ulid(), "pid": pid, "h": vs["height_cm"], "w": vs["weight_kg"], "bmi": vs["bmi"],
                 "sys": vs["bp_systolic"], "dia": vs["bp_diastolic"], "hr": vs["heart_rate"],
                 "temp": vs["temperature_c"], "spo2": vs["spo2"], "src": vs["source"]},
            )
        print(f"  Inserted {len(VITAL_SIGNS)} vital signs")

        # 8. Social Histories
        import json
        for sh in SOCIAL_HISTORIES:
            pid = patient_ids[sh["patient_idx"]]
            await session.execute(
                text("""
                    INSERT INTO patient_social_history (social_history_id, patient_id,
                        occupation, work_environment, chemical_exposure, chemical_exposure_details,
                        smoking_status, cigarettes_per_day, smoking_years, wants_to_quit,
                        alcohol_status, alcohol_frequency, alcohol_type, alcohol_amount,
                        substance_use, hospitalization_history)
                    VALUES (:shid, :pid, :occ, :env, :chem, :chem_d,
                        :smoke, :cig, :smoke_y, :quit,
                        :alc, :alc_f, :alc_t, :alc_a,
                        :sub, :hosp)
                """),
                {"shid": ulid(), "pid": pid,
                 "occ": sh.get("occupation"), "env": sh.get("work_environment"),
                 "chem": sh.get("chemical_exposure", False), "chem_d": sh.get("chemical_exposure_details"),
                 "smoke": sh.get("smoking_status", "never"), "cig": sh.get("cigarettes_per_day"),
                 "smoke_y": sh.get("smoking_years"), "quit": sh.get("wants_to_quit"),
                 "alc": sh.get("alcohol_status", "never"), "alc_f": sh.get("alcohol_frequency"),
                 "alc_t": sh.get("alcohol_type"), "alc_a": sh.get("alcohol_amount"),
                 "sub": sh.get("substance_use", False),
                 "hosp": json.dumps(sh.get("hospitalization_history", []))},
            )
        print(f"  Inserted {len(SOCIAL_HISTORIES)} social histories")

        # 9. Lifestyles
        for ls in LIFESTYLES:
            pid = patient_ids[ls["patient_idx"]]
            await session.execute(
                text("""
                    INSERT INTO patient_lifestyle (lifestyle_id, patient_id,
                        nutrition, exercise, sleep, mental_health, functional_status, sdoh, reproductive_health)
                    VALUES (:lid, :pid, :nutr, :exer, :sleep, :mental, :func, :sdoh, :repro)
                """),
                {"lid": ulid(), "pid": pid,
                 "nutr": json.dumps(ls.get("nutrition")), "exer": json.dumps(ls.get("exercise")),
                 "sleep": json.dumps(ls.get("sleep")), "mental": json.dumps(ls.get("mental_health")),
                 "func": json.dumps(ls.get("functional_status")), "sdoh": json.dumps(ls.get("sdoh")),
                 "repro": json.dumps(ls.get("reproductive_health"))},
            )
        print(f"  Inserted {len(LIFESTYLES)} lifestyle records")

        # 10. Vaccinations
        for v in VACCINATIONS:
            pid = patient_ids[v["patient_idx"]]
            await session.execute(
                text("""
                    INSERT INTO patient_vaccinations (vaccination_id, patient_id, vaccine_name, date_administered, dose_number)
                    VALUES (:vid, :pid, :name, :date, :dose)
                """),
                {"vid": ulid(), "pid": pid, "name": v["vaccine_name"],
                 "date": v.get("date_administered"), "dose": v.get("dose_number")},
            )
        print(f"  Inserted {len(VACCINATIONS)} vaccinations")

        # 11. Screenings
        for sc in SCREENINGS:
            pid = patient_ids[sc["patient_idx"]]
            await session.execute(
                text("""
                    INSERT INTO patient_screenings (screening_id, patient_id, screening_type, screening_date, result, next_due_date, notes)
                    VALUES (:sid, :pid, :type, :date, :result, :next, :notes)
                """),
                {"sid": ulid(), "pid": pid, "type": sc["screening_type"],
                 "date": sc.get("screening_date"), "result": sc.get("result"),
                 "next": sc.get("next_due_date"), "notes": sc.get("notes")},
            )
        print(f"  Inserted {len(SCREENINGS)} screenings")

        await session.commit()
        print("\n  Seed completed successfully!")


async def main():
    import sys
    force = "--force" in sys.argv

    print("\n=== Seeding ai_agent_db ===\n")

    if force:
        async with async_session_factory() as session:
            for table in [
                "patient_screenings", "patient_documents", "patient_vaccinations",
                "patient_lifestyle", "patient_social_history", "patient_vital_signs",
                "patient_family_histories", "patient_surgeries", "patient_allergies",
                "patient_medications", "patient_medical_conditions", "patients",
            ]:
                await session.execute(text(f"DELETE FROM {table}"))
            await session.commit()
            print("  Cleared all patient data (--force)\n")

    await seed()
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
