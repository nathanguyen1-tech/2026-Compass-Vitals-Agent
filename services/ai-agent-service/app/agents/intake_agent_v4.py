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

# Patient declining to add more (closing confirmation pattern)
_NO_SUPPLEMENT_PATTERN = re.compile(
    r'^(không|ko|k|no|nope|không có|không có gì|không bổ sung|'
    r'không thêm|không có gì thêm|đủ rồi|xong|xong rồi|ok|okay|'
    r'được rồi|vậy thôi|hết rồi|không muốn|không cần)\b',
    re.IGNORECASE | re.UNICODE,
)

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
        # meal_relation: nice-to-have, not blocking
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

    # === Step 5b: Context-aware extraction — standalone "không/no" ===
    # When patient answers just "không" to a specific question, infer what field they answered
    _is_bare_negative = deidentified_text.strip().lower() in (
        "không", "ko", "k", "no", "nope", "không có", "không bị", "chưa", "không dùng"
    )
    # Get last AI message for all context-aware logic
    _last_ai_content = ""
    for _msg in reversed(messages[:-1]):
        if isinstance(_msg, AIMessage):
            _last_ai_content = (_msg.content if hasattr(_msg, "content") else str(_msg)).lower()
            break

    # Context-aware: bare negative "không" answers for ANY symptom field AI just asked
    _SYMPTOM_KEYWORD_MAP = {
        "nausea":    ["buồn nôn", "nôn", "nausea"],
        "fever":     ["sốt", "fever", "nhiệt độ"],
        "urinary":   ["tiểu", "urinary", "tiểu tiện"],
        "anorexia":  ["chán ăn", "appetite", "ngon miệng"],
        "dyspnea":   ["khó thở", "shortness", "hụt hơi"],
        "radiation": ["lan ra", "radiation", "lan lên"],
    }
    if _is_bare_negative and _last_ai_content:
        for field, keywords in _SYMPTOM_KEYWORD_MAP.items():
            if any(kw in _last_ai_content for kw in keywords) and not confirmed_facts.get(field):
                confirmed_facts[field] = "no"

    # Context-aware: bare number after AI asks age or severity
    _bare_number = re.fullmatch(r'\d{1,3}', deidentified_text.strip())
    if _bare_number and _last_ai_content:
        bare_val = int(deidentified_text.strip())

        # Bare number → severity (if AI just asked about pain scale 1-10)
        _severity_kw = ["thang", "1-10", "1 đến 10", "mức độ đau", "mấy điểm", "pain scale", "mức đau"]
        if not confirmed_facts.get("severity") and any(kw in _last_ai_content for kw in _severity_kw):
            if 1 <= bare_val <= 10:
                confirmed_facts["severity"] = f"{bare_val}/10"

        # Bare number → age (if AI just asked about age)
        elif not confirmed_facts.get("age"):
            if "tuổi" in _last_ai_content or "age" in _last_ai_content:
                if 1 <= bare_val <= 120:
                    confirmed_facts["age"] = str(bare_val)

    if _is_bare_negative:
        last_ai_msg = _last_ai_content
        if last_ai_msg:
            _pmh_kw  = ["bệnh nền", "tiền sử", "bệnh lý", "medical history", "bệnh mãn", "bệnh tim", "tiểu đường", "huyết áp"]
            _meds_kw = ["thuốc", "medication", "dùng thuốc", "uống thuốc"]
            _allergy_kw = ["dị ứng", "allergy"]

            if any(kw in last_ai_msg for kw in _pmh_kw)     and not confirmed_facts.get("pmh"):
                confirmed_facts["pmh"] = "none"
            if any(kw in last_ai_msg for kw in _meds_kw)    and not confirmed_facts.get("medications"):
                confirmed_facts["medications"] = "none"
            if any(kw in last_ai_msg for kw in _allergy_kw) and not confirmed_facts.get("allergies"):
                confirmed_facts["allergies"] = "none"
            if "sốt" in last_ai_msg and not confirmed_facts.get("fever"):
                confirmed_facts["fever"] = "no"
            if any(kw in last_ai_msg for kw in ["mang thai", "kinh nguyệt", "kinh"]) and not confirmed_facts.get("lmp"):
                confirmed_facts["lmp"] = "none/not applicable"
    # Context-aware: LMP — AI asked about kinh nguyệt and BN answered with time expression
    if not _is_bare_negative and not confirmed_facts.get("lmp") and _last_ai_content:
        _ai_asked_lmp = any(kw in _last_ai_content for kw in ["kinh nguyệt", "kinh", "lmp", "kỳ kinh"])
        _is_time_answer = bool(re.search(r'(?:tuần|tháng|ngày|hôm|cách đây|trước|qua)', deidentified_text))
        if _ai_asked_lmp and _is_time_answer:
            confirmed_facts["lmp"] = deidentified_text.strip()
            if "tiểu" in last_ai_msg and not confirmed_facts.get("urinary"):
                confirmed_facts["urinary"] = "normal"
            if "hút thuốc" in last_ai_msg and not confirmed_facts.get("social_history"):
                confirmed_facts["social_history"] = "no smoking"
            if any(kw in last_ai_msg for kw in ["giới tính", "nam hay nữ", "nam hoặc nữ"]):
                raw = deidentified_text.strip().lower()
                if raw in ("nữ", "female", "f", "gái"):
                    confirmed_facts["gender"] = "female"
                elif raw in ("nam", "male", "m", "trai"):
                    confirmed_facts["gender"] = "male"

            # Heuristic: if AI asked combo (PMH + meds in same message) → "không" clears all 3
            _asked_pmh  = any(kw in last_ai_msg for kw in _pmh_kw)
            _asked_meds = any(kw in last_ai_msg for kw in _meds_kw)
            if _asked_pmh and _asked_meds:
                if not confirmed_facts.get("pmh"):         confirmed_facts["pmh"] = "none"
                if not confirmed_facts.get("medications"):  confirmed_facts["medications"] = "none"

    # Detect complaint category
    complaint_category = confirmed_facts.get("complaint_category") or \
        detect_complaint_category(deidentified_text, confirmed_facts.get("cc", ""))
    confirmed_facts["complaint_category"] = complaint_category

    # === Step 6: Code red flag combo check ===
    is_combo_emergency, combo_name = check_red_flag_combos(confirmed_facts)
    if is_combo_emergency:
        logger.warning("intake_v4.combo_emergency", combo=combo_name, case_id=case_id)
        return _emergency_response_v4(state, trigger=combo_name, confirmed_facts=confirmed_facts)

    # === Step 6b: Code-enforced early demographics gate ===
    # Age and gender MUST be asked by turn 3. If missing after CC is known, force it.
    _has_cc = bool(confirmed_facts.get("cc"))
    _missing_age = not confirmed_facts.get("age")
    _missing_gender = not confirmed_facts.get("gender")
    _early_turns = state.get("turn_count", 0)  # turn_count not yet incremented this turn

    if _has_cc and (_missing_age or _missing_gender) and _early_turns >= 3:
        # Code hard-override: ask age+gender now, skip LLM for this turn
        if _missing_age and _missing_gender:
            early_q = "Bạn bao nhiêu tuổi và là nam hay nữ?"
        elif _missing_age:
            early_q = "Bạn bao nhiêu tuổi?"
        else:
            early_q = "Bạn là nam hay nữ?"

        tracker = IntakeTracker(data=state.get("intake_tracker"))
        _sync_tracker_from_facts(tracker, confirmed_facts)
        turn_count_early = _early_turns + 1
        tracker.message_count = turn_count_early

        logger.info("intake_v4.early_demographics_forced", case_id=case_id,
                    missing_age=_missing_age, missing_gender=_missing_gender, turn=_early_turns)
        return {
            "messages": [AIMessage(content=early_q)],
            "detected_language": detected_language,
            "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
            "is_emergency": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "intake_tracker": tracker.to_dict(),
            "intake_data": None,
            "intake_complete": False,
            "confirmed_facts": confirmed_facts,
            "turn_count": turn_count_early,
        }

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

    # Rebuild system prompt with UPDATED facts (after this turn's extraction)
    mandatory_text = build_mandatory_injection(confirmed_facts, gender, complaint_category)
    system_prompt = (
        DOCTOR_SYSTEM_PROMPT
        .replace("{language}", lang_label)
        .replace("{mandatory_injection}", mandatory_text)
        .replace("{complaint_specific_injection}", complaint_probe)
    )

    # Inject confirmed facts so LLM knows exactly what's collected — do NOT re-ask these
    _SKIP_KEYS = {"complaint_category", "chest_pain_flag", "functional_status"}
    _known = {k: v for k, v in confirmed_facts.items() if v and k not in _SKIP_KEYS}
    if _known:
        facts_lines = "\n".join(f"  ✓ {k}: {v}" for k, v in _known.items())
        system_prompt += f"\n\n=== ĐÃ XÁC NHẬN — KHÔNG HỎI LẠI ===\n{facts_lines}"

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

    # === Step 12: Code completion gate (2-phase: summary → confirm) ===
    intake_complete = False
    awaiting_confirmation = state.get("awaiting_confirmation", False)

    # Phase 2: BN is confirming/rejecting the summary we showed last turn
    if awaiting_confirmation:
        _bn_confirmed = bool(re.match(
            r'^(ok|okay|ổn|đúng|đúng rồi|chính xác|xác nhận|đồng ý|duyệt|yes|yep|ừ|uh|được|vậy đó|đúng vậy)\b',
            clean_text.strip(), re.IGNORECASE | re.UNICODE
        ))
        _bn_wants_change = bool(re.match(
            r'^(sai|không đúng|sửa|chưa đúng|thiếu|bổ sung|thêm|chỉnh|chưa|không phải)',
            clean_text.strip(), re.IGNORECASE | re.UNICODE
        ))
        if _bn_confirmed:
            logger.info("intake_v4.summary_confirmed", case_id=case_id)
            intake_complete = True
            patient_response = "Cảm ơn bạn. Hồ sơ đã sẵn sàng, bác sĩ sẽ xem xét và liên hệ sớm nhất."
        elif _bn_wants_change:
            # BN wants to correct → back to intake, ask what to change
            patient_response = "Bạn muốn sửa hoặc bổ sung thông tin nào?"
            awaiting_confirmation = False
        else:
            # Ambiguous → treat as confirm if they said something short/neutral
            if len(clean_text.strip()) <= 10:
                intake_complete = True
                patient_response = "Cảm ơn bạn. Hồ sơ đã sẵn sàng, bác sĩ sẽ xem xét và liên hệ sớm nhất."
            else:
                # Long text → treat as additional info, re-extract and continue
                awaiting_confirmation = False
    else:
        # Phase 1: Check if ready to show summary
        _can_complete = _validate_completion(confirmed_facts, complaint_category, turn_count)

        if llm_wants_done and not _can_complete:
            missing = _get_hard_missing(confirmed_facts)
            logger.info("intake_v4.premature_done_blocked", case_id=case_id, missing=missing)
            patient_response = _ask_next_missing(confirmed_facts, complaint_category)

        elif _can_complete:
            # Ready → show summary and ask for confirmation (don't mark complete yet)
            logger.info("intake_v4.showing_summary_for_confirmation", case_id=case_id)
            tracker_tmp = IntakeTracker(data=state.get("intake_tracker"))
            _sync_tracker_from_facts(tracker_tmp, confirmed_facts)
            summary = _generate_summary_v4(tracker_tmp, confirmed_facts)
            patient_response = summary + "\n\n**Thông tin trên đã chính xác chưa?** Nhắn \"ok\" để xác nhận, hoặc cho tôi biết cần sửa gì."
            awaiting_confirmation = True

        # Anti-loop: ANY response mentioning "bổ sung"/"thêm gì" → always redirect
        # This catches LLM asking "bổ sung?" regardless of completion status
        _is_llm_asking_supplement = bool(re.search(
            r'bổ sung|thêm (?:gì|điều gì)|có gì thêm|muốn (?:thêm|nói thêm)', patient_response, re.IGNORECASE
        ))
        if _is_llm_asking_supplement:
            next_q = _ask_next_missing(confirmed_facts, complaint_category)
            if "bổ sung" not in next_q:
                patient_response = next_q
                logger.info("intake_v4.supplement_replaced_with_missing",
                            case_id=case_id, next=next_q)
            else:
                # No more specific fields → show summary anyway
                logger.info("intake_v4.no_more_fields_force_summary", case_id=case_id)
                tracker_tmp = IntakeTracker(data=state.get("intake_tracker"))
                _sync_tracker_from_facts(tracker_tmp, confirmed_facts)
                summary = _generate_summary_v4(tracker_tmp, confirmed_facts)
                patient_response = summary + "\n\n**Thông tin trên đã chính xác chưa?** Nhắn \"ok\" để xác nhận, hoặc cho tôi biết cần sửa gì."
                awaiting_confirmation = True


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

    return {
        "messages": [AIMessage(content=patient_response)],
        "detected_language": detected_language,
        "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
        "is_emergency": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "intake_tracker": tracker.to_dict(),
        "intake_data": tracker.to_intake_data() if intake_complete else None,
        "intake_complete": intake_complete,
        "awaiting_confirmation": awaiting_confirmation,
        "confirmed_facts": confirmed_facts,
        "turn_count": turn_count,
    }


_HARD_REQUIRED_FIELDS = [
    ("age",        "Bạn bao nhiêu tuổi?"),
    ("gender",     "Bạn là nam hay nữ?"),
    ("severity",   "Trên thang 1-10, cơn đau mấy điểm? Có ảnh hưởng sinh hoạt không?"),
    ("pmh",        "Bạn có bệnh nền gì không — như tiểu đường, huyết áp, hay bệnh tim?"),
    ("medications","Bạn đang dùng thuốc gì không?"),
    ("allergies",  "Bạn có dị ứng với thuốc hay thức ăn gì không?"),
]

_CATEGORY_NEXT = {
    "abdominal_pain": [
        ("fever",   "Bạn có bị sốt không?"),
        ("nausea",  "Bạn có buồn nôn hay nôn không?"),
        ("bowel",   "Đại tiện có thay đổi gì không?"),
        ("urinary", "Tiểu tiện có bất thường không?"),
    ],
    "chest_pain": [
        ("radiation",   "Đau có lan lên vai hay cánh tay không?"),
        ("dyspnea",     "Bạn có khó thở không?"),
        ("diaphoresis", "Bạn có đổ mồ hôi lạnh không?"),
    ],
}


def _get_hard_missing(facts: dict) -> list[str]:
    return [f for f, _ in _HARD_REQUIRED_FIELDS if not facts.get(f)]


def _ask_next_missing(facts: dict, category: str) -> str:
    """Return the next question for the highest-priority missing field."""
    # Hard required first
    for field, question in _HARD_REQUIRED_FIELDS:
        if not facts.get(field):
            return question
    # Category-specific
    for field, question in _CATEGORY_NEXT.get(category, []):
        if not facts.get(field):
            return question
    # LMP for female abdominal
    if facts.get("gender") == "female" and category in ("abdominal_pain", "general"):
        if not facts.get("lmp"):
            return "Kinh nguyệt gần nhất của bạn khi nào?"
    return "Bạn có muốn bổ sung thêm điều gì không?"


def _validate_completion(facts: dict, category: str, turn_count: int) -> bool:
    """Code-enforced completion gate — hard stop on critical fields."""
    if turn_count < MIN_TURNS_FOR_COMPLETION:
        return False

    # === HARD BLOCK: these fields MUST be present, no exceptions ===
    hard_required = {"age", "gender", "cc", "onset", "location", "character", "severity",
                     "pmh", "medications", "allergies"}
    for field in hard_required:
        if not facts.get(field):
            return False  # Block no matter what LLM says

    # === Category-specific required fields ===
    cat_required = COMPLETION_REQUIRED_BY_CATEGORY.get(category, set())
    if facts.get("gender") == "female" and category in ("abdominal_pain", "general"):
        cat_required = cat_required | {"lmp"}

    missing_cat = [f for f in cat_required if not facts.get(f)]
    # Allow max 1 missing category field (patient may have declined)
    return len(missing_cat) <= 1


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
