"""Clinical Summary v2 Generator — GPT-4 clinical narrative for MD review.

Unlike clinical_summary_generator.py (pure Python field extraction), this calls
GPT-4 to write detailed HPI, Chief Complaint, and ROS narratives from the full
CareFlowState. Follows the same PHI de-id pattern as soap_note_generator.py.
"""

import json
from datetime import datetime, timezone

import structlog

from app.agents.prompts.clinical_summary_v2_prompt import (
    CLINICAL_SUMMARY_V2_SYSTEM_PROMPT,
)
from app.agents.state import CareFlowState
from app.agents.tools.intake_tracker import IntakeTracker, OLDCARTS_FIELDS
from app.api.v1.schemas.clinical_summary_v2 import (
    ClinicalNarrativeSection,
    ClinicalSummaryV2Response,
)
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()


def _build_clinical_summary_context(state: CareFlowState) -> str:
    """Build comprehensive context from state for the Clinical Summary v2 prompt.

    Prioritizes intake_tracker > intake_data > screening > messages.
    Excludes treatment data (orders, critic) since this is a pre-assessment document.
    """
    parts = []

    parts.append(f"CASE ID: {state.get('case_id', 'unknown')}")
    parts.append(f"SEVERITY: {state.get('severity', 'unknown')}")
    parts.append(f"DETECTED LANGUAGE: {state.get('detected_language', 'vi')}")

    # --- Reconstruct IntakeTracker for richer data ---
    tracker_data = state.get("intake_tracker")
    tracker = IntakeTracker(data=tracker_data) if tracker_data else None
    intake_data = state.get("intake_data") or {}

    # === Demographics ===
    age = (tracker.age if tracker else None) or intake_data.get("age")
    gender = (tracker.gender if tracker else None) or intake_data.get("gender")
    if age or gender:
        parts.append(f"\n=== DEMOGRAPHICS ===")
        if age:
            parts.append(f"  Age: {age}")
        if gender:
            parts.append(f"  Gender: {gender}")

    # === Chief Complaint ===
    cc = ""
    complaint_category = ""
    if tracker and tracker.cc:
        cc = tracker.cc
        complaint_category = tracker.complaint_category or ""
    elif intake_data.get("chief_complaint"):
        cc = intake_data["chief_complaint"]
        complaint_category = intake_data.get("complaint_category", "")

    if cc:
        parts.append(f"\n=== CHIEF COMPLAINT ===")
        parts.append(f"  Complaint: {cc}")
        if complaint_category:
            parts.append(f"  Complaint Category: {complaint_category}")

    # === OLDCARTS Symptom Characterization ===
    parts.append(f"\n=== OLDCARTS SYMPTOM CHARACTERIZATION ===")
    if tracker:
        for field in OLDCARTS_FIELDS:
            val = tracker.hpi.get(field)
            parts.append(f"  {field}: {val or 'Not assessed'}")
        for key, val in tracker.hpi_additional.items():
            parts.append(f"  {key}: {val}")
    else:
        for field in OLDCARTS_FIELDS:
            val = intake_data.get(field, "")
            parts.append(f"  {field}: {val or 'Not assessed'}")

    # === Past Medical History ===
    pmh = ""
    if tracker:
        pmh = tracker.pmh or ""
    else:
        pmh = intake_data.get("pmh", "")
    parts.append(f"\n=== PAST MEDICAL HISTORY ===")
    parts.append(f"  PMH: {pmh or 'Not reported'}")

    # === Current Medications ===
    meds = ""
    if tracker:
        meds = tracker.medications or ""
    else:
        meds = intake_data.get("medications", "")
    parts.append(f"\n=== CURRENT MEDICATIONS ===")
    parts.append(f"  {meds or 'Not reported'}")

    # === Allergies ===
    allergies = ""
    if tracker:
        allergies = tracker.allergies or ""
    else:
        allergies = intake_data.get("allergies", "")
    parts.append(f"\n=== ALLERGIES ===")
    parts.append(f"  {allergies or 'Not reported'}")

    # === Social/Family History ===
    social = ""
    if tracker:
        social = tracker.social_family or ""
    else:
        social = intake_data.get("social_family", "")
    parts.append(f"\n=== SOCIAL/FAMILY HISTORY ===")
    parts.append(f"  {social or 'Not reported'}")

    # === Red Flags ===
    red_flags: list[str] = []
    if tracker and tracker.red_flags_found:
        red_flags = list(tracker.red_flags_found)
    elif intake_data.get("red_flags_found"):
        red_flags = list(intake_data["red_flags_found"])
    if red_flags:
        parts.append(f"\n=== RED FLAGS ===")
        for flag in red_flags:
            parts.append(f"  - {flag}")

    # === Review of Systems (collected) ===
    ros_data: dict[str, str] = {}
    if tracker and tracker.ros_systems:
        ros_data = tracker.ros_systems
    elif intake_data.get("ros") and isinstance(intake_data["ros"], dict):
        ros_data = intake_data["ros"]
    if ros_data:
        parts.append(f"\n=== REVIEW OF SYSTEMS (collected) ===")
        for system, finding in ros_data.items():
            parts.append(f"  {system}: {finding}")

    # --- Cultural Expressions ---
    cultural = state.get("cultural_expressions", [])
    if cultural:
        parts.append("\n=== CULTURAL EXPRESSIONS ===")
        for expr in cultural:
            if isinstance(expr, dict):
                parts.append(
                    f"  '{expr.get('original', '')}' => {expr.get('medical_meaning', '')}"
                )

    # --- Screening Result ---
    screening = state.get("screening_result")
    if screening and isinstance(screening, dict):
        parts.append("\n=== SCREENING RESULTS ===")
        clinical_impression = screening.get("clinical_impression", "")
        if clinical_impression:
            parts.append(f"  Clinical Impression: {clinical_impression}")
        key_findings = screening.get("key_findings", [])
        if key_findings:
            parts.append(f"  Key Findings: {', '.join(key_findings)}")
        screening_red_flags = screening.get("red_flags", [])
        if screening_red_flags:
            parts.append(f"  Red Flags: {', '.join(screening_red_flags)}")

    # --- Differential Diagnoses ---
    dx_list = state.get("differential_diagnoses", [])
    if dx_list:
        parts.append("\n=== DIFFERENTIAL DIAGNOSES ===")
        for dx in dx_list:
            name = dx.get("name", "Unknown")
            name_vi = dx.get("name_vi", "")
            conf = dx.get("confidence", 0)
            reasoning = dx.get("reasoning", "")
            parts.append(f"  - {name} ({name_vi}) [{conf}%]: {reasoning}")

    # NOTE: Raw conversation excerpts excluded to avoid PHI leakage.
    # All clinically relevant data is captured in structured fields above.

    # --- Active Symptoms (cross-message accumulator) ---
    if tracker and tracker.active_symptoms:
        parts.append("\n=== ACTIVE SYMPTOMS ===")
        for symptom in tracker.active_symptoms:
            parts.append(f"  - {symptom}")

    # --- Flags ---
    if state.get("is_emergency"):
        parts.append("\n*** EMERGENCY CASE ***")

    if state.get("needs_human_review"):
        reason = state.get("human_review_reason", "")
        parts.append(f"\n*** NEEDS HUMAN REVIEW: {reason} ***")

    return "\n".join(parts)


def _parse_clinical_summary_response(response_text: str) -> dict:
    """Parse JSON from LLM response with fallback."""
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(
            "clinical_summary_v2.json_parse_failed", response_preview=text[:200]
        )
        return {
            "hpi": {"content": "Unable to parse structured response.", "content_vi": ""},
            "chief_complaint": {"content": response_text, "content_vi": ""},
            "ros": {"content": "Unable to parse structured response.", "content_vi": ""},
            "data_quality_notes": [
                "Clinical summary v2 parsing failed -- manual review required"
            ],
        }


async def generate_clinical_summary_v2(
    state: CareFlowState,
    session_id: str,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> ClinicalSummaryV2Response:
    """Generate a Clinical Summary v2 from the CareFlowState using GPT-4."""
    case_id = state.get("case_id", "unknown")

    # === Step 1: Build comprehensive context ===
    context = _build_clinical_summary_context(state)

    # === Step 2: PHI De-identification ===
    deidentified_context, phi_mapping = phi_deidentifier.deidentify(context)

    # === Step 3: Build LLM Messages ===
    llm_messages = [
        {"role": "system", "content": CLINICAL_SUMMARY_V2_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Generate a comprehensive Clinical Summary (HPI, Chief Complaint, ROS) "
                f"for the following clinical encounter:\n\n{deidentified_context}"
            ),
        },
    ]

    # === Step 4: Call LLM via Gateway ===
    response = await llm_gateway.generate(
        messages=llm_messages,
        agent_type="clinical_summary",
        case_id=case_id,
        temperature=0.3,
        max_tokens=4096,
    )

    # === Step 5: Re-identify response ===
    ai_response_text = response.content
    if phi_mapping:
        ai_response_text = phi_deidentifier.reidentify(ai_response_text, phi_mapping)

    # === Step 6: Parse response ===
    parsed = _parse_clinical_summary_response(ai_response_text)

    # === Step 7: Build ClinicalSummaryV2Response ===
    # Red flags from tracker, intake_data, or screening
    red_flags: list[str] = []
    tracker_data = state.get("intake_tracker")
    if tracker_data:
        t = IntakeTracker(data=tracker_data)
        red_flags = list(t.red_flags_found) if t.red_flags_found else []
    elif (state.get("intake_data") or {}).get("red_flags_found"):
        red_flags = list(state["intake_data"]["red_flags_found"])
    elif (state.get("screening_result") or {}).get("red_flags"):
        red_flags = list(state["screening_result"]["red_flags"])

    # Primary diagnosis from differentials
    dx_list = state.get("differential_diagnoses", [])
    primary_dx = ""
    if dx_list:
        primary = max(dx_list, key=lambda d: d.get("confidence", 0))
        primary_dx = primary.get("name", "")

    result = ClinicalSummaryV2Response(
        case_id=case_id,
        session_id=session_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        hpi=ClinicalNarrativeSection(
            **parsed.get("hpi", {"content": "", "content_vi": ""})
        ),
        chief_complaint=ClinicalNarrativeSection(
            **parsed.get("chief_complaint", {"content": "", "content_vi": ""})
        ),
        ros=ClinicalNarrativeSection(
            **parsed.get("ros", {"content": "", "content_vi": ""})
        ),
        severity=state.get("severity", "") or "",
        primary_diagnosis=primary_dx,
        is_emergency=state.get("is_emergency", False),
        needs_human_review=state.get("needs_human_review", False),
        human_review_reason=state.get("human_review_reason"),
        red_flags=red_flags,
        data_quality_notes=parsed.get("data_quality_notes", []),
        detected_language=state.get("detected_language", "vi"),
    )

    logger.info(
        "clinical_summary_v2.generated",
        case_id=case_id,
        session_id=session_id,
        severity=result.severity,
    )

    return result
