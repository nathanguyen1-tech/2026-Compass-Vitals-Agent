"""Intake Agent V2 — Trust the LLM, verify output.

V2 philosophy: GPT-4 already knows how to conduct a clinical interview.
Instead of 21 override layers, we:
  1. Check instant emergency keywords (unconscious, seizure, suicide, OD)
  2. Let LLM drive the conversation freely
  3. Extract structured data from markers

V1 is preserved in intake_agent.py for comparison.
"""

import re
from datetime import datetime, timezone

import structlog
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.prompts.intake_prompt_v2 import INTAKE_V2_SYSTEM_PROMPT
from app.agents.state import CareFlowState
from app.agents.tools.emergency_detector import detect_instant_emergency
from app.agents.tools.intake_tracker import (
    INTAKE_MARKER_PATTERN,
    IntakeTracker,
    parse_intake_markers,
)
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier
from app.nlp.code_switcher import CodeSwitcher
from app.nlp.cultural_mapper import CulturalMapper

logger = structlog.get_logger()

code_switcher = CodeSwitcher()
cultural_mapper = CulturalMapper()

# Pattern for V2 emergency marker: [EMERGENCY:reason]
EMERGENCY_MARKER_PATTERN = re.compile(r"\[EMERGENCY:([^\]]+)\]")


async def intake_node_v2(
    state: CareFlowState,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> dict:
    """V2 Intake Agent — trust the LLM, verify output.

    Compared to V1 (intake_node):
    - No broad keyword detection, no conversation-context scan
    - No safety classifier, no clinical scoring during intake
    - No phase enforcement, no screening question gate
    - Single static prompt instead of compose_intake_prompt()
    - Only instant emergency keywords as pre-LLM safety net
    """
    messages = state.get("messages", [])
    case_id = state.get("case_id", "unknown")

    # === No messages yet → initial greeting ===
    if not messages:
        return _initial_greeting_v2(state)

    last_message = messages[-1]
    patient_text = (
        last_message.content if hasattr(last_message, "content") else str(last_message)
    )

    # === Step 1: Prompt injection protection ===
    clean_text = INTAKE_MARKER_PATTERN.sub("", patient_text).strip()
    emergency_stripped = EMERGENCY_MARKER_PATTERN.sub("", clean_text).strip()
    if emergency_stripped != patient_text:
        logger.warning("intake_v2.marker_injection_stripped", case_id=case_id)
        patient_text = emergency_stripped

    # === Step 2: Instant emergency check (only life-threatening keywords) ===
    # "bất tỉnh", "co giật", "tự tử", "OD", "gunshot" etc. — can't wait for LLM
    if detect_instant_emergency(patient_text):
        logger.warning("intake_v2.instant_emergency", case_id=case_id)
        return _emergency_response_v2(state)

    # === Step 3: NLP pipeline ===
    detected_language = code_switcher.detect_language(patient_text)
    cultural_expressions = cultural_mapper.map_expressions(patient_text)

    # === Step 4: PHI de-identification ===
    deidentified_text, phi_mapping = phi_deidentifier.deidentify(patient_text)

    # === Step 5: Build messages for LLM — single static prompt ===
    cultural_context = ""
    if cultural_expressions:
        expr_info = "; ".join(
            f"'{e['original']}' \u2192 {e['medical_meaning']}" for e in cultural_expressions
        )
        cultural_context = f"\n\nCULTURAL CONTEXT DETECTED: {expr_info}"

    current_year = datetime.now(timezone.utc).year
    year_context = (
        f"\n\nCURRENT YEAR: {current_year}. "
        f"When a patient states their birth year (e.g., 'sinh năm 1958'), "
        f"calculate age as {current_year} minus birth year. "
        f"Do NOT use any other year for this calculation."
    )
    llm_messages = [
        {"role": "system", "content": INTAKE_V2_SYSTEM_PROMPT + cultural_context + year_context},
    ]

    # Add full conversation history (de-identified, markers stripped from user msgs)
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(msg, HumanMessage):
            # Strip any injected markers from user messages before sending to LLM
            content = INTAKE_MARKER_PATTERN.sub("", content)
            content = EMERGENCY_MARKER_PATTERN.sub("", content).strip()
        deidentified_content, _ = phi_deidentifier.deidentify(content)
        if isinstance(msg, HumanMessage):
            llm_messages.append({"role": "user", "content": deidentified_content})
        elif isinstance(msg, AIMessage):
            llm_messages.append({"role": "assistant", "content": deidentified_content})

    # === Step 6: Call LLM — no overrides, no second-guessing ===
    response = await llm_gateway.generate(
        messages=llm_messages,
        agent_type="intake_v2",
        case_id=case_id,
        temperature=0.3,
    )

    ai_response_text = response.content

    # Re-identify if needed
    if phi_mapping:
        ai_response_text = phi_deidentifier.reidentify(ai_response_text, phi_mapping)

    # === Step 7: Extract markers ===
    # Check for [EMERGENCY:reason] BEFORE stripping markers
    emergency_match = EMERGENCY_MARKER_PATTERN.search(ai_response_text)
    is_emergency = emergency_match is not None
    emergency_reason = emergency_match.group(1) if emergency_match else None

    # Strip [EMERGENCY:...] from visible text
    ai_response_text = EMERGENCY_MARKER_PATTERN.sub("", ai_response_text)

    # Parse [INTAKE:field=value] markers
    ai_response_text, extracted_fields = parse_intake_markers(ai_response_text)

    if is_emergency:
        logger.warning(
            "intake_v2.llm_emergency",
            case_id=case_id,
            reason=emergency_reason,
        )

    # === Step 8: Update tracker (soft — no enforcement) ===
    tracker = IntakeTracker(
        data=state.get("intake_tracker"),
        existing_history=state.get("existing_history"),
    )
    tracker.message_count += 1

    for field, value in extracted_fields.items():
        tracker.update_field(field, value)

    # === Step 9: Return ===
    intake_data = tracker.to_intake_data()

    return {
        "messages": [AIMessage(content=ai_response_text)],
        "detected_language": detected_language,
        "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
        "is_emergency": is_emergency,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "intake_tracker": tracker.to_dict(),
        "intake_data": intake_data if intake_data else None,
        "intake_complete": tracker.phase == "complete",
    }


def _initial_greeting_v2(state: CareFlowState) -> dict:
    """Return initial greeting — asks demographics + chief complaint naturally."""
    tracker = IntakeTracker(existing_history=state.get("existing_history"))
    tracker.phase = "greeting"
    return {
        "messages": [
            AIMessage(
                content="Xin ch\u00e0o! T\u00f4i l\u00e0 b\u00e1c s\u0129 tr\u1ef1c tuy\u1ebfn c\u1ee7a Compass Vitals. "
                "Cu\u1ed9c tr\u00f2 chuy\u1ec7n s\u1ebd m\u1ea5t t\u1ed1i \u0111a 15 ph\u00fat.\n\n"
                "Xin cho bi\u1ebft tu\u1ed5i v\u00e0 gi\u1edbi t\u00ednh c\u1ee7a b\u1ea1n, "
                "v\u00e0 h\u00f4m nay b\u1ea1n c\u1ea7n kh\u00e1m g\u00ec \u1ea1?"
            )
        ],
        "detected_language": "vi",
        "is_emergency": False,
        "intake_tracker": tracker.to_dict(),
    }


def _emergency_response_v2(state: CareFlowState) -> dict:
    """Return emergency alert for instant keywords."""
    tracker = IntakeTracker(
        data=state.get("intake_tracker"),
        existing_history=state.get("existing_history"),
    )

    emergency_content = (
        "\u26a0\ufe0f C\u1ea2NH B\u00c1O KH\u1ea8N C\u1ea4P:\n\n"
        "D\u1ef1a tr\u00ean nh\u1eefng g\u00ec b\u1ea1n m\u00f4 t\u1ea3, ch\u00fang t\u00f4i nh\u1eadn th\u1ea5y c\u00e1c tri\u1ec7u ch\u1ee9ng "
        "c\u1ea7n \u0111\u01b0\u1ee3c \u0111\u00e1nh gi\u00e1 y t\u1ebf NGAY L\u1eacP T\u1ee8C.\n\n"
        "\u26a0\ufe0f EMERGENCY ALERT:\n\n"
        "Based on your symptoms, you need IMMEDIATE medical evaluation.\n\n"
        "\U0001F4DE G\u1ecdi 115 (Vi\u1ec7t Nam) ho\u1eb7c 911 (M\u1ef9) NGAY\n"
        "\U0001F4DE Call 115 (Vietnam) or 911 (US) NOW\n\n"
        "\U0001F3E5 Ho\u1eb7c \u0111\u1ebfn ph\u00f2ng c\u1ea5p c\u1ee9u g\u1ea7n nh\u1ea5t\n"
        "\U0001F3E5 Or go to the nearest emergency room"
    )

    return {
        "messages": [AIMessage(content=emergency_content)],
        "detected_language": state.get("detected_language", "vi"),
        "cultural_expressions": state.get("cultural_expressions", []),
        "is_emergency": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "intake_tracker": tracker.to_dict(),
        "intake_data": tracker.to_intake_data(),
        "intake_complete": False,
    }
