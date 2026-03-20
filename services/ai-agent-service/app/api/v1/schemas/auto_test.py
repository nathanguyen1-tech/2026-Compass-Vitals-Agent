"""Auto Test API request/response schemas."""

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    case_id: str
    primary_symptom: str
    secondary_symptoms: list[str] = []
    context: str = ""
    patient_history: str = ""
    severity: str = "medium"  # "low" | "medium" | "high" | "critical"
    personality: str = "cooperative"  # "cooperative" | "anxious" | "vague" | "talkative" | "reluctant"
    language_mix: str = "vi"  # "vi" | "en" | "mixed"
    expected_safety: str = "normal"  # "normal" | "emergency"


class ScenarioGenerateRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=20)
    severity_filter: str = "all"  # "all" | "low" | "medium" | "high" | "critical"
    topic: str = "all"  # "all" | "sot" | "dau_nguc" | "kho_tho" | ...
    reference_content: str = ""  # nội dung file .md kịch bản tham khảo


class ScenarioGenerateResponse(BaseModel):
    scenarios: list[Scenario]


class PatientRespondRequest(BaseModel):
    scenario: Scenario
    conversation_history: list[dict] = []  # [{role: "patient"|"agent", content: str}]
    agent_message: str
    reference_content: str = ""  # nội dung file .md — hướng dẫn cách trả lời


class PatientRespondResponse(BaseModel):
    patient_message: str
    should_end: bool = False
    end_reason: str | None = None


class EvaluateRequest(BaseModel):
    scenario: Scenario
    conversation_history: list[dict]
    reference_content: str = ""  # nội dung file .md — tiêu chí đánh giá tham khảo


class EvaluationResult(BaseModel):
    safety_detection: str = "PASS"  # "PASS" | "FAIL"
    safety_comment: str = ""
    history_completeness: int = Field(default=3, ge=1, le=5)
    critical_issues: list[str] = []  # lỗi nguy hiểm phát hiện được
    clinical_advice_quality: int = Field(default=3, ge=1, le=5)
    empathy_communication: int = Field(default=2, ge=1, le=3)
    language_grammar: int = Field(default=1, ge=1, le=2)
    final_verdict: str = "PASS"  # "PASS" | "NEEDS_IMPROVEMENT" | "FAIL"
    recommendation: str = ""


class EvaluateResponse(BaseModel):
    result: EvaluationResult


class ExportRequest(BaseModel):
    test_run_id: str
    timestamp: str = ""
    summary: dict = {}
    results: list[dict] = []
    failed_cases_summary: list[dict] = []
