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
