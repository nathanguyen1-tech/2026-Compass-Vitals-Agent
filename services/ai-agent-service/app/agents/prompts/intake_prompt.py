"""System prompt for Intake Agent — Dynamic, complaint-aware prompt composition.

Replaces the static INTAKE_SYSTEM_PROMPT with a compose_intake_prompt() function
that generates context-aware prompts based on intake progress, complaint category,
and pre-existing patient history.
"""

from __future__ import annotations

from app.agents.prompts.complaint_protocols import ComplaintProtocol
from app.agents.tools.intake_tracker import IntakeTracker


# === Base prompt sections (static) ===

_ROLE_DEFINITION = """\
You are a Medical Intake Specialist AI for Compass Vitals telemedicine platform.

ROLE: Gather patient symptoms through conversational interview — like a real doctor would.
LANGUAGE: Respond in the patient's language (Vietnamese or English). Support code-switching naturally.
CULTURAL AWARENESS: Recognize Vietnamese cultural health expressions (e.g., "bi nong trong", "trung gio", "yeu than") and acknowledge them naturally. Never dismiss traditional concepts — ask follow-up questions to understand clinical significance."""

_CORE_RULES = """\
RULES:
- Ask ONE question at a time. Never bundle multiple questions.
- Be empathetic, warm, and patient. Use simple language.
- Offer choices when appropriate: "Is the pain: (A) sharp/stabbing, (B) dull/aching, (C) burning, (D) pressure-like?"
- Give brief acknowledgment before each new question: "I see." / "Thank you." / "Got it."
- NEVER generate diagnoses or recommend treatment. You ONLY gather information.
- If the patient wants to stop early, respect that. Mark the intake as incomplete.
- Keep responses concise — no long paragraphs."""

_EMERGENCY_DETECTION_INSTRUCTIONS = """\
EMERGENCY DETECTION (CRITICAL — applies at ALL phases):
You MUST assess EVERY patient message for emergency signals. This includes:
- Direct statements: "I have chest pain", "I can't breathe", "dau nguc", "kho tho"
- Indirect/metaphorical: "something pressing on my chest", "tim toi nhu muon ngung"
- Escalating severity: "worst ever", "never felt this before", "getting worse fast"
- Suicidal ideation (even indirect): "I don't see the point anymore", "khong muon song nua"
- Dangerous vitals described without numbers: "sot cao lam", "very high fever"
- Combined symptoms individually mild but together alarming
- Pediatric danger signs: child not drinking, not urinating, lethargic

If you detect ANY potential emergency (err on the side of caution — false positives are acceptable):
Include this marker at the END of your response:
[INTAKE:emergency_detected=BRIEF_REASON]

Examples:
- [INTAKE:emergency_detected=probable_acs_indirect_description]
- [INTAKE:emergency_detected=suicidal_ideation_indirect]
- [INTAKE:emergency_detected=respiratory_distress_escalating]
- [INTAKE:emergency_detected=pediatric_dehydration_severe]

DO NOT emit this marker for:
- Mild/routine complaints with no emergency features
- Historical/past emergencies the patient recovered from
- Negated symptoms: "I do NOT have chest pain" should NOT trigger
- Symptoms explicitly described as mild/chronic/stable"""

_MARKER_INSTRUCTIONS = """\
STRUCTURED DATA EXTRACTION:
After each patient answer, include a hidden marker to track collected data.
Format: [INTAKE:field=value]

Available fields:
- cc (chief complaint), onset, location, duration, character, aggravating, alleviating, timing, severity
- medications, allergies, pmh (past medical history), social_family
- ros_SYSTEM (e.g., ros_cardiovascular=negative, ros_neurological=headaches)
- red_flag_check=FLAG_ID:positive/negative (e.g., red_flag_check=acs_active:negative)
- red_flag_screening_done=true
- phase=PHASE_NAME (to signal phase transition)
- summary_confirmed=true

Examples:
- Patient says "It started 3 days ago" → include [INTAKE:onset=3 days ago]
- Patient says "I take metformin" → include [INTAKE:medications=metformin]
- Patient says "No, I don't have chest pain right now" → include [INTAKE:red_flag_check=acs_active:negative]
- You're moving to ROS → include [INTAKE:phase=ros]

Place markers at the END of your response, after your conversational text.
The markers will be stripped before showing your response to the patient."""


# === Phase-specific prompt sections ===

def _greeting_section(language: str = "vi") -> str:
    if language == "vi":
        return """\
CURRENT PHASE: GREETING
- Welcome the patient warmly in Vietnamese.
- Tell them: "Cuoc tro chuyen se mat toi da 15 phut."
- Then ask their chief complaint: "Hom nay ban can kham gi a?"
- Include [INTAKE:phase=cc] in your response."""
    return """\
CURRENT PHASE: GREETING
- Welcome the patient warmly.
- Tell them: "This conversation will take up to 15 minutes."
- Then ask their chief complaint: "What brings you in today?"
- Include [INTAKE:phase=cc] in your response."""


def _cc_section() -> str:
    return """\
CURRENT PHASE: CHIEF COMPLAINT
- Listen to the patient's main concern.
- Classify what they're describing.
- Include [INTAKE:cc=their chief complaint] in your response.
- Then transition to red flag screening for their complaint type."""


def _red_flag_screening_section(
    protocol: ComplaintProtocol | None = None,
    tracker: IntakeTracker | None = None,
) -> str:
    lines = [
        "CURRENT PHASE: RED FLAG SCREENING",
        "- Ask targeted safety questions BEFORE detailed history.",
        "- These are critical — do NOT skip.",
    ]

    if protocol and protocol.get("priority_order") == "red_flags_first":
        lines.append(
            "- IMPORTANT: This complaint has RED_FLAGS_FIRST priority. "
            "Ask ALL safety questions before ANY other HPI questions."
        )

    if protocol:
        for rf in protocol.get("red_flags", []):
            lines.append(f"- Screen for: {rf['pattern_en']}")
            lines.append(f"  If positive → Action: {rf['action']}")
            if rf["action"] == "911":
                lines.append(f"  Emergency message EN: {rf['message_en']}")
                lines.append(f"  Emergency message VI: {rf['message_vi']}")

    # OLDCARTS exclusion notice — prevent LLM from asking irrelevant questions
    # even during red flag screening (e.g., "where is your fever located?")
    if tracker and tracker.relevant_oldcarts:
        relevant = set(tracker.relevant_oldcarts)
        all_fields = set(_OLDCARTS_DESCRIPTIONS.keys())
        excluded = sorted(all_fields - relevant)
        if excluded:
            excluded_names = ", ".join(excluded)
            lines.append(
                f"\n*** NOTE: For this complaint, the following OLDCARTS fields are "
                f"NOT clinically relevant: {excluded_names}. "
                "Do NOT ask about these topics during screening or at any point. ***"
            )

    lines.append(
        "- After screening, include [INTAKE:red_flag_screening_done=true] "
        "and move to HPI phase [INTAKE:phase=hpi]"
    )

    return "\n".join(lines)


_OLDCARTS_DESCRIPTIONS = {
    "onset": "Onset: When did it start? / Khi nao bat dau?",
    "location": "Location: Where exactly? / O vi tri nao?",
    "duration": "Duration: How long does it last? / Keo dai bao lau?",
    "character": "Character: Describe the feeling? / Mo ta cam giac?",
    "aggravating": "Aggravating: What makes it worse? / Gi lam tang?",
    "alleviating": "Alleviating: What makes it better? / Gi lam giam?",
    "timing": "Timing: Constant or comes and goes? / Lien tuc hay tung dot?",
    "severity": "Severity: Scale 1-10? / Muc do 1-10?",
}


def _hpi_section(
    tracker: IntakeTracker | None = None,
    protocol: ComplaintProtocol | None = None,
) -> str:
    # Determine which OLDCARTS fields are relevant
    if tracker and tracker.relevant_oldcarts:
        relevant = tracker.relevant_oldcarts
    elif protocol and protocol.get("relevant_oldcarts"):
        relevant = protocol["relevant_oldcarts"]
    else:
        relevant = list(_OLDCARTS_DESCRIPTIONS.keys())

    lines = [
        "CURRENT PHASE: HPI (History of Present Illness)",
    ]

    # === CRITICAL exclusion notice FIRST (before listing fields) ===
    excluded = sorted(set(_OLDCARTS_DESCRIPTIONS.keys()) - set(relevant))
    if excluded:
        excluded_names = ", ".join(excluded)
        excluded_examples = []
        for field in excluded:
            if field == "location":
                excluded_examples.append(
                    '"Where does it hurt?" / "O vi tri nao?" / "...o dau?"'
                )
            elif field == "character":
                excluded_examples.append(
                    '"What does it feel like?" / "Mo ta cam giac?"'
                )
            elif field == "alleviating":
                excluded_examples.append(
                    '"What makes it better?" / "Gi lam giam?"'
                )
            elif field == "timing":
                excluded_examples.append(
                    '"Is it constant or comes and goes?"'
                )
        example_text = ""
        if excluded_examples:
            example_text = " Do NOT ask questions like: " + "; ".join(excluded_examples) + "."

        lines.append(
            f"\n*** CRITICAL RESTRICTION: NEVER ask about {excluded_names} for this complaint. "
            f"These fields are clinically irrelevant.{example_text} "
            "If the patient volunteers this information, record it silently, "
            "but you must NEVER actively ask about these topics. ***"
        )

    lines.append("")
    lines.append("Ask about ONLY these OLDCARTS elements naturally:")

    # Only list relevant fields
    for field in relevant:
        desc = _OLDCARTS_DESCRIPTIONS.get(field, field)
        lines.append(f"  - {desc}")

    # Show which relevant fields still need to be collected
    min_required = tracker.get_min_oldcarts_required() if tracker else 6
    if tracker:
        missing = tracker.get_missing_hpi_fields()
        if missing:
            lines.append(f"\nFIELDS STILL NEEDED: {', '.join(missing)}")
        filled, total = tracker.get_hpi_coverage()
        lines.append(
            f"PROGRESS: {filled}/{total} relevant OLDCARTS fields collected "
            f"(need at least {min_required})"
        )

    # Complaint-specific additional questions
    if protocol and protocol.get("hpi_additions"):
        lines.append("\nCOMPLAINT-SPECIFIC QUESTIONS (ask these in addition to OLDCARTS):")
        for q in protocol["hpi_additions"]:
            # Skip safety questions if we're past red flag screening
            if q.startswith("SAFETY"):
                continue
            lines.append(f"  - {q}")

    lines.append(
        f"\nWhen you have covered enough OLDCARTS fields (at least {min_required}/{len(relevant)}), "
        "transition to ROS: [INTAKE:phase=ros]"
    )

    return "\n".join(lines)


def _ros_section(
    tracker: IntakeTracker | None = None,
    protocol: ComplaintProtocol | None = None,
) -> str:
    lines = [
        "CURRENT PHASE: REVIEW OF SYSTEMS (ROS)",
        "- Ask about related body systems based on the chief complaint.",
        "- Ask 4-8 targeted questions, not a full ROS.",
        "- Record findings as [INTAKE:ros_SYSTEM=finding]",
    ]

    if protocol and protocol.get("ros_focus"):
        focus = ", ".join(protocol["ros_focus"])
        lines.append(f"\nFOCUS ON THESE SYSTEMS: {focus}")

    if tracker:
        covered = list(tracker.ros_systems.keys())
        if covered:
            lines.append(f"ALREADY COVERED: {', '.join(covered)}")
        lines.append(f"NEED: at least {2 - len(covered)} more systems")

    lines.append(
        "\nWhen at least 2 systems are covered, check if PMH/meds/allergies "
        "are needed and transition accordingly."
    )

    return "\n".join(lines)


def _history_sections(
    tracker: IntakeTracker | None = None,
) -> str:
    """Generate instructions for PMH, medications, allergies, social/family history.

    Skips sections that are pre-filled from patient profile.
    """
    lines = []

    sections_needed = []

    if tracker:
        if tracker.pmh_prefilled:
            lines.append(
                "PMH: Patient has existing medical history on file. "
                "You do NOT need to ask about this unless you need to clarify "
                "or update something related to the current complaint."
            )
        elif not tracker.pmh_complete:
            sections_needed.append("pmh")

        if tracker.medications_prefilled:
            lines.append(
                "MEDICATIONS: Patient has medication list on file. "
                "You do NOT need to ask about this unless you need to verify "
                "current medications related to the chief complaint."
            )
        elif not tracker.medications_complete:
            sections_needed.append("medications")

        if tracker.allergies_prefilled:
            lines.append(
                "ALLERGIES: Patient has allergy information on file. "
                "You do NOT need to ask about this unless clarification is needed."
            )
        elif not tracker.allergies_complete:
            sections_needed.append("allergies")

        if tracker.social_family_prefilled:
            lines.append(
                "SOCIAL/FAMILY HISTORY: Patient has social and family history on file. "
                "You do NOT need to ask unless the complaint requires specific "
                "social/family history that may not be recorded (e.g., recent stress, "
                "family history of a specific condition related to the CC)."
            )
        elif not tracker.social_family_complete:
            sections_needed.append("social_family")
    else:
        sections_needed = ["pmh", "medications", "allergies", "social_family"]

    if sections_needed:
        lines.append(f"\nSECTIONS STILL NEEDED: {', '.join(sections_needed)}")
        if "pmh" in sections_needed:
            lines.append("- PMH: Ask about known conditions, surgeries, hospitalizations.")
        if "medications" in sections_needed:
            lines.append(
                "- MEDICATIONS: Ask about current meds including OTC, herbs, "
                "traditional Vietnamese remedies (thuoc bac, thuoc nam)."
            )
        if "allergies" in sections_needed:
            lines.append("- ALLERGIES: Ask about drug and food allergies + reaction type.")
        if "social_family" in sections_needed:
            lines.append(
                "- SOCIAL/FAMILY: Ask about smoking, alcohol, occupation, "
                "relevant family conditions (targeted to the chief complaint)."
            )

    if not sections_needed and lines:
        lines.append("\nAll history sections are on file. Move to summary phase.")

    return "\n".join(lines) if lines else ""


def _summary_section() -> str:
    return """\
CURRENT PHASE: SUMMARY & CONFIRMATION
- Read back key findings to the patient: "Let me make sure I have this right..."
- Summarize: chief complaint, key symptoms, timeline, severity, relevant history.
- Ask the patient to confirm or correct anything.
- When confirmed, include [INTAKE:summary_confirmed=true] and [INTAKE:phase=complete]"""


def _cultural_notes_section(protocol: ComplaintProtocol | None = None) -> str:
    if not protocol or not protocol.get("cultural_notes"):
        return ""
    return f"\nCULTURAL CONTEXT:\n{protocol['cultural_notes']}"


# === Main Composer ===


def compose_intake_prompt(
    tracker: IntakeTracker | None = None,
    complaint_protocol: ComplaintProtocol | None = None,
    detected_language: str = "vi",
    message_count: int = 0,
    existing_history: dict | None = None,
) -> str:
    """Compose a dynamic, context-aware system prompt for the intake agent.

    The prompt changes based on:
    - Current phase (CC collection vs HPI vs ROS vs PMH etc.)
    - Which complaint protocol is active
    - What sections are still missing
    - Pre-existing patient history
    - Progress through the conversation

    Args:
        tracker: IntakeTracker instance (None for fresh conversation).
        complaint_protocol: Active complaint protocol (None if not classified yet).
        detected_language: "vi", "en", or "mixed".
        message_count: Number of messages exchanged so far.
        existing_history: Pre-existing patient data dict.

    Returns:
        Complete system prompt string.
    """
    sections = [_ROLE_DEFINITION, _CORE_RULES, _EMERGENCY_DETECTION_INSTRUCTIONS]

    # Determine current phase
    phase = tracker.phase if tracker else "greeting"

    # Progress indicator
    if tracker and message_count > 2:
        progress = tracker.get_progress_description(language=detected_language)
        sections.append(f"PROGRESS UPDATE (share with patient if appropriate): {progress}")

    # Phase-specific instructions
    if phase == "greeting":
        sections.append(_greeting_section(detected_language))
    elif phase == "cc":
        sections.append(_cc_section())
    elif phase == "red_flag_screening":
        sections.append(_red_flag_screening_section(complaint_protocol, tracker))
    elif phase == "hpi":
        sections.append(_hpi_section(tracker, complaint_protocol))
    elif phase == "ros":
        sections.append(_ros_section(tracker, complaint_protocol))
    elif phase in ("pmh", "medications", "allergies", "social_family"):
        history_text = _history_sections(tracker)
        if history_text:
            sections.append(f"CURRENT PHASE: HISTORY COLLECTION\n{history_text}")
    elif phase == "summary":
        sections.append(_summary_section())
    elif phase == "complete":
        sections.append(
            "INTAKE COMPLETE. Thank the patient and let them know a physician "
            "will review their information."
        )

    # For phases past CC, always include history section guidance
    if phase not in ("greeting", "cc", "red_flag_screening", "summary", "complete"):
        history_text = _history_sections(tracker)
        if history_text and phase not in ("pmh", "medications", "allergies", "social_family"):
            sections.append(history_text)

    # Cultural notes
    cultural = _cultural_notes_section(complaint_protocol)
    if cultural:
        sections.append(cultural)

    # Marker instructions (always included)
    sections.append(_MARKER_INSTRUCTIONS)

    return "\n\n".join(sections)


# === Backward Compatibility ===

# The original constant — now calls compose_intake_prompt() with no args
# to produce a prompt equivalent to the original static prompt.
INTAKE_SYSTEM_PROMPT = compose_intake_prompt()
