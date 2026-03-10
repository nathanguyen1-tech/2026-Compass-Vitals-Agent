"""Care Plan Generator — Compiles CareFlowState into a structured care plan.

NOT an LLM agent — pure Python data transformation.
Reads all agent results from state and produces a unified CarePlanResponse.
"""

from datetime import datetime, timezone

from app.agents.state import CareFlowState
from app.api.v1.schemas.flow import (
    CarePlanResponse,
    CriticSummary,
    DiagnosisItem,
    ImagingOrder,
    LabOrder,
    MedicationOrder,
    MonitoringPlan,
)


def generate_care_plan(state: CareFlowState, session_id: str) -> CarePlanResponse:
    """Compile all agent results from CareFlowState into a CarePlanResponse."""
    # === Diagnoses ===
    differential_diagnoses = []
    primary_diagnosis = ""
    primary_diagnosis_vi = ""

    for dx in state.get("differential_diagnoses", []):
        item = DiagnosisItem(
            name=dx.get("name", "Unknown"),
            name_vi=dx.get("name_vi", ""),
            confidence=dx.get("confidence", 0),
            reasoning=dx.get("reasoning", ""),
        )
        differential_diagnoses.append(item)

    # Primary = highest confidence
    if differential_diagnoses:
        primary = max(differential_diagnoses, key=lambda d: d.confidence)
        primary_diagnosis = primary.name
        primary_diagnosis_vi = primary.name_vi

    # === Orders ===
    medications = []
    lab_orders = []
    imaging_orders = []
    monitoring = None

    for order in state.get("order_recommendations", []):
        order_type = order.get("type", "")

        if order_type == "medication":
            medications.append(
                MedicationOrder(
                    drug=order.get("drug", ""),
                    drug_vi=order.get("drug_vi", ""),
                    dosage=order.get("dosage", ""),
                    frequency=order.get("frequency", ""),
                    frequency_vi=order.get("frequency_vi", ""),
                    duration=order.get("duration", ""),
                    route=order.get("route", ""),
                    rationale=order.get("rationale", ""),
                )
            )
        elif order_type == "lab":
            lab_orders.append(
                LabOrder(
                    test_name=order.get("test_name", ""),
                    test_name_vi=order.get("test_name_vi", ""),
                    rationale=order.get("rationale", ""),
                    urgency=order.get("urgency", "routine"),
                )
            )
        elif order_type == "imaging":
            imaging_orders.append(
                ImagingOrder(
                    imaging_type=order.get("imaging_type", ""),
                    imaging_type_vi=order.get("imaging_type_vi", order.get("type_vi", "")),
                    rationale=order.get("rationale", ""),
                    urgency=order.get("urgency", "routine"),
                )
            )
        elif order_type == "monitoring":
            monitoring = MonitoringPlan(
                follow_up_interval=order.get("follow_up_interval", ""),
                follow_up_interval_vi=order.get("follow_up_interval_vi", ""),
                warning_signs=order.get("warning_signs", []),
                warning_signs_vi=order.get("warning_signs_vi", []),
                instructions=order.get("instructions", ""),
                instructions_vi=order.get("instructions_vi", ""),
            )

    # === Critic Summary ===
    critic_validation = state.get("critic_validation") or {}
    critic = None
    if critic_validation:
        critic = CriticSummary(
            status=critic_validation.get("status", "unknown"),
            safety_score=critic_validation.get("overall_safety_score", 0),
            issues_count=len(critic_validation.get("issues", [])),
            summary=critic_validation.get("summary", ""),
            summary_vi=critic_validation.get("summary_vi", ""),
        )

    return CarePlanResponse(
        case_id=state.get("case_id", "unknown"),
        session_id=session_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        severity=state.get("severity", "routine") or "routine",
        primary_diagnosis=primary_diagnosis,
        primary_diagnosis_vi=primary_diagnosis_vi,
        differential_diagnoses=differential_diagnoses,
        medications=medications,
        lab_orders=lab_orders,
        imaging_orders=imaging_orders,
        monitoring=monitoring,
        critic=critic,
        confidence_score=state.get("confidence_score", 0) or 0,
        detected_language=state.get("detected_language", "vi"),
        is_emergency=state.get("is_emergency", False),
    )
