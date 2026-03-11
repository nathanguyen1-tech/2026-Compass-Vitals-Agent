"""Intake Agent — Thu thap trieu chung qua conversational interview.

Thay the vai tro Y ta triage (RN). FR9: Symptom Intake with Contextual Follow-up.

Enhanced with:
- Complaint-specific protocols (11 clinical protocols)
- Intake progress tracking (OLDCARTS, ROS, PMH, etc.)
- Contextual red flag detection
- Dynamic prompt composition
- Structured data extraction via [INTAKE:field=value] markers
"""

from datetime import datetime, timezone

import structlog
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.prompts.complaint_protocols import (
    classify_chief_complaint,
    get_complaint_protocol,
    get_relevant_oldcarts,
)
from app.agents.prompts.intake_prompt import compose_intake_prompt
from app.agents.state import CareFlowState
from app.agents.tools.emergency_detector import (
    detect_contextual_red_flags,
    detect_high_temperature,
    detect_instant_emergency,
    get_emergency_keywords_found,
)
from app.agents.tools.intake_tracker import IntakeTracker, parse_intake_markers
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier
from app.nlp.code_switcher import CodeSwitcher
from app.nlp.cultural_mapper import CulturalMapper

logger = structlog.get_logger()

code_switcher = CodeSwitcher()
cultural_mapper = CulturalMapper()


async def intake_node(
    state: CareFlowState,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> dict:
    """Intake Agent LangGraph node function.

    Reads messages from state, processes through NLP pipeline,
    calls LLM via gateway, returns updated state fields.
    """
    messages = state.get("messages", [])
    case_id = state.get("case_id", "unknown")

    if not messages:
        return _initial_greeting(state)

    # Get latest patient message
    last_message = messages[-1]
    patient_text = (
        last_message.content if hasattr(last_message, "content") else str(last_message)
    )

    # === Load or create tracker ===
    tracker = IntakeTracker(
        data=state.get("intake_tracker"),
        existing_history=state.get("existing_history"),
    )
    tracker.message_count += 1

    # === Step 1a: INSTANT Emergency Detection (small keyword set + vital signs) ===
    # Only life-threatening conditions: unconscious, seizure, suicide, hemorrhage, overdose, ≥40°C
    is_instant_emergency = detect_instant_emergency(patient_text)
    if is_instant_emergency:
        emergency_keywords = get_emergency_keywords_found(patient_text)
        logger.warning(
            "emergency.instant",
            case_id=case_id,
            keywords=emergency_keywords,
        )

        # Check if this is a temperature emergency for specific messaging
        temp_info = detect_high_temperature(patient_text)
        if temp_info:
            emergency_content = (
                "\u26a0\ufe0f C\u1ea2NH B\u00c1O KH\u1ea8N C\u1ea4P: "
                f"Nhi\u1ec7t \u0111\u1ed9 {temp_info['value']}\u00b0{temp_info['unit']} "
                "l\u00e0 r\u1ea5t nguy hi\u1ec3m (s\u1ed1t cao \u0111\u1ed9 IV / hyperpyrexia). "
                "\u0110\u00e2y l\u00e0 t\u00ecnh tr\u1ea1ng \u0111e d\u1ecda t\u00ednh m\u1ea1ng c\u1ea7n \u0111\u01b0\u1ee3c c\u1ea5p c\u1ee9u ngay.\n\n"
                "Vui l\u00f2ng g\u1ecdi 911 ho\u1eb7c \u0111\u1ebfn ph\u00f2ng c\u1ea5p c\u1ee9u g\u1ea7n nh\u1ea5t ngay l\u1eadp t\u1ee9c.\n\n"
                "\u26a0\ufe0f EMERGENCY: "
                f"Temperature {temp_info['value']}\u00b0{temp_info['unit']} "
                "is extremely dangerous (Grade IV fever / hyperpyrexia). "
                "This is a life-threatening condition requiring immediate emergency care. "
                "Please call 911 or go to the nearest ER immediately."
            )
        else:
            emergency_content = (
                "\u26a0\ufe0f C\u1ea2NH B\u00c1O KH\u1ea8N C\u1ea4P: "
                "Tri\u1ec7u ch\u1ee9ng b\u1ea1n m\u00f4 t\u1ea3 c\u1ea7n \u0111\u01b0\u1ee3c x\u1eed l\u00fd ngay l\u1eadp t\u1ee9c. "
                "Vui l\u00f2ng g\u1ecdi 911 ho\u1eb7c \u0111\u1ebfn ph\u00f2ng c\u1ea5p c\u1ee9u g\u1ea7n nh\u1ea5t ngay. "
                "\u0110\u1eebng ch\u1edd \u0111\u1ee3i \u2014 s\u1ee9c kh\u1ecfe c\u1ee7a b\u1ea1n l\u00e0 \u01b0u ti\u00ean h\u00e0ng \u0111\u1ea7u."
            )

        return {
            "is_emergency": True,
            "messages": [AIMessage(content=emergency_content)],
            "intake_tracker": tracker.to_dict(),
        }

    # === Step 1b: Suspected emergency — increment confirmation counter ===
    if tracker.suspected_emergency is not None:
        tracker.suspected_emergency["confirmation_questions_asked"] += 1
        asked = tracker.suspected_emergency["confirmation_questions_asked"]
        logger.info(
            "emergency.confirmation_turn",
            case_id=case_id,
            asked=asked,
            reason=tracker.suspected_emergency["reason"],
        )

    # === Step 1c: Contextual red flag detection ===
    # During red_flag_screening: only check current message (no history)
    # to avoid false positives from the LLM's own screening questions.
    # Other phases: check current message normally (history is optional).
    if tracker.complaint_category:
        if tracker.phase == "red_flag_screening":
            contextual_flags = detect_contextual_red_flags(
                patient_text,
                tracker.complaint_category,
                conversation_history=None,
            )
        else:
            contextual_flags = detect_contextual_red_flags(
                patient_text,
                tracker.complaint_category,
            )
        if contextual_flags:
            flag = contextual_flags[0]  # Most severe
            if flag["action"] == "911":
                logger.warning(
                    "emergency.contextual_red_flag",
                    case_id=case_id,
                    flag_id=flag["id"],
                    keywords=flag["keywords_found"],
                )
                return _contextual_emergency_response(flag, tracker, case_id)

    # === Step 2: NLP Pipeline ===
    detected_language = code_switcher.detect_language(patient_text)
    cultural_expressions = cultural_mapper.map_expressions(patient_text)
    normalized_text = code_switcher.normalize(patient_text)

    # === Step 3: PHI De-identification ===
    deidentified_text, phi_mapping = phi_deidentifier.deidentify(normalized_text)

    # === Step 3.5: Classify complaint if in early phase ===
    if tracker.phase in ("greeting", "cc") and not tracker.complaint_category:
        complaint_category = classify_chief_complaint(patient_text)
        if complaint_category != "general":
            tracker.complaint_category = complaint_category
            tracker.cc = patient_text
            protocol = get_complaint_protocol(complaint_category)
            tracker.set_relevant_oldcarts(get_relevant_oldcarts(protocol))
            if protocol.get("priority_order") == "red_flags_first":
                tracker.phase = "red_flag_screening"
            else:
                tracker.phase = "red_flag_screening"
        else:
            tracker.cc = patient_text
            tracker.phase = "hpi"

    # === Step 4: Build LLM messages ===
    # Get active complaint protocol
    protocol = get_complaint_protocol(tracker.complaint_category)

    # Build cultural context
    cultural_context = ""
    if cultural_expressions:
        expr_info = "; ".join(
            f"'{e['original']}' \u2192 {e['medical_meaning']}" for e in cultural_expressions
        )
        cultural_context = f"\n\nCULTURAL CONTEXT DETECTED: {expr_info}"

    # Compose dynamic prompt
    system_prompt = compose_intake_prompt(
        tracker=tracker,
        complaint_protocol=protocol,
        detected_language=detected_language,
        message_count=len(messages),
        existing_history=state.get("existing_history"),
    )

    llm_messages = [
        {"role": "system", "content": system_prompt + cultural_context},
    ]

    # Add conversation history (de-identified)
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else str(msg)
        deidentified_content, _ = phi_deidentifier.deidentify(content)
        if isinstance(msg, HumanMessage):
            llm_messages.append({"role": "user", "content": deidentified_content})
        elif isinstance(msg, AIMessage):
            llm_messages.append({"role": "assistant", "content": deidentified_content})

    # === Step 5: Call LLM via Gateway ===
    response = await llm_gateway.generate(
        messages=llm_messages,
        agent_type="intake",
        case_id=case_id,
        temperature=0.3,
    )

    # === Step 6: Re-identify response if needed ===
    ai_response_text = response.content
    if phi_mapping:
        ai_response_text = phi_deidentifier.reidentify(ai_response_text, phi_mapping)

    # === Step 6.5: Parse intake markers from response ===
    ai_response_text, extracted_fields = parse_intake_markers(ai_response_text)
    for field, value in extracted_fields.items():
        tracker.update_field(field, value)

    # === Step 6.55: LLM emergency marker handling ===

    # Handle emergency_suspected: LLM just detected something suspicious
    if "emergency_suspected" in extracted_fields:
        reason = extracted_fields["emergency_suspected"]
        logger.info(
            "emergency.suspected",
            case_id=case_id,
            reason=reason,
        )
        # tracker.update_field already set suspected_emergency via marker parsing above
        # LLM response already contains the first confirmation question
        # Return normal (NOT emergency) — let the conversation continue
        return {
            "messages": [AIMessage(content=ai_response_text)],
            "detected_language": detected_language,
            "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
            "is_emergency": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "intake_tracker": tracker.to_dict(),
            "intake_data": tracker.to_intake_data() if tracker.to_intake_data() else None,
            "intake_complete": False,
        }

    # Handle emergency_confirmed: LLM confirmed after 2+ questions
    if "emergency_confirmed" in extracted_fields:
        llm_emergency_reason = extracted_fields["emergency_confirmed"]
        asked = (
            tracker.suspected_emergency.get("confirmation_questions_asked", 0)
            if tracker.suspected_emergency
            else 0
        )
        # Only escalate if at least 2 confirmation questions were asked
        if asked >= 2:
            logger.warning(
                "emergency.confirmed",
                case_id=case_id,
                reason=llm_emergency_reason,
                questions_asked=asked,
            )
            tracker.suspected_emergency = None  # Clear the investigation
            return _llm_emergency_response(tracker, detected_language, cultural_expressions, state)
        else:
            # Not enough questions yet — keep investigating
            logger.info(
                "emergency.confirmed_too_early",
                case_id=case_id,
                reason=llm_emergency_reason,
                questions_asked=asked,
            )
            # Keep suspected_emergency active, return LLM response (which has a question)
            return {
                "messages": [AIMessage(content=ai_response_text)],
                "detected_language": detected_language,
                "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
                "is_emergency": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "intake_tracker": tracker.to_dict(),
                "intake_data": tracker.to_intake_data() if tracker.to_intake_data() else None,
                "intake_complete": False,
            }

    # Handle emergency_cleared: LLM determined it's not an emergency
    if "emergency_cleared" in extracted_fields:
        logger.info(
            "emergency.cleared",
            case_id=case_id,
            reason=extracted_fields["emergency_cleared"],
        )
        # tracker.update_field already cleared suspected_emergency
        # Continue with normal intake flow below

    # Handle legacy emergency_detected marker (backward compat) — treat as suspected
    if "emergency_detected" in extracted_fields:
        reason = extracted_fields["emergency_detected"]
        logger.info(
            "emergency.detected_legacy_as_suspected",
            case_id=case_id,
            reason=reason,
        )
        # Treat like emergency_suspected: set tracker and continue
        tracker.suspected_emergency = {
            "reason": reason,
            "confirmation_questions_asked": 0,
            "source": "llm",
        }
        return {
            "messages": [AIMessage(content=ai_response_text)],
            "detected_language": detected_language,
            "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
            "is_emergency": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "intake_tracker": tracker.to_dict(),
            "intake_data": tracker.to_intake_data() if tracker.to_intake_data() else None,
            "intake_complete": False,
        }

    # === Step 6.56: Safety fallback — force escalate if too many turns without decision ===
    if (
        tracker.suspected_emergency is not None
        and tracker.suspected_emergency.get("confirmation_questions_asked", 0) >= 3
    ):
        logger.warning(
            "emergency.safety_fallback",
            case_id=case_id,
            reason=tracker.suspected_emergency.get("reason"),
            questions_asked=tracker.suspected_emergency["confirmation_questions_asked"],
        )
        tracker.suspected_emergency = None
        return _llm_emergency_response(tracker, detected_language, cultural_expressions, state)

    # === Step 6.6: Auto-advance phase based on tracker state ===
    if tracker.is_minimum_complete() and tracker.phase not in ("summary", "complete"):
        tracker.phase = "summary"
    elif tracker.phase == "hpi":
        filled, _ = tracker.get_hpi_coverage()
        if filled >= tracker.get_min_oldcarts_required() and len(tracker.ros_systems) < 2:
            tracker.phase = "ros"
    elif tracker.phase == "ros" and len(tracker.ros_systems) >= 2:
        # Check what history sections still need collection
        next_phase = tracker.suggest_next_phase()
        if next_phase in ("pmh", "medications", "allergies", "social_family"):
            tracker.phase = next_phase
        elif next_phase == "summary":
            tracker.phase = "summary"

    # === Step 7: Return updated state ===
    intake_data = tracker.to_intake_data()

    return {
        "messages": [AIMessage(content=ai_response_text)],
        "detected_language": detected_language,
        "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
        "is_emergency": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "intake_tracker": tracker.to_dict(),
        "intake_data": intake_data if intake_data else None,
        "intake_complete": tracker.phase == "complete",
    }


def _initial_greeting(state: CareFlowState) -> dict:
    """Return initial greeting when no messages yet."""
    tracker = IntakeTracker(existing_history=state.get("existing_history"))
    tracker.phase = "greeting"
    return {
        "messages": [
            AIMessage(
                content="Xin ch\u00e0o! T\u00f4i l\u00e0 tr\u1ee3 l\u00fd y t\u1ebf AI c\u1ee7a Compass Vitals. "
                "T\u00f4i s\u1ebd h\u1ecfi b\u1ea1n m\u1ed9t s\u1ed1 c\u00e2u h\u1ecfi v\u1ec1 s\u1ee9c kh\u1ecfe \u0111\u1ec3 chu\u1ea9n b\u1ecb cho b\u00e1c s\u0129. "
                "Cu\u1ed9c tr\u00f2 chuy\u1ec7n s\u1ebd m\u1ea5t t\u1ed1i \u0111a 15 ph\u00fat.\n\n"
                "H\u00f4m nay b\u1ea1n c\u1ea7n kh\u00e1m g\u00ec \u1ea1?"
            )
        ],
        "detected_language": "vi",
        "is_emergency": False,
        "intake_tracker": tracker.to_dict(),
    }


def _llm_emergency_response(
    tracker: IntakeTracker,
    detected_language: str,
    cultural_expressions: list,
    state: dict,
) -> dict:
    """Return emergency response after LLM confirmation flow completes."""
    emergency_content = (
        "\u26a0\ufe0f C\u1ea2NH B\u00c1O KH\u1ea8N C\u1ea4P:\n\n"
        "D\u1ef1a tr\u00ean nh\u1eefng g\u00ec b\u1ea1n m\u00f4 t\u1ea3, ch\u00fang t\u00f4i nh\u1eadn th\u1ea5y c\u00e1c tri\u1ec7u ch\u1ee9ng "
        "c\u1ea7n \u0111\u01b0\u1ee3c \u0111\u00e1nh gi\u00e1 y t\u1ebf NGAY L\u1eacP T\u1ee8C.\n\n"
        "Vui l\u00f2ng g\u1ecdi 911 ho\u1eb7c \u0111\u1ebfn ph\u00f2ng c\u1ea5p c\u1ee9u g\u1ea7n nh\u1ea5t ngay. "
        "\u0110\u1eebng ch\u1edd \u0111\u1ee3i \u2014 s\u1ee9c kh\u1ecfe c\u1ee7a b\u1ea1n l\u00e0 \u01b0u ti\u00ean h\u00e0ng \u0111\u1ea7u.\n\n"
        "\u26a0\ufe0f EMERGENCY ALERT:\n\n"
        "Based on what you've described, we've identified symptoms that "
        "require IMMEDIATE medical evaluation.\n\n"
        "Please call 911 or go to the nearest emergency room immediately. "
        "Do not wait \u2014 your health is the top priority."
    )
    return {
        "is_emergency": True,
        "messages": [AIMessage(content=emergency_content)],
        "intake_tracker": tracker.to_dict(),
        "intake_data": tracker.to_intake_data(),
        "detected_language": detected_language,
        "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _contextual_emergency_response(
    flag: dict,
    tracker: IntakeTracker,
    case_id: str,
) -> dict:
    """Return contextual emergency response with bilingual messaging."""
    # Build bilingual message
    message_vi = flag.get("message_vi", "")
    message_en = flag.get("message_en", "")

    if message_vi and message_en:
        content = f"\u26a0\ufe0f C\u1ea2NH B\u00c1O KH\u1ea8N C\u1ea4P:\n\n{message_vi}\n\n{message_en}"
    elif message_vi:
        content = f"\u26a0\ufe0f C\u1ea2NH B\u00c1O KH\u1ea8N C\u1ea4P: {message_vi}"
    else:
        content = f"\u26a0\ufe0f EMERGENCY ALERT: {message_en}"

    # Track red flag
    tracker.red_flags_found.append(flag["id"])

    return {
        "is_emergency": True,
        "messages": [AIMessage(content=content)],
        "intake_tracker": tracker.to_dict(),
        "intake_data": tracker.to_intake_data(),
    }
