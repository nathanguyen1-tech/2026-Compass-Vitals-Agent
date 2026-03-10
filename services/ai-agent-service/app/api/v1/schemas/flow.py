"""Flow API schemas — request/response models for care flow management."""

from pydantic import BaseModel


class FlowStatusResponse(BaseModel):
    session_id: str
    current_agent: str  # "intake" | "screening" | "proposer" | "critic" | "complete"
    intake_complete: bool
    screening_complete: bool
    proposer_complete: bool
    critic_complete: bool
    critic_approved: bool | None = None
    care_plan_ready: bool
    clinical_summary_ready: bool = False
    clinical_summary_v2_ready: bool = False
    soap_note_ready: bool = False
    is_emergency: bool
    severity: str | None = None


class DiagnosisItem(BaseModel):
    name: str
    name_vi: str = ""
    confidence: float
    reasoning: str = ""


class MedicationOrder(BaseModel):
    drug: str
    drug_vi: str = ""
    dosage: str
    frequency: str
    frequency_vi: str = ""
    duration: str = ""
    route: str = ""
    rationale: str = ""


class LabOrder(BaseModel):
    test_name: str
    test_name_vi: str = ""
    rationale: str = ""
    urgency: str = "routine"


class ImagingOrder(BaseModel):
    imaging_type: str
    imaging_type_vi: str = ""
    rationale: str = ""
    urgency: str = "routine"


class MonitoringPlan(BaseModel):
    follow_up_interval: str = ""
    follow_up_interval_vi: str = ""
    warning_signs: list[str] = []
    warning_signs_vi: list[str] = []
    instructions: str = ""
    instructions_vi: str = ""


class CriticSummary(BaseModel):
    status: str  # "approved" | "rejected" | "needs_modification"
    safety_score: float
    issues_count: int
    summary: str = ""
    summary_vi: str = ""


class CarePlanResponse(BaseModel):
    case_id: str
    session_id: str
    generated_at: str

    # Diagnosis
    severity: str
    primary_diagnosis: str
    primary_diagnosis_vi: str = ""
    differential_diagnoses: list[DiagnosisItem] = []

    # Treatment
    medications: list[MedicationOrder] = []
    lab_orders: list[LabOrder] = []
    imaging_orders: list[ImagingOrder] = []

    # Monitoring
    monitoring: MonitoringPlan | None = None

    # Safety
    critic: CriticSummary | None = None

    # Metadata
    confidence_score: float = 0.0
    detected_language: str = "vi"
    is_emergency: bool = False


# ── Clinical Summary schemas ──


class OLDCARTSDetail(BaseModel):
    onset: str = ""
    location: str = ""
    duration: str = ""
    character: str = ""
    aggravating: str = ""
    alleviating: str = ""
    radiation: str = ""
    timing: str = ""
    severity: str = ""


class ChiefComplaintSection(BaseModel):
    complaint: str
    complaint_vi: str = ""
    oldcarts: OLDCARTSDetail = OLDCARTSDetail()
    onset_description: str = ""


class HPISection(BaseModel):
    demographics: str = ""
    demographics_vi: str = ""
    past_medical_history: str = ""
    past_medical_history_vi: str = ""
    surgical_history: str = ""
    current_medications: str = ""
    current_medications_vi: str = ""
    allergies: str = ""
    allergies_vi: str = ""
    social_history: str = ""
    social_history_vi: str = ""
    family_history: str = ""
    family_history_vi: str = ""


class ROSSystem(BaseModel):
    system_name: str
    system_name_vi: str = ""
    positives: list[str] = []
    pertinent_negatives: list[str] = []
    past_similar_episodes: str = ""


class ScreeningFinding(BaseModel):
    """Key finding from screening agent analysis."""
    clinical_impression: str = ""
    key_findings: list[str] = []
    severity: str = ""
    recommended_urgency: str = ""


class ClinicalSummaryResponse(BaseModel):
    case_id: str
    session_id: str
    generated_at: str
    detected_language: str = "vi"

    chief_complaint: ChiefComplaintSection
    hpi: HPISection
    ros: list[ROSSystem] = []
    cultural_expressions: list[dict] = []
    is_emergency: bool = False
    red_flags: list[str] = []

    # Screening results (enrichment from screening agent)
    screening: ScreeningFinding | None = None
    differential_diagnoses: list[DiagnosisItem] = []
    severity: str = ""
    conversation_summary: str = ""


# ── SOAP Note schemas ──


class SOAPSection(BaseModel):
    content: str
    content_vi: str = ""


class SOAPNoteResponse(BaseModel):
    case_id: str
    session_id: str
    generated_at: str

    subjective: SOAPSection
    objective: SOAPSection
    assessment: SOAPSection
    plan: SOAPSection

    severity: str
    primary_diagnosis: str
    confidence_score: float = 0.0
    critic_safety_score: float = 0.0
    needs_human_review: bool = False
    human_review_reason: str | None = None
    safety_concerns: list[str] = []
