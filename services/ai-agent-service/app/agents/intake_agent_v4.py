"""Intake Agent V4 — Single LLM "Senior Doctor" Architecture.

V4 philosophy:
  "One smart LLM with full context + code safety net"

Each patient turn:
  1. Code: instant emergency (keywords + vitals) — 0ms
  2. Code: extract facts from patient text
  3. Code: check red flag combos → emergency if triggered
  4. Code: build dynamic system prompt (base + mandatory injection + complaint-specific)
  5. LLM: single call — senior doctor responds naturally
  6. Code: parse output for [EMERGENCY] / [INTAKE_DONE] markers
  7. Code: validate completion gate before marking done

LLM role: HOW to ask, probe depth, naturalness, hypothesis reasoning
Code role: WHAT must be asked, safety gates, emergency detection, completion gate
"""

import re
from datetime import datetime, timezone

import structlog
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.intake_facts_extractor import (
    extract_facts_from_text,
    check_red_flag_combos,
    detect_complaint_category,
)
from app.agents.prompts.doctor_prompt_v4 import (
    DOCTOR_SYSTEM_PROMPT,
    COMPLAINT_PROBES,
    build_mandatory_injection,
)
from app.agents.state import CareFlowState
from app.agents.tools.emergency_detector import detect_instant_emergency
from app.agents.tools.intake_tracker import IntakeTracker, INTAKE_MARKER_PATTERN
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier
from app.nlp.code_switcher import CodeSwitcher
from app.nlp.cultural_mapper import CulturalMapper

logger = structlog.get_logger()

code_switcher = CodeSwitcher()
cultural_mapper = CulturalMapper()

_EMERGENCY_MARKER = re.compile(r'\[EMERGENCY\]', re.IGNORECASE)
_INTAKE_DONE_MARKER = re.compile(r'\[INTAKE_DONE\]', re.IGNORECASE)

# Minimum turns before allowing INTAKE_DONE (prevent premature completion)
MIN_TURNS_FOR_COMPLETION = 6

# Minimum required facts before INTAKE_DONE
COMPLETION_REQUIRED_ALWAYS = {
    "age", "gender", "cc", "onset", "location", "character", "severity",
    "pmh", "medications", "allergies",
}

COMPLETION_REQUIRED_BY_CATEGORY = {
    "abdominal_pain": {
        "fever", "nausea", "bowel", "urinary", "radiation",
        "meal_relation",   # đau liên quan bữa ăn / đi tiêu không
    },
    "chest_pain":     {"radiation", "dyspnea", "diaphoresis"},
    "headache":       {"fever", "worst_headache_ever"},
    "respiratory":    {"dyspnea", "fever"},
    "urinary":        {"fever", "urinary"},
    "general":        {"fever", "nausea"},
}


async def intake_node_v4(
    state: CareFlowState,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> dict:
    """V4 Intake Agent — Single LLM Senior Doctor."""

    messages = state.get("messages", [])
    case_id = state.get("case_id", "unknown")

    # === No messages → initial greeting ===
    if not messages:
        return _initial_greeting_v4(state)

    # === Already complete ===
    if state.get("intake_complete"):
        return {
            "messages": [AIMessage(content=(
                "Tôi đã ghi nhận đầy đủ thông tin. "
                "Bác sĩ sẽ xem xét và liên hệ với bạn sớm nhất có thể."
            ))],
            "detected_language": state.get("detected_language", "vi"),
            "is_emergency": False,
            "intake_complete": True,
            "intake_tracker": state.get("intake_tracker"),
            "intake_data": state.get("intake_data"),
            "confirmed_facts": state.get("confirmed_facts", {}),
        }

    # === Get patient message ===
    last_message = messages[-1]
    patient_text = last_message.content if hasattr(last_message, "content") else str(last_message)

    # === Step 1: Prompt injection protection ===
    clean_text = INTAKE_MARKER_PATTERN.sub("", patient_text).strip()
    clean_text = _EMERGENCY_MARKER.sub("", clean_text).strip()

    # === Step 2: Instant emergency (code, 0ms) ===
    if detect_instant_emergency(clean_text):
        logger.warning("intake_v4.instant_emergency", case_id=case_id)
        return _emergency_response_v4(state, trigger="instant_keyword")

    # === Step 3: NLP ===
    detected_language = code_switcher.detect_language(clean_text)
    cultural_expressions = cultural_mapper.map_expressions(clean_text)

    # === Step 4: PHI de-identification ===
    deidentified_text, phi_mapping = phi_deidentifier.deidentify(clean_text)

    # === Step 5: Code fact extraction ===
    confirmed_facts = dict(state.get("confirmed_facts") or {})
    confirmed_facts = extract_facts_from_text(deidentified_text, confirmed_facts)

    # Detect complaint category
    complaint_category = confirmed_facts.get("complaint_category") or \
        detect_complaint_category(deidentified_text, confirmed_facts.get("cc", ""))
    confirmed_facts["complaint_category"] = complaint_category

    # === Step 6: Code red flag combo check ===
    is_combo_emergency, combo_name = check_red_flag_combos(confirmed_facts)
    if is_combo_emergency:
        logger.warning("intake_v4.combo_emergency", combo=combo_name, case_id=case_id)
        return _emergency_response_v4(state, trigger=combo_name, confirmed_facts=confirmed_facts)

    # === Step 7: Build dynamic system prompt ===
    gender = confirmed_facts.get("gender", "")
    lang_label = "Tiếng Việt" if "vi" in detected_language else "English"

    mandatory_text = build_mandatory_injection(confirmed_facts, gender, complaint_category)
    complaint_probe = COMPLAINT_PROBES.get(complaint_category, COMPLAINT_PROBES["general"])

    system_prompt = (
        DOCTOR_SYSTEM_PROMPT
        .replace("{language}", lang_label)
        .replace("{mandatory_injection}", mandatory_text)
        .replace("{complaint_specific_injection}", complaint_probe)
    )

    # === Step 8: Build conversation history for LLM ===
    turn_count = state.get("turn_count", 0) + 1
    llm_messages = [{"role": "system", "content": system_prompt}]

    # Include full conversation (deidentified)
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else str(msg)
        deident, _ = phi_deidentifier.deidentify(content)
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        # Strip any markers from prior AI messages
        deident = _EMERGENCY_MARKER.sub("", deident).strip()
        deident = _INTAKE_DONE_MARKER.sub("", deident).strip()
        llm_messages.append({"role": role, "content": deident})

    # === Step 9: LLM call — single senior doctor ===
    try:
        response = await llm_gateway.generate(
            messages=llm_messages,
            agent_type="intake_v4_doctor",
            case_id=case_id,
            temperature=0.4,
        )
        raw_response = response.content.strip()
    except Exception as e:
        logger.error("intake_v4.llm_failed", case_id=case_id, error=str(e))
        raw_response = "Xin lỗi, tôi gặp sự cố kỹ thuật. Bạn có thể nhắn lại không?"

    # === Step 10: Parse LLM output for markers ===
    llm_wants_emergency = bool(_EMERGENCY_MARKER.search(raw_response))
    llm_wants_done = bool(_INTAKE_DONE_MARKER.search(raw_response))

    # Strip markers from patient-facing response
    patient_response = _EMERGENCY_MARKER.sub("", raw_response).strip()
    patient_response = _INTAKE_DONE_MARKER.sub("", patient_response).strip()

    # === Step 11: Code safety net — re-check emergency after LLM ===
    # Update facts from LLM response context (LLM may have surfaced new info)
    # Also re-check combos with any new facts extracted this turn
    is_combo_emergency2, combo_name2 = check_red_flag_combos(confirmed_facts)

    # Code guard: LLM [EMERGENCY] only trusted if there's at least 1 confirmed red flag
    _has_red_flag = any(confirmed_facts.get(f) == "yes" for f in [
        "chest_pain_flag", "diaphoresis", "dyspnea", "radiation_arm",
        "worst_headache_ever", "syncope", "vaginal_bleeding", "neck_stiffness",
    ])
    llm_emergency_valid = llm_wants_emergency and _has_red_flag

    if llm_emergency_valid or is_combo_emergency2:
        trigger = combo_name2 if is_combo_emergency2 else "llm_flagged"
        logger.warning("intake_v4.emergency_confirmed", trigger=trigger, case_id=case_id)
        # Use LLM's natural response but ensure emergency message
        emergency_prefix = (
            "⚠️ Dựa trên triệu chứng của bạn, đây có thể là tình trạng khẩn cấp.\n\n"
            "📞 **Gọi 115** (Việt Nam) hoặc **911** (Mỹ) ngay bây giờ.\n"
            "🏥 Hoặc đến phòng cấp cứu gần nhất ngay lập tức.\n\n"
        )
        # Keep LLM's explanation if meaningful, otherwise use standard message
        if len(patient_response) > 20 and "115" not in patient_response:
            emergency_msg = emergency_prefix
        else:
            emergency_msg = patient_response if patient_response else emergency_prefix

        tracker = IntakeTracker(data=state.get("intake_tracker"))
        _sync_tracker_from_facts(tracker, confirmed_facts)

        return {
            "messages": [AIMessage(content=emergency_msg)],
            "detected_language": detected_language,
            "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
            "is_emergency": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "intake_tracker": tracker.to_dict(),
            "intake_data": tracker.to_intake_data(),
            "intake_complete": False,
            "confirmed_facts": confirmed_facts,
            "turn_count": turn_count,
        }

    # === Step 12: Code completion gate ===
    intake_complete = False
    if llm_wants_done:
        intake_complete = _validate_completion(confirmed_facts, complaint_category, turn_count)
        if not intake_complete:
            logger.info(
                "intake_v4.premature_done_blocked",
                case_id=case_id,
                turn_count=turn_count,
                missing=_get_missing_fields(confirmed_facts, complaint_category),
            )
            # Don't complete — LLM will continue next turn with updated mandatory injection

    # === Step 13: Final cleanup — strip any markers that leaked through ===
    patient_response = _EMERGENCY_MARKER.sub("", patient_response).strip()
    patient_response = _INTAKE_DONE_MARKER.sub("", patient_response).strip()

    # PHI re-identification
    if phi_mapping:
        patient_response = phi_deidentifier.reidentify(patient_response, phi_mapping)

    # === Step 14: Update tracker ===
    tracker = IntakeTracker(data=state.get("intake_tracker"))
    _sync_tracker_from_facts(tracker, confirmed_facts)
    tracker.message_count = turn_count

    if intake_complete:
        patient_response = _generate_summary_v4(tracker, confirmed_facts)

    return {
        "messages": [AIMessage(content=patient_response)],
        "detected_language": detected_language,
        "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
        "is_emergency": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "intake_tracker": tracker.to_dict(),
        "intake_data": tracker.to_intake_data() if intake_complete else None,
        "intake_complete": intake_complete,
        "confirmed_facts": confirmed_facts,
        "turn_count": turn_count,
    }


def _validate_completion(facts: dict, category: str, turn_count: int) -> bool:
    """Code-enforced completion gate."""
    if turn_count < MIN_TURNS_FOR_COMPLETION:
        return False

    required = COMPLETION_REQUIRED_ALWAYS | COMPLETION_REQUIRED_BY_CATEGORY.get(category, set())
    # Add gendered requirements
    if facts.get("gender") == "female" and category in ("abdominal_pain", "general", "urinary"):
        required.add("lmp")

    missing = _get_missing_fields(facts, category)
    # Allow up to 2 missing non-critical fields (patient may have declined)
    critical = {"age", "gender", "cc", "onset", "location", "character", "severity"}
    critical_missing = [f for f in missing if f in critical]
    return len(critical_missing) == 0 and len(missing) <= 2


def _get_missing_fields(facts: dict, category: str) -> list[str]:
    required = COMPLETION_REQUIRED_ALWAYS | COMPLETION_REQUIRED_BY_CATEGORY.get(category, set())
    return [f for f in required if not facts.get(f)]


def _sync_tracker_from_facts(tracker: IntakeTracker, facts: dict) -> None:
    """Sync IntakeTracker from confirmed_facts dict."""
    if facts.get("age"):     tracker.age = facts["age"]
    if facts.get("gender"):  tracker.gender = facts["gender"]
    if facts.get("cc"):      tracker.cc = facts["cc"]
    for field in ["onset", "location", "duration", "character",
                  "aggravating", "alleviating", "timing", "severity"]:
        if facts.get(field):
            tracker.hpi[field] = facts[field]
    if facts.get("pmh"):         tracker.pmh = facts["pmh"]
    if facts.get("medications"): tracker.medications = facts["medications"]
    if facts.get("allergies"):   tracker.allergies = facts["allergies"]


def _generate_summary_v4(tracker: IntakeTracker, facts: dict) -> str:
    """Clean intake summary — no open questions."""
    age = facts.get("age") or tracker.age or "Chưa rõ"
    gender_map = {"female": "Nữ", "male": "Nam"}
    gender = gender_map.get(facts.get("gender", ""), facts.get("gender") or tracker.gender or "Chưa rõ")
    cc = facts.get("cc") or tracker.cc or "Chưa rõ"

    parts = [f"**Thông tin cơ bản:** {age} tuổi, {gender}", f"**Lý do khám:** {cc}"]

    hpi_labels = {
        "onset": "Khởi phát", "location": "Vị trí", "character": "Tính chất",
        "severity": "Mức độ", "duration": "Thời gian", "aggravating": "Yếu tố nặng",
        "alleviating": "Yếu tố giảm", "radiation": "Lan ra",
    }
    hpi_items = []
    for f, label in hpi_labels.items():
        val = facts.get(f) or tracker.hpi.get(f)
        if val:
            hpi_items.append(f"- {label}: {val}")
    if hpi_items:
        parts.append("\n**Triệu chứng:**\n" + "\n".join(hpi_items))

    assoc = []
    for sym in ["fever", "nausea", "anorexia", "bowel", "urinary", "dyspnea"]:
        val = facts.get(sym)
        if val:
            label = {"fever":"Sốt","nausea":"Buồn nôn","anorexia":"Chán ăn",
                     "bowel":"Đại tiện","urinary":"Tiểu tiện","dyspnea":"Khó thở"}.get(sym, sym)
            assoc.append(f"- {label}: {val}")
    if assoc:
        parts.append("\n**Triệu chứng đi kèm:**\n" + "\n".join(assoc))

    pmh_items = []
    if facts.get("pmh") or tracker.pmh:         pmh_items.append(f"Bệnh nền: {facts.get('pmh') or tracker.pmh}")
    if facts.get("medications") or tracker.medications: pmh_items.append(f"Thuốc: {facts.get('medications') or tracker.medications}")
    if facts.get("allergies") or tracker.allergies:     pmh_items.append(f"Dị ứng: {facts.get('allergies') or tracker.allergies}")
    if pmh_items:
        parts.append("\n**Tiền sử:**\n" + "\n".join(f"- {p}" for p in pmh_items))

    summary = "\n".join(parts)
    summary += "\n\nTôi đã ghi nhận đầy đủ. Bác sĩ sẽ xem xét và liên hệ với bạn sớm."
    return summary


def _initial_greeting_v4(state: CareFlowState) -> dict:
    tracker = IntakeTracker(existing_history=state.get("existing_history"))
    return {
        "messages": [AIMessage(content=(
            "Xin chào! Tôi là bác sĩ intake trực tuyến của Compass Vitals.\n\n"
            "Hôm nay bạn cần khám vì vấn đề gì? Hãy mô tả triệu chứng của bạn."
        ))],
        "detected_language": "vi",
        "is_emergency": False,
        "intake_tracker": tracker.to_dict(),
        "confirmed_facts": {},
        "turn_count": 0,
    }


def _emergency_response_v4(
    state: CareFlowState,
    trigger: str = "",
    confirmed_facts: dict = None,
) -> dict:
    tracker = IntakeTracker(data=state.get("intake_tracker"))
    content = (
        "⚠️ **CẢNH BÁO KHẨN CẤP**\n\n"
        "Dựa trên triệu chứng bạn mô tả, đây có thể là tình trạng cần xử lý NGAY LẬP TỨC.\n\n"
        "📞 **Gọi 115** (Việt Nam) hoặc **911** (Mỹ) ngay bây giờ\n"
        "🏥 Hoặc đến phòng cấp cứu gần nhất\n\n"
        "⚠️ **EMERGENCY ALERT** — Call **115** (Vietnam) or **911** (US) NOW"
    )
    return {
        "messages": [AIMessage(content=content)],
        "detected_language": state.get("detected_language", "vi"),
        "cultural_expressions": state.get("cultural_expressions", []),
        "is_emergency": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "intake_tracker": tracker.to_dict(),
        "intake_data": tracker.to_intake_data(),
        "intake_complete": False,
        "confirmed_facts": confirmed_facts or state.get("confirmed_facts", {}),
        "turn_count": state.get("turn_count", 0),
    }
