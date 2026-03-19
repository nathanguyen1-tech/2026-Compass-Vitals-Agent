"""Intake Agent V3 — Two-LLM Per Turn Architecture.

V3 philosophy:
  "Separate reasoning from speaking. Think first, then ask."

Each patient turn triggers TWO LLM calls:
  Call 1 — Clinical Reasoner (hidden): explicit structured reasoning about
            what is known, what is missing, what the differential is,
            what to ask next, and emergency risk score.
  Call 2 — Conversationalist (patient-facing): focused on generating
            ONE natural, empathetic question for exactly the target field.

Safety enforcement is done by CODE, not by prompt:
  - Instant emergency: keyword + vital sign detection (0ms)
  - Semantic emergency: Reasoner score ≥ 7 → escalation
  - Field skip persistence: code tracks & enforces, not LLM
  - Answer quality: 6-level scale, code-enforced progression
  - Intake completeness gate: code validates before downstream trigger
"""

import re
from datetime import datetime, timezone

import structlog
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.clinical_reasoner import run_clinical_reasoner
from app.agents.prompts.conversationalist_prompt import (
    CONVERSATIONALIST_SYSTEM_PROMPT,
    CONVERSATIONALIST_USER_TEMPLATE,
)
from app.agents.tools.intake_tracker import INTAKE_MARKER_PATTERN
from app.agents.state import CareFlowState
from app.agents.tools.differential_tracker import DifferentialTracker
from app.agents.tools.emergency_detector import detect_instant_emergency
from app.agents.tools.intake_tracker import IntakeTracker, parse_intake_markers
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier
from app.nlp.code_switcher import CodeSwitcher
from app.nlp.cultural_mapper import CulturalMapper

logger = structlog.get_logger()

code_switcher = CodeSwitcher()
cultural_mapper = CulturalMapper()

EMERGENCY_MARKER_PATTERN = re.compile(r"\[EMERGENCY:([^\]]+)\]")

# Max skip attempts before marking field as "declined"
MAX_SKIP_BEFORE_DECLINE = 3

# Emergency score thresholds — two-tier system
EMERGENCY_SCORE_URGENT = 7    # Score 7–8: needs care today (urgent, not ER)
EMERGENCY_SCORE_CRITICAL = 9  # Score 9–10: life-threatening, call 115/911 NOW


async def intake_node_v3(
    state: CareFlowState,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> dict:
    """V3 Intake Agent — Two-LLM Per Turn Architecture.

    Flow per patient message:
      1. Instant emergency check (code, 0ms)
      2. NLP pipeline (language detect, cultural mapping)
      3. PHI de-identification
      4. LLM Call 1: Clinical Reasoner → structured JSON
      5. Code: validate + enforce field requirements
      6. Check semantic emergency (score ≥ 7)
      7. LLM Call 2: Conversationalist → patient-facing question
      8. Update state (tracker + differential)
    """
    messages = state.get("messages", [])
    case_id = state.get("case_id", "unknown")

    # === No messages yet → initial greeting ===
    if not messages:
        return _initial_greeting_v3(state)

    # === Already complete — don't re-run intake ===
    if state.get("intake_complete"):
        return {
            "messages": [AIMessage(content=(
                "Cảm ơn bạn. Tôi đã ghi nhận đầy đủ thông tin. "
                "Bác sĩ sẽ xem xét và liên hệ với bạn sớm nhất có thể."
            ))],
            "detected_language": state.get("detected_language", "vi"),
            "is_emergency": False,
            "intake_complete": True,
            "intake_tracker": state.get("intake_tracker"),
            "differential_tracker": state.get("differential_tracker"),
            "intake_data": state.get("intake_data"),
        }

    last_message = messages[-1]
    patient_text = (
        last_message.content if hasattr(last_message, "content") else str(last_message)
    )

    # === Step 1: Prompt injection protection ===
    clean_text = INTAKE_MARKER_PATTERN.sub("", patient_text).strip()
    clean_text = EMERGENCY_MARKER_PATTERN.sub("", clean_text).strip()

    # === Step 2: Instant emergency check (code-enforced, 0ms) ===
    if detect_instant_emergency(clean_text):
        logger.warning("intake_v3.instant_emergency", case_id=case_id)
        return _emergency_response_v3(state)

    # === Step 3: NLP pipeline ===
    detected_language = code_switcher.detect_language(clean_text)
    cultural_expressions = cultural_mapper.map_expressions(clean_text)

    cultural_context = ""
    if cultural_expressions:
        cultural_context = "; ".join(
            f"'{e['original']}' → {e['medical_meaning']}"
            for e in cultural_expressions
        )

    # === Step 4: PHI de-identification ===
    deidentified_text, phi_mapping = phi_deidentifier.deidentify(clean_text)

    # === Step 5: Load / init trackers ===
    tracker = IntakeTracker(
        data=state.get("intake_tracker"),
        existing_history=state.get("existing_history"),
    )
    diff_tracker = DifferentialTracker(
        data=state.get("differential_tracker")
    )

    # === Step 6: LLM CALL 1 — Clinical Reasoner ===
    # De-identified messages for reasoner
    deidentified_messages = _deidentify_messages(messages, phi_deidentifier)

    reasoner_output = await run_clinical_reasoner(
        messages=deidentified_messages,
        patient_message=deidentified_text,
        differential_tracker=diff_tracker,
        llm_gateway=llm_gateway,
        case_id=case_id,
        cultural_context=cultural_context,
        phi_deidentifier=phi_deidentifier,
        last_asked_field=state.get("last_asked_field") or "unknown",
        narrative_done=state.get("narrative_done", False),
    )

    # === Step 7: Update DifferentialTracker from reasoner ===
    diff_tracker.update_from_reasoner(reasoner_output)

    # === Step 7b: Safety-by-code answer extraction ===
    # Do NOT trust LLM to classify "bình thường" answers — enforce in Python.
    last_field = state.get("last_asked_field") or ""
    _raw_user_text = last_message.content if hasattr(last_message, "content") else str(last_message)
    user_lower = _raw_user_text.lower()

    _NEGATIVE_PATTERNS = [
        "bình thường", "không có", "không bị", "không sốt", "không buồn nôn",
        "không nôn", "không tiêu chảy", "không táo bón", "không tiểu buốt",
        "không khó thở", "không hồi hộp", "ổn hết", "bình thường hết",
        "không gì hết", "không có gì", "không thấy gì", "không biết",
        "không liên quan", "không theo thời gian", "không rõ",
    ]
    # Fields where a negative/normal answer from patient = clinically sufficient
    _NEGATIVE_SUFFICIENT_FIELDS = {
        "fever", "nausea", "anorexia", "bowel", "urinary", "dyspnea", "palpitations",
        "diaphoresis", "jaundice", "weight_loss", "night_sweats",
        "vaginal_bleeding", "radiation", "travel_history",
        "timing", "alleviating", "aggravating",  # OLDCARTS: "không có" is valid
    }

    if last_field in _NEGATIVE_SUFFICIENT_FIELDS:
        patient_said_normal = any(p in user_lower for p in _NEGATIVE_PATTERNS)
        if patient_said_normal:
            if "answer_quality" not in reasoner_output:
                reasoner_output["answer_quality"] = {}
            if reasoner_output["answer_quality"].get(last_field) in (None, "vague", "partial", "skipped"):
                reasoner_output["answer_quality"][last_field] = "sufficient"
            if "known_facts" not in reasoner_output:
                reasoner_output["known_facts"] = {}
            if not reasoner_output["known_facts"].get(last_field):
                reasoner_output["known_facts"][last_field] = "patient reported none/normal"
            diff_tracker.update_from_reasoner(reasoner_output)
            logger.info("intake_v3.forced_sufficient", field=last_field, user_text=_raw_user_text[:80], case_id=case_id)

    # Safety-by-code: extract PMH/medications/allergies/social from patient text
    _pmh_negatives     = ["không có bệnh nền", "không bệnh nền", "không bệnh gì", "khỏe mạnh", "no medical history", "không có tiền sử"]
    _meds_negatives    = ["không dùng thuốc", "không uống thuốc", "không có thuốc", "no medication", "không thuốc"]
    _allergy_negatives = ["không dị ứng", "không có dị ứng", "no allergy", "no allergies"]
    _no_smoke          = ["không hút thuốc", "không hút", "chưa hút bao giờ", "no smoking", "non-smoker"]
    _no_alcohol        = ["không uống rượu", "không uống bia", "không uống rượu bia", "no alcohol"]
    _no_family_hx      = ["không có tiền sử gia đình", "gia đình không ai bị", "no family history"]

    _kf = reasoner_output.setdefault("known_facts", {})
    _aq = reasoner_output.setdefault("answer_quality", {})
    forced_fields = []

    if not _kf.get("pmh") and any(p in user_lower for p in _pmh_negatives):
        _kf["pmh"] = "none reported"; _aq["pmh"] = "sufficient"; forced_fields.append("pmh")
    if not _kf.get("medications") and any(p in user_lower for p in _meds_negatives):
        _kf["medications"] = "none"; _aq["medications"] = "sufficient"; forced_fields.append("medications")
    if not _kf.get("allergies") and any(p in user_lower for p in _allergy_negatives):
        _kf["allergies"] = "none"; _aq["allergies"] = "sufficient"; forced_fields.append("allergies")

    # Social history negative extractions
    _sh = _kf.get("social_history", "") or ""
    if "không hút" not in _sh and any(p in user_lower for p in _no_smoke):
        _kf["social_history"] = (_sh + "; không hút thuốc").strip("; ")
        _aq["social_history"] = "partial"  # Alcohol still needed
        forced_fields.append("social_history(smoke)")
    if "không uống" not in _sh and any(p in user_lower for p in _no_alcohol):
        existing = _kf.get("social_history", "") or ""
        _kf["social_history"] = (existing + "; không uống rượu bia").strip("; ")
        _aq["social_history"] = "sufficient"
        forced_fields.append("social_history(alcohol)")
    if not _kf.get("family_history") and any(p in user_lower for p in _no_family_hx):
        _kf["family_history"] = "none reported"; _aq["family_history"] = "sufficient"; forced_fields.append("family_history")

    if forced_fields:
        diff_tracker.update_from_reasoner(reasoner_output)
        logger.info("intake_v3.forced_extract", fields=forced_fields, case_id=case_id)

    # === Step 7c: Safety-by-code positive symptom extraction ===
    # Extract POSITIVE answers that LLM might miss (not just negatives)
    _POSITIVE_ANOREXIA = ["chán ăn", "mất cảm giác ngon", "không muốn ăn", "không thấy ngon", "không ăn được"]
    _POSITIVE_NAUSEA   = ["buồn nôn", "nôn", "muốn ói", "ói"]
    _POSITIVE_FEVER    = ["sốt", "nóng người", "nóng sốt"]
    _POSITIVE_WEIGHT   = ["sụt cân", "gầy đi", "giảm cân không cố ý", "sút cân"]
    _POSITIVE_SWEAT    = ["đổ mồ hôi đêm", "mồ hôi đêm"]

    _pos_kf = reasoner_output.setdefault("known_facts", {})
    _pos_aq = reasoner_output.setdefault("answer_quality", {})

    def _force_positive(field, value):
        if not _pos_kf.get(field):
            _pos_kf[field] = value
            _pos_aq[field] = "sufficient"

    if any(p in user_lower for p in _POSITIVE_ANOREXIA): _force_positive("anorexia", "yes — chán ăn")
    if any(p in user_lower for p in _POSITIVE_NAUSEA):   _force_positive("nausea", "yes — buồn nôn/nôn")
    if any(p in user_lower for p in _POSITIVE_FEVER):    _force_positive("fever", "yes — sốt")
    if any(p in user_lower for p in _POSITIVE_WEIGHT):   _force_positive("weight_loss", "yes — sụt cân")
    if any(p in user_lower for p in _POSITIVE_SWEAT):    _force_positive("night_sweats", "yes — đổ mồ hôi đêm")

    if _pos_kf != reasoner_output.get("known_facts", {}):
        diff_tracker.update_from_reasoner(reasoner_output)

    # === Step 8: Emergency check (code-enforced) ===
    score = diff_tracker.emergency_score
    if score >= EMERGENCY_SCORE_CRITICAL:
        logger.warning("intake_v3.critical_emergency", case_id=case_id, score=score)
        return _emergency_response_v3(state, reason=diff_tracker.emergency_reasoning, critical=True)
    elif score >= EMERGENCY_SCORE_URGENT:
        logger.info("intake_v3.urgent_flag", case_id=case_id, score=score)

    # === Step 8b: Code-side skip tracking ===
    _last_asked = state.get("last_asked_field") or ""
    if _last_asked and _last_asked not in ("narrative_open", "cc", "age_gender", "unknown", ""):
        _aq_check = reasoner_output.get("answer_quality", {})
        _quality_check = _aq_check.get(_last_asked, "")
        if _quality_check in ("skipped", "redirected", "vague", ""):
            diff_tracker.increment_skip(_last_asked)

    # === Step 9: CODE STATE MACHINE decides next field (LLM suggestion ignored) ===
    _kf_now = reasoner_output.get("known_facts", {})
    _aq_now = reasoner_output.get("answer_quality", {})
    next_target, reason_for_target = _code_decide_next_field(
        kf=_kf_now,
        aq=_aq_now,
        diff_tracker=diff_tracker,
        state=state,
        tracker=tracker,
        reasoner_output=reasoner_output,
    )
    logger.info("intake_v3.code_next_field", field=next_target, reason=reason_for_target, case_id=case_id)

    # === Step 9b: narrative_done latch ===
    current_narrative_done = (
        state.get("narrative_done", False)
        or (state.get("last_asked_field") == "narrative_open")
        or reasoner_output.get("narrative_done", False)
    )

    # === Step 10: intake_complete from code state machine ===
    intake_complete = (next_target == "INTAKE_COMPLETE")
    if intake_complete:
        hpi_filled, _ = tracker.get_hpi_coverage()
        if hpi_filled < 4:
            intake_complete = False
            next_target = _find_next_oldcarts_target(tracker)
            reason_for_target = f"Code gate: only {hpi_filled}/8 OLDCARTS"

    # Urgent advisory when score 7-8 and intake is complete
    # But first ensure critical safety questions were asked (vaginal_bleeding for female pelvic)
    _kf_final = reasoner_output.get("known_facts", {})
    _gender_final = (_kf_final.get("gender") or tracker.gender or "").lower()
    _is_female_final = "nữ" in _gender_final or "female" in _gender_final
    _complaint_final = (reasoner_output.get("complaint_category") or "").lower()
    _vb_needed = _is_female_final and _complaint_final in ("abdominal_pain", "general", "")
    _vb_asked = diff_tracker.is_field_sufficient("vaginal_bleeding") or diff_tracker.get_skip_count("vaginal_bleeding") >= 1
    if score >= EMERGENCY_SCORE_URGENT and intake_complete and (_vb_needed and not _vb_asked):
        # Must ask vaginal_bleeding first before completing
        intake_complete = False
        next_target = "vaginal_bleeding"
        reason_for_target = "Female + pelvic pain + score 7-8 — must rule out ectopic before handoff"
        skip_count = diff_tracker.get_skip_count("vaginal_bleeding")

    if score >= EMERGENCY_SCORE_URGENT and intake_complete:
        _sync_tracker_from_reasoner(tracker, reasoner_output)
        tracker.message_count += 1
        intake_data = tracker.to_intake_data()
        urgent_msg = (
            "⚠️ Dựa trên những gì bạn mô tả, tôi khuyến nghị bạn nên **gặp bác sĩ trong ngày hôm nay** "
            "— không cần gọi cấp cứu, nhưng nên được khám sớm.\n\n"
            "Tôi đã ghi nhận đầy đủ thông tin của bạn và sẽ chuyển cho bác sĩ xem xét ngay."
        )
        return {
            "messages": [AIMessage(content=urgent_msg)],
            "detected_language": detected_language,
            "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
            "is_emergency": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "intake_tracker": tracker.to_dict(),
            "differential_tracker": diff_tracker.to_dict(),
            "intake_data": intake_data,
            "intake_complete": True,
        }

    # skip_count for the field code just chose
    skip_count = diff_tracker.get_skip_count(next_target)

    # === Step 11: Update IntakeTracker from reasoner known_facts ===
    _sync_tracker_from_reasoner(tracker, reasoner_output)
    tracker.message_count += 1

    # === Step 11b: Determine narrative_done for state update ===
    # True if: (a) already done before this turn, OR (b) we are asking narrative_open this turn
    narrative_done = current_narrative_done or (next_target == "narrative_open")

    # === Step 12: LLM CALL 2 — Conversationalist ===
    if next_target == "INTAKE_COMPLETE" or intake_complete:
        patient_response = _generate_summary(tracker)
        intake_complete = True
    else:
        # Extract last patient message for acknowledgment
        last_patient_message = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_patient_message = msg.content if hasattr(msg, "content") else str(msg)
                break

        patient_response = await _run_conversationalist(
            target_field=next_target,
            reason_for_target=reason_for_target,
            skip_count=skip_count,
            messages=messages,
            language=detected_language,
            llm_gateway=llm_gateway,
            case_id=case_id,
            last_patient_message=last_patient_message,
        )

    # Re-identify PHI in response
    if phi_mapping:
        patient_response = phi_deidentifier.reidentify(patient_response, phi_mapping)

    # === Step 13: Return updated state ===
    intake_data = tracker.to_intake_data()

    return {
        "messages": [AIMessage(content=patient_response)],
        "detected_language": detected_language,
        "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
        "is_emergency": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "intake_tracker": tracker.to_dict(),
        "differential_tracker": diff_tracker.to_dict(),
        "intake_data": intake_data if intake_data else None,
        "intake_complete": intake_complete,
        "last_asked_field": next_target,  # Track for next turn's Reasoner
        "narrative_done": narrative_done,  # Persist narrative phase state
    }


async def _run_conversationalist(
    target_field: str,
    reason_for_target: str,
    skip_count: int,
    messages: list,
    language: str,
    llm_gateway: LLMGateway,
    case_id: str,
    last_patient_message: str = "",
) -> str:
    """LLM Call 2: generate ONE focused patient-facing question."""
    lang_label = "Tiếng Việt" if "vi" in language else "English"

    system_prompt = (
        CONVERSATIONALIST_SYSTEM_PROMPT
        .replace("{language}", lang_label)
        .replace("{target_field}", target_field)
        .replace("{reason_for_target}", reason_for_target)
        .replace("{skip_count}", str(skip_count))
        .replace("{last_patient_message}", last_patient_message or "")
    )

    # Recent history: last 4 turns for context
    from langchain_core.messages import HumanMessage as HM, AIMessage as AM
    recent = []
    for msg in messages[-8:]:
        content = msg.content if hasattr(msg, "content") else str(msg)
        prefix = "Patient" if isinstance(msg, HM) else "Agent"
        recent.append(f"{prefix}: {content}")
    recent_history = "\n".join(recent)

    user_prompt = (
        CONVERSATIONALIST_USER_TEMPLATE
        .replace("{target_field}", target_field)
        .replace("{skip_count}", str(skip_count))
        .replace("{last_patient_message}", last_patient_message or "")
        .replace("{recent_history}", recent_history)
    )

    llm_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await llm_gateway.generate(
            messages=llm_messages,
            agent_type="intake_v3_conversationalist",
            case_id=case_id,
            temperature=0.6,  # Some creativity for natural conversation
        )
        return response.content.strip()
    except Exception as e:
        logger.error("conversationalist.llm_call_failed", case_id=case_id, error=str(e))
        # Fallback: minimal question
        fallback_questions = {
            "location": "Bạn cảm thấy đau / khó chịu ở vị trí nào cụ thể?",
            "character": "Bạn có thể mô tả cảm giác đó như thế nào — âm ỉ, nhói, hay co thắt?",
            "onset": "Triệu chứng này bắt đầu từ khi nào?",
            "severity": "Trên thang 1-10, bạn cho mức độ khó chịu này mấy điểm?",
            "cc": "Hôm nay bạn cần khám vì vấn đề gì?",
        }
        return fallback_questions.get(target_field, f"Bạn có thể cho tôi biết thêm về {target_field}?")


def _deidentify_messages(messages: list, phi_deidentifier: PHIDeidentifier) -> list:
    """Return a copy of messages with PHI de-identified."""
    result = []
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else str(msg)
        deidentified, _ = phi_deidentifier.deidentify(content)
        if isinstance(msg, HumanMessage):
            result.append(HumanMessage(content=deidentified))
        elif isinstance(msg, AIMessage):
            result.append(AIMessage(content=deidentified))
    return result


def _sync_tracker_from_reasoner(tracker: IntakeTracker, reasoner_output: dict) -> None:
    """Sync IntakeTracker fields from Reasoner's known_facts."""
    known = reasoner_output.get("known_facts", {})
    field_map = {
        "age": "age", "gender": "gender", "cc": "cc",
        "onset": "onset", "location": "location",
        "duration": "duration", "character": "character",
        "aggravating": "aggravating", "alleviating": "alleviating",
        "timing": "timing", "severity": "severity",
        "pmh": "pmh", "medications": "medications", "allergies": "allergies",
        "social_history": "social_family",
        "family_history": "social_family",
    }
    for reasoner_key, tracker_field in field_map.items():
        value = known.get(reasoner_key)
        if value and value != "null":
            tracker.update_field(tracker_field, str(value))

    # Sync new clinical fields to hpi_additional
    hpi_additional_fields = [
        "functional_status", "radiation", "anorexia", "weight_loss",
        "night_sweats", "jaundice", "travel_history", "vaginal_bleeding", "diaphoresis",
    ]
    for field in hpi_additional_fields:
        value = known.get(field)
        if value and value != "null":
            tracker.hpi_additional[field] = str(value)

    # Sync risk level
    emergency_score = reasoner_output.get("emergency_score", 0)
    if emergency_score >= 7:
        tracker.risk_level = "critical"
    elif emergency_score >= 5:
        tracker.risk_level = "high"
    elif emergency_score >= 3:
        tracker.risk_level = "moderate"
    else:
        tracker.risk_level = "low"

    # Mark intake complete if reasoner + code both agree
    if reasoner_output.get("intake_complete"):
        tracker.phase = "summary"


def _is_field_done(field: str, kf: dict, aq: dict, diff_tracker: DifferentialTracker) -> bool:
    """Code-enforced check: is this field sufficiently answered or declined?"""
    q = aq.get(field, "")
    if q in ("sufficient", "declined"):
        return True
    if diff_tracker.is_field_sufficient(field):
        return True
    val = kf.get(field)
    # For boolean-negative fields, any value is sufficient
    if val and val not in ("null", "None", ""):
        return True
    return False


def _code_decide_next_field(
    kf: dict,
    aq: dict,
    diff_tracker: DifferentialTracker,
    state: dict,
    tracker: "IntakeTracker",
    reasoner_output: dict,
) -> tuple[str, str]:
    """
    CODE-ENFORCED phase state machine.
    Returns (next_field, reason).

    LLM suggestion is IGNORED — code fully controls flow.
    Rules:
      - Gender unknown → ask gender before any gendered question
      - Phases in order: CC → Narrative → HPI Core → Associated Symptoms (complaint-specific) → Social Hx → Family Hx → PMH → Medications → Allergies → COMPLETE
      - Never jump phases (e.g., no urinary while asking PMH)
      - Never ask gendered questions without confirmed gender
      - Skip declined fields
    """
    gender = (kf.get("gender") or tracker.gender or "").lower()
    cc = kf.get("cc") or tracker.cc or ""
    complaint_cat = reasoner_output.get("complaint_category", "general")
    is_female = "nữ" in gender or "female" in gender or "f" == gender

    def done(f):
        return _is_field_done(f, kf, aq, diff_tracker)

    def skipped_max(f):
        return diff_tracker.get_skip_count(f) >= MAX_SKIP_BEFORE_DECLINE

    def next_undone(fields, reason):
        for f in fields:
            if not done(f) and not skipped_max(f):
                return f, reason
        return None, None

    # Phase 1: CC
    if not cc:
        return "cc", "Chief complaint not yet captured"

    # Phase 2: Narrative (once only)
    narrative_done = (
        state.get("narrative_done", False)
        or state.get("last_asked_field") == "narrative_open"
        or reasoner_output.get("narrative_done", False)
    )
    if not narrative_done:
        return "narrative_open", "Open narrative — let patient describe in own words"

    # Phase 3: HPI Core — OLDCARTS in clinical priority order
    # Onset + Location first (highest yield for differential), then character, severity, etc.
    hpi_order = ["onset", "location", "character", "severity", "aggravating", "alleviating", "duration", "timing"]
    f, r = next_undone(hpi_order[:4], "Core HPI — highest yield for differential")
    if f:
        return f, r

    # Phase 4a: Emergency-relevant associated symptoms (complaint-specific)
    # ONLY based on complaint category
    abdominal_cats = {"abdominal_pain", "general"}
    chest_cats = {"chest_pain"}
    head_cats = {"headache"}
    resp_cats = {"respiratory"}

    if complaint_cat in abdominal_cats or "đau bụng" in cc.lower() or "bụng" in cc.lower():
        # Core: fever, nausea, anorexia (key for appendicitis/cancer)
        f, r = next_undone(["fever", "nausea", "anorexia"], "Abdominal complaint — core associated symptoms")
        if f:
            return f, r
        # Radiation (key discriminating feature)
        if not done("radiation"):
            return "radiation", "Radiation pattern — critical for renal colic vs appendicitis vs biliary"
        # Bowel/urinary
        f, r = next_undone(["bowel", "urinary"], "Abdominal — bowel/urinary changes")
        if f:
            return f, r
        # Gendered: only if female confirmed
        if is_female:
            if not done("lmp") and not skipped_max("lmp"):
                return "lmp", "Female + abdominal pain — LMP essential for ectopic/ovarian"
            if not done("vaginal_bleeding") and not skipped_max("vaginal_bleeding"):
                return "vaginal_bleeding", "Female + lower abdominal — rule out ectopic"
        elif not gender:
            # Gender unknown — ask gender first before any gendered question
            return "age_gender", "Need gender to determine if LMP/pregnancy questions apply"

    elif complaint_cat in chest_cats or "ngực" in cc.lower():
        f, r = next_undone(["radiation", "dyspnea", "diaphoresis", "palpitations"], "Chest — discriminating symptoms")
        if f:
            return f, r

    elif complaint_cat in head_cats or "đau đầu" in cc.lower():
        f, r = next_undone(["fever", "nausea"], "Headache — meningismus screen")
        if f:
            return f, r

    elif complaint_cat in resp_cats:
        f, r = next_undone(["dyspnea", "fever", "nausea"], "Respiratory — associated symptoms")
        if f:
            return f, r

    else:
        # General: fever, nausea only
        f, r = next_undone(["fever", "nausea"], "General — core associated symptoms")
        if f:
            return f, r

    # Phase 4b: Remaining OLDCARTS (lower priority)
    f, r = next_undone(hpi_order[4:], "Remaining HPI fields")
    if f:
        return f, r

    # Phase 4c: Functional status (once)
    if not done("functional_status") and not skipped_max("functional_status"):
        return "functional_status", "Functional impact — severity validation"

    # Phase 5: Demographic if still unknown
    if not kf.get("age") and not tracker.age:
        return "age_gender", "Age/gender still unknown"

    # Phase 6: Social history — smoking then alcohol
    _sh = kf.get("social_history") or ""
    _sh_done = aq.get("social_history") == "sufficient" or done("social_history")
    if not _sh_done and not skipped_max("social_history"):
        return "social_history", "Social history — smoking/alcohol"

    # Phase 7: Family history (only if relevant complaint)
    _fh_relevant = complaint_cat in chest_cats | {"general"} or any(
        w in cc.lower() for w in ["ngực", "tim", "đầu", "bụng"]
    )
    if _fh_relevant and not done("family_history") and not skipped_max("family_history"):
        return "family_history", "Family history — hereditary/cardiac/cancer risk"

    # Phase 8: PMH / Medications / Allergies
    f, r = next_undone(["pmh", "medications", "allergies"], "Past medical history")
    if f:
        return f, r

    # All done
    return "INTAKE_COMPLETE", "All required fields collected"


def _find_next_oldcarts_target(tracker: IntakeTracker) -> str:
    """Fallback: find first OLDCARTS field not yet filled."""
    from app.agents.tools.intake_tracker import OLDCARTS_FIELDS
    for field in OLDCARTS_FIELDS:
        if not tracker.hpi.get(field):
            return field
    return "pmh"


def _find_next_partial_or_oldcarts_target(
    tracker: IntakeTracker,
    diff_tracker: DifferentialTracker,
    reasoner_output: dict,
) -> str:
    """Smart fallback: pick highest-yield missing field from reasoner known_facts."""
    known = reasoner_output.get("known_facts", {})
    quality = reasoner_output.get("answer_quality", {})

    # Priority 1: OLDCARTS fields marked partial by reasoner
    from app.agents.tools.intake_tracker import OLDCARTS_FIELDS
    for field in OLDCARTS_FIELDS:
        if quality.get(field) in ("partial", "vague"):
            return field

    # Priority 2: OLDCARTS fields null in known_facts
    for field in OLDCARTS_FIELDS:
        if not known.get(field) and quality.get(field) not in ("declined", "sufficient"):
            return field

    # Priority 3: Key associated symptoms not yet asked
    for field in ["fever", "nausea", "anorexia", "bowel", "urinary", "radiation", "functional_status"]:
        if not known.get(field) and quality.get(field) not in ("declined", "sufficient"):
            return field

    # Priority 4: Social/family/PMH
    for field in ["social_history", "family_history", "pmh", "medications", "allergies"]:
        if not known.get(field) and quality.get(field) not in ("declined", "sufficient"):
            return field

    return "INTAKE_COMPLETE"


def _generate_summary(tracker: IntakeTracker) -> str:
    """Generate intake summary — clean handoff, no open questions."""
    age = tracker.age or "Chưa rõ"
    gender = tracker.gender or "Chưa rõ"
    cc = tracker.cc or "Chưa rõ"

    hpi_parts = []
    for field in ["onset", "location", "duration", "character", "severity",
                  "aggravating", "alleviating", "timing"]:
        val = tracker.hpi.get(field)
        if val:
            label = {
                "onset": "Khởi phát", "location": "Vị trí", "duration": "Thời gian",
                "character": "Tính chất", "severity": "Mức độ",
                "aggravating": "Yếu tố làm nặng", "alleviating": "Yếu tố giảm",
                "timing": "Diễn tiến",
            }.get(field, field.capitalize())
            hpi_parts.append(f"- {label}: {val}")

    summary = (
        f"**Thông tin cơ bản:** {age} tuổi, {gender}\n"
        f"**Lý do khám:** {cc}\n"
    )
    if hpi_parts:
        summary += "\n**Diễn tiến triệu chứng:**\n" + "\n".join(hpi_parts)

    extras = []
    if tracker.pmh:        extras.append(f"**Bệnh nền:** {tracker.pmh}")
    if tracker.medications: extras.append(f"**Thuốc:** {tracker.medications}")
    if tracker.allergies:   extras.append(f"**Dị ứng:** {tracker.allergies}")
    if extras:
        summary += "\n\n" + "\n".join(extras)

    summary += (
        "\n\nTôi đã ghi nhận đầy đủ thông tin. "
        "Bác sĩ sẽ xem xét và liên hệ với bạn sớm nhất có thể."
    )
    return summary


def _initial_greeting_v3(state: CareFlowState) -> dict:
    """Return initial greeting — open-ended to capture chief complaint naturally."""
    tracker = IntakeTracker(existing_history=state.get("existing_history"))
    tracker.phase = "greeting"
    diff_tracker = DifferentialTracker()

    return {
        "messages": [
            AIMessage(
                content=(
                    "Xin chào! Tôi là bác sĩ intake trực tuyến của Compass Vitals.\n\n"
                    "Hôm nay bạn cần khám vì vấn đề gì? Hãy mô tả triệu chứng của bạn."
                )
            )
        ],
        "detected_language": "vi",
        "is_emergency": False,
        "intake_tracker": tracker.to_dict(),
        "differential_tracker": diff_tracker.to_dict(),
    }


def _emergency_response_v3(state: CareFlowState, reason: str = "", critical: bool = True) -> dict:
    """Emergency escalation response."""
    tracker = IntakeTracker(
        data=state.get("intake_tracker"),
        existing_history=state.get("existing_history"),
    )

    content = (
        "⚠️ **CẢNH BÁO KHẨN CẤP**\n\n"
        "Dựa trên triệu chứng bạn mô tả, đây có thể là tình trạng cần xử lý NGAY LẬP TỨC.\n\n"
        "📞 **Gọi 115** (Việt Nam) hoặc **911** (Mỹ) ngay bây giờ\n"
        "🏥 Hoặc đến phòng cấp cứu gần nhất\n\n"
        "⚠️ **EMERGENCY ALERT**\n\n"
        "Based on your symptoms, you need IMMEDIATE medical evaluation.\n"
        "📞 Call **115** (Vietnam) or **911** (US) NOW\n"
        "🏥 Or go to the nearest emergency room immediately"
    )

    return {
        "messages": [AIMessage(content=content)],
        "detected_language": state.get("detected_language", "vi"),
        "cultural_expressions": state.get("cultural_expressions", []),
        "is_emergency": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "intake_tracker": tracker.to_dict(),
        "differential_tracker": state.get("differential_tracker", {}),
        "intake_data": tracker.to_intake_data(),
        "intake_complete": False,
    }
