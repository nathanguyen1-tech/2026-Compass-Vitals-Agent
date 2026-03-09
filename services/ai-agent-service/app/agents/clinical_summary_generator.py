"""Clinical Summary Generator — Structured HPI, CC, and ROS for MD review.

Pure Python data transformation (like care_plan_generator.py).
Extracts from intake_data, intake_tracker, screening_result, and messages
to produce a ClinicalSummaryResponse for physician display.

Data priority: intake_tracker > intake_data > screening_result > messages
"""

from datetime import datetime, timezone

from app.agents.state import CareFlowState
from app.agents.tools.intake_tracker import IntakeTracker
from app.api.v1.schemas.flow import (
    ChiefComplaintSection,
    ClinicalSummaryResponse,
    DiagnosisItem,
    HPISection,
    OLDCARTSDetail,
    ROSSystem,
    ScreeningFinding,
)


# Vietnamese system name translations
_ROS_SYSTEM_VI = {
    "constitutional": "Toan than",
    "cardiovascular": "Tim mach",
    "respiratory": "Ho hap",
    "gastrointestinal": "Tieu hoa",
    "genitourinary": "Tiet nieu - sinh duc",
    "musculoskeletal": "Co xuong khop",
    "neurological": "Than kinh",
    "psychiatric": "Tam than",
    "skin": "Da lieu",
    "endocrine": "Noi tiet",
    "hematologic": "Huyet hoc",
    "ent": "Tai Mui Hong",
    "eyes": "Mat",
    "allergic_immunologic": "Di ung - Mien dich",
}


def generate_clinical_summary(
    state: CareFlowState, session_id: str
) -> ClinicalSummaryResponse:
    """Compile intake data into a structured Clinical Summary for MD review.

    Uses multiple data sources with fallback priority:
    intake_tracker > intake_data > screening_result > conversation messages
    """

    intake_data = state.get("intake_data") or {}
    tracker_data = state.get("intake_tracker")
    screening = state.get("screening_result") or {}

    # Reconstruct IntakeTracker if serialized dict is available
    tracker = IntakeTracker(data=tracker_data) if tracker_data else None

    # Extract conversation text for fallback context
    conversation_text = _extract_conversation_text(state.get("messages", []))

    # === Chief Complaint ===
    cc_text = ""
    if tracker and tracker.cc:
        cc_text = tracker.cc
    elif intake_data.get("chief_complaint"):
        cc_text = intake_data["chief_complaint"]
    elif screening.get("clinical_impression"):
        cc_text = screening["clinical_impression"]
    elif conversation_text:
        # Use first patient message as fallback CC
        cc_text = _extract_first_patient_message(state.get("messages", []))

    oldcarts = _build_oldcarts(intake_data, tracker)

    chief_complaint = ChiefComplaintSection(
        complaint=cc_text,
        oldcarts=oldcarts,
        onset_description=_build_onset_narrative(oldcarts),
    )

    # === HPI ===
    hpi = _build_hpi(intake_data, tracker)

    # === ROS ===
    ros = _build_ros(intake_data, tracker)

    # === Red Flags (from tracker, intake_data, or screening) ===
    red_flags: list[str] = []
    if tracker and tracker.red_flags_found:
        red_flags = list(tracker.red_flags_found)
    elif intake_data.get("red_flags_found"):
        red_flags = list(intake_data["red_flags_found"])
    elif screening.get("red_flags"):
        red_flags = list(screening["red_flags"])

    # === Screening Key Findings (supplement ROS/HPI if sparse) ===
    key_findings = screening.get("key_findings", [])
    if key_findings and not ros:
        # Add screening findings as a pseudo-ROS "clinical_findings" system
        ros.append(
            ROSSystem(
                system_name="clinical_findings",
                system_name_vi="Phat hien lam sang",
                positives=key_findings,
            )
        )

    # === Cultural Expressions ===
    cultural = state.get("cultural_expressions", [])

    # === Screening enrichment ===
    screening_finding = None
    if screening:
        screening_finding = ScreeningFinding(
            clinical_impression=screening.get("clinical_impression", ""),
            key_findings=screening.get("key_findings", []),
            severity=screening.get("severity", ""),
            recommended_urgency=screening.get("recommended_urgency", ""),
        )

    # === Differential Diagnoses ===
    differentials = []
    for dx in state.get("differential_diagnoses", []):
        differentials.append(
            DiagnosisItem(
                name=dx.get("name", ""),
                name_vi=dx.get("name_vi", ""),
                confidence=dx.get("confidence", 0),
                reasoning=dx.get("reasoning", ""),
            )
        )

    # === Conversation summary (first 3 patient messages) ===
    conv_summary = _build_conversation_summary(state.get("messages", []))

    return ClinicalSummaryResponse(
        case_id=state.get("case_id", "unknown"),
        session_id=session_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        detected_language=state.get("detected_language", "vi"),
        chief_complaint=chief_complaint,
        hpi=hpi,
        ros=ros,
        cultural_expressions=cultural if cultural else [],
        is_emergency=state.get("is_emergency", False),
        red_flags=red_flags,
        screening=screening_finding,
        differential_diagnoses=differentials,
        severity=state.get("severity", ""),
        conversation_summary=conv_summary,
    )


def _extract_conversation_text(messages: list) -> str:
    """Extract all patient messages as a single text block."""
    parts = []
    for msg in messages:
        if hasattr(msg, "type") and msg.type == "human":
            content = msg.content if hasattr(msg, "content") else str(msg)
            parts.append(content)
        elif isinstance(msg, dict) and msg.get("type") == "human":
            parts.append(msg.get("content", ""))
    return " ".join(parts)


def _extract_first_patient_message(messages: list) -> str:
    """Extract the first patient (human) message as fallback chief complaint."""
    for msg in messages:
        if hasattr(msg, "type") and msg.type == "human":
            return msg.content if hasattr(msg, "content") else str(msg)
        elif isinstance(msg, dict) and msg.get("type") == "human":
            return msg.get("content", "")
    return ""


def _build_oldcarts(
    intake_data: dict, tracker: IntakeTracker | None
) -> OLDCARTSDetail:
    """Extract OLDCARTS fields from tracker or intake_data."""
    if tracker:
        hpi = tracker.hpi
        return OLDCARTSDetail(
            onset=hpi.get("onset") or "",
            location=hpi.get("location") or "",
            duration=hpi.get("duration") or "",
            character=hpi.get("character") or "",
            aggravating=hpi.get("aggravating") or "",
            alleviating=hpi.get("alleviating") or "",
            radiation=hpi.get("radiation") or "",
            timing=hpi.get("timing") or "",
            severity=hpi.get("severity") or "",
        )

    # Fallback: read directly from intake_data
    return OLDCARTSDetail(
        onset=intake_data.get("onset", ""),
        location=intake_data.get("location", ""),
        duration=intake_data.get("duration", ""),
        character=intake_data.get("character", ""),
        aggravating=intake_data.get("aggravating", ""),
        alleviating=intake_data.get("alleviating", ""),
        radiation=intake_data.get("radiation", ""),
        timing=intake_data.get("timing", ""),
        severity=intake_data.get("severity", ""),
    )


def _build_onset_narrative(oldcarts: OLDCARTSDetail) -> str:
    """Build a brief onset narrative from OLDCARTS data."""
    parts = []
    if oldcarts.onset:
        parts.append(f"Onset: {oldcarts.onset}")
    if oldcarts.duration:
        parts.append(f"Duration: {oldcarts.duration}")
    if oldcarts.character:
        parts.append(f"Character: {oldcarts.character}")
    if oldcarts.severity:
        parts.append(f"Severity: {oldcarts.severity}")
    return ". ".join(parts)


def _build_hpi(intake_data: dict, tracker: IntakeTracker | None) -> HPISection:
    """Build HPI section from tracker and intake_data."""
    pmh = ""
    meds = ""
    allergies = ""
    social = ""

    if tracker:
        pmh = tracker.pmh or ""
        meds = tracker.medications or ""
        allergies = tracker.allergies or ""
        social = tracker.social_family or ""
    else:
        pmh = intake_data.get("pmh", "")
        meds = intake_data.get("medications", "")
        allergies = intake_data.get("allergies", "")
        social = intake_data.get("social_family", "")

    return HPISection(
        past_medical_history=pmh,
        current_medications=meds,
        allergies=allergies,
        social_history=social,
    )


def _build_ros(
    intake_data: dict, tracker: IntakeTracker | None
) -> list[ROSSystem]:
    """Build full ROS with positives, pertinent negatives, and past episodes."""
    ros_data: dict[str, str] = {}

    if tracker and tracker.ros_systems:
        ros_data = tracker.ros_systems
    elif intake_data.get("ros") and isinstance(intake_data["ros"], dict):
        ros_data = intake_data["ros"]

    ros_list: list[ROSSystem] = []
    for system_name, finding in ros_data.items():
        positives, negatives, past_episodes = _parse_ros_finding(finding)
        ros_list.append(
            ROSSystem(
                system_name=system_name,
                system_name_vi=_ROS_SYSTEM_VI.get(system_name, ""),
                positives=positives,
                pertinent_negatives=negatives,
                past_similar_episodes=past_episodes,
            )
        )

    return ros_list


def _parse_ros_finding(finding: str) -> tuple[list[str], list[str], str]:
    """Parse a ROS finding string into positives, negatives, and past episodes.

    Handles formats like:
    - "positive: cough, fever; negative: chest pain; past: had similar 2 years ago"
    - Simple text (treated as positive)
    """
    positives: list[str] = []
    negatives: list[str] = []
    past_episodes = ""

    finding_lower = finding.lower()

    # Try structured format first
    if "positive:" in finding_lower or "negative:" in finding_lower:
        parts = finding.split(";")
        for part in parts:
            part_stripped = part.strip()
            part_lower = part_stripped.lower()
            if part_lower.startswith("positive:"):
                items = part_stripped[len("positive:"):].strip()
                positives = [i.strip() for i in items.split(",") if i.strip()]
            elif part_lower.startswith("negative:"):
                items = part_stripped[len("negative:"):].strip()
                negatives = [i.strip() for i in items.split(",") if i.strip()]
            elif part_lower.startswith("past:"):
                past_episodes = part_stripped[len("past:"):].strip()
    else:
        # Simple finding — treat as positive
        if finding.strip():
            positives = [finding.strip()]

    return positives, negatives, past_episodes


def _build_conversation_summary(messages: list, max_messages: int = 5) -> str:
    """Build a brief summary of the patient conversation for MD context.

    Extracts patient messages (up to max_messages) to give the MD
    a quick read of what the patient actually said.
    """
    patient_msgs = []
    for msg in messages:
        content = ""
        if hasattr(msg, "type") and msg.type == "human":
            content = msg.content if hasattr(msg, "content") else str(msg)
        elif isinstance(msg, dict) and msg.get("type") == "human":
            content = msg.get("content", "")
        if content:
            patient_msgs.append(content)
        if len(patient_msgs) >= max_messages:
            break

    if not patient_msgs:
        return ""

    return " | ".join(patient_msgs)
