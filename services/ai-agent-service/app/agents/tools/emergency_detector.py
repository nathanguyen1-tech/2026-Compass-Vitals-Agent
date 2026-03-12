"""Emergency Detector — Phát hiện triệu chứng khẩn cấp trong text.

Tier 1: Keyword-based detection (original, fast, backward compatible).
Tier 1b: Numeric vital sign detection (temperature, heart rate, etc.).
Tier 2: Context-aware red flag detection based on complaint category.
"""

from __future__ import annotations

import re

from app.agents.prompts.complaint_protocols import PROTOCOLS, get_complaint_protocol


# === Tier 1b: Numeric vital sign patterns ===

# Temperature patterns — matches values like "42°C", "42 do C", "42 do", "104°F", "104 F"
# Vietnamese: "42 do", "42 do C", "42°C", "sot 42", "nhiet do 42"
_TEMP_CELSIUS_PATTERN = re.compile(
    r"(\d{2,3}(?:[.,]\d{1,2})?)\s*(?:°\s*C|do\s*C|do\s*c|độ\s*C|độ\s*c|degrees?\s*C|degrees?\s*c)",
    re.IGNORECASE,
)
# Standalone "XX do" (Vietnamese for degrees) — only match 38-45 range to avoid false positives
_TEMP_VIET_PATTERN = re.compile(
    r"(\d{2}(?:[.,]\d{1,2})?)\s*(?:°|do|độ)(?:\s|$|[,.])",
    re.IGNORECASE,
)
_TEMP_FAHRENHEIT_PATTERN = re.compile(
    r"(\d{2,3}(?:[.,]\d{1,2})?)\s*(?:°\s*F|do\s*F|degrees?\s*F)",
    re.IGNORECASE,
)
# "sot 42" / "nhiet do 42" / "fever 104" pattern
_TEMP_CONTEXT_PATTERN = re.compile(
    r"(?:sốt|sot|nhiet do|nhiệt độ|fever|temperature|temp)\s+(\d{2,3}(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)

# Thresholds
TEMP_CELSIUS_EMERGENCY = 40.0  # ≥40°C = hyperpyrexia, life-threatening
TEMP_FAHRENHEIT_EMERGENCY = 104.0  # ≥104°F equivalent


def _parse_number(s: str) -> float:
    """Parse a number string that may use comma as decimal separator."""
    return float(s.replace(",", "."))


def detect_high_temperature(text: str) -> dict | None:
    """Detect dangerously high temperature values in text.

    Returns dict with temperature info if emergency threshold met, else None.
    Thresholds: ≥40°C (104°F) — hyperpyrexia requiring immediate medical attention.
    """
    # Check explicit Celsius patterns
    for pattern in [_TEMP_CELSIUS_PATTERN, _TEMP_CONTEXT_PATTERN]:
        for match in pattern.finditer(text):
            try:
                temp = _parse_number(match.group(1))
                if TEMP_CELSIUS_EMERGENCY <= temp <= 50:  # Upper bound sanity check
                    return {
                        "value": temp,
                        "unit": "C",
                        "matched_text": match.group(0).strip(),
                    }
            except (ValueError, IndexError):
                continue

    # Check Vietnamese "XX do" pattern (only if in fever range 38-45)
    for match in _TEMP_VIET_PATTERN.finditer(text):
        try:
            temp = _parse_number(match.group(1))
            if TEMP_CELSIUS_EMERGENCY <= temp <= 45:
                return {
                    "value": temp,
                    "unit": "C",
                    "matched_text": match.group(0).strip(),
                }
        except (ValueError, IndexError):
            continue

    # Check Fahrenheit
    for match in _TEMP_FAHRENHEIT_PATTERN.finditer(text):
        try:
            temp = _parse_number(match.group(1))
            if TEMP_FAHRENHEIT_EMERGENCY <= temp <= 115:
                return {
                    "value": temp,
                    "unit": "F",
                    "matched_text": match.group(0).strip(),
                }
        except (ValueError, IndexError):
            continue

    return None


# === INSTANT emergency keywords (life-threatening, no confirmation needed) ===
# Only conditions where delaying 1 minute = risk of death.
# Everything else is handled by the LLM with 2-question confirmation.

EMERGENCY_KEYWORDS_INSTANT_VI = [
    # Loss of consciousness / seizure
    "mất ý thức", "mat y thuc",  # ASCII-folded
    "bất tỉnh", "bat tinh",  # ASCII-folded
    "hôn mê", "hon me",  # ASCII-folded
    "co giật", "co giat",  # ASCII-folded
    # Suicide / self-harm
    "tự tử", "tu tu",  # ASCII-folded
    "muốn chết", "muon chet",  # ASCII-folded
    "không muốn sống", "khong muon song",  # ASCII-folded
    # GI hemorrhage
    "ói ra máu", "oi ra mau",  # ASCII-folded
    "nôn ra máu", "non ra mau",  # ASCII-folded
    "đi cầu ra máu", "di cau ra mau",  # ASCII-folded
    # Overdose
    "uống thuốc quá liều", "uong thuoc qua lieu",  # ASCII-folded
    # Critical trauma
    "bị bắn", "bi ban",  # shot/gunshot
    "đuối nước", "duoi nuoc",  # drowning
    "bị nghẹn", "bi nghen",  # choking
]

EMERGENCY_KEYWORDS_INSTANT_EN = [
    # Loss of consciousness / seizure
    "unconscious", "loss of consciousness", "seizure",
    # Suicide / self-harm
    "want to die", "kill myself", "suicide",
    # GI hemorrhage
    "vomiting blood", "bloody stool", "coughing blood",
    # Anaphylaxis
    "anaphylaxis",
    # Overdose
    "overdose",
    # Critical trauma
    "gunshot", "shot in the",
    "choking", "can't swallow",
    "near drowning",
]


def detect_instant_emergency(text: str) -> bool:
    """Check for INSTANT-only emergencies (small keyword set + vital signs).

    These are life-threatening conditions where delaying even 1 minute is dangerous.
    Everything else (chest pain, difficulty breathing, etc.) goes through LLM
    with 2-question confirmation flow.

    Negation-aware: "I do NOT want to die" won't trigger.
    Vital signs (temperature ≥40°C) always trigger regardless of negation.
    """
    text_lower = text.lower()

    for keyword in EMERGENCY_KEYWORDS_INSTANT_VI + EMERGENCY_KEYWORDS_INSTANT_EN:
        kw_lower = keyword.lower()
        if kw_lower not in text_lower:
            continue
        if not _is_negated(text_lower, kw_lower):
            return True

    # Vital signs always trigger (temperature ≥40°C / ≥104°F)
    if detect_high_temperature(text) is not None:
        return True

    return False


# === Tier 1: Keyword-based detection (backward compatible) ===

EMERGENCY_KEYWORDS_VI = [
    # Cardiac / Respiratory
    "đau ngực", "dau nguc",  # ASCII-folded
    "khó thở", "kho tho",  # ASCII-folded
    "không thở được", "khong tho duoc",  # ASCII-folded
    "tê nửa người", "te nua nguoi",  # ASCII-folded
    "đau ngực trái", "dau nguc trai",  # ASCII-folded
    "đau lan ra cánh tay", "dau lan ra canh tay",  # ASCII-folded
    # Neurological
    "đột ngột yếu nửa người", "dot ngot yeu nua nguoi",  # ASCII-folded
    "méo miệng", "meo mieng",  # ASCII-folded
    "nói ngọng đột ngột", "noi ngong dot ngot",  # ASCII-folded
    "mất thị lực đột ngột", "mat thi luc dot ngot",  # ASCII-folded
    # Loss of consciousness
    "mất ý thức", "mat y thuc",  # ASCII-folded
    "bất tỉnh", "bat tinh",  # ASCII-folded
    "ngất", "ngat",  # ASCII-folded
    "ngất xỉu", "ngat xiu",  # ASCII-folded
    "hôn mê", "hon me",  # ASCII-folded
    # Bleeding / seizure
    "chảy máu nhiều", "chay mau nhieu",  # ASCII-folded
    "co giật", "co giat",  # ASCII-folded
    # Suicide / self-harm
    "tự tử", "tu tu",  # ASCII-folded
    "muốn chết", "muon chet",  # ASCII-folded
    "không muốn sống", "khong muon song",  # ASCII-folded
    # GI hemorrhage
    "ói ra máu", "oi ra mau",  # ASCII-folded
    "nôn ra máu", "non ra mau",  # ASCII-folded
    "đi cầu ra máu", "di cau ra mau",  # ASCII-folded
    # Anaphylaxis
    "sưng họng", "sung hong",  # ASCII-folded
    "phù mặt", "phu mat",  # ASCII-folded
    # Overdose
    "uống thuốc quá liều", "uong thuoc qua lieu",  # ASCII-folded
    # Trauma / Falls / Accidents
    "rơi từ", "roi tu",  # fell from (rơi từ lầu 2, rơi từ tầng 3...)
    "ngã từ", "nga tu",  # fell from (ngã từ cầu thang...)
    "rơi xuống", "roi xuong",  # fell down
    "ngã cầu thang", "nga cau thang",  # fell down stairs
    "ngã từ trên cao", "nga tu tren cao",  # fell from height
    "tai nạn xe", "tai nan xe",  # vehicle accident
    "tai nạn giao thông", "tai nan giao thong",  # traffic accident
    "bị xe đâm", "bi xe dam",  # hit by vehicle
    "bị đâm", "bi dam",  # stabbed
    "bị bắn", "bi ban",  # shot
    "chấn thương đầu", "chan thuong dau",  # head injury
    "gãy xương", "gay xuong",  # broken bone
    "bị điện giật", "bi dien giat",  # electric shock
    "đuối nước", "duoi nuoc",  # drowning
    "bị bỏng", "bi bong",  # burned
    "bị nghẹn", "bi nghen",  # choking
    "bị kẹt", "bi ket",  # trapped/crushed
]

EMERGENCY_KEYWORDS_EN = [
    "chest pain", "difficulty breathing", "can't breathe", "numbness",
    "unconscious", "severe bleeding", "seizure", "stroke signs",
    "sudden weakness", "facial drooping", "slurred speech",
    "loss of consciousness", "fainting", "heart attack",
    # Suicide / self-harm
    "want to die", "kill myself", "suicide",
    # GI hemorrhage
    "vomiting blood", "bloody stool", "coughing blood",
    # Anaphylaxis
    "throat swelling", "throat closing", "anaphylaxis",
    # Overdose
    "overdose",
    # Trauma / injury
    "fell from", "fall from", "fallen from",
    "car accident", "motorcycle accident", "traffic accident",
    "hit by a car", "hit by car",
    "stabbed", "gunshot", "shot in",
    "head injury", "head trauma",
    "broken bone", "bone sticking out",
    "electric shock", "electrocuted",
    "near drowning", "almost drowned",
    "choking",
    "severe burn", "burned",
]

# === Negation-aware detection ===

_NEGATION_PREFIXES_EN = [
    "no ", "not ", "don't have ", "do not have ",
    "without ", "deny ", "denies ", "negative for ",
]
_NEGATION_PREFIXES_VI = [
    "khong ", "không ", "khong bi ", "không bị ",
    "khong co ", "không có ", "chua bi ", "chưa bị ",
]


def detect_emergency(text: str) -> bool:
    """Check if text contains emergency symptoms. Returns True if emergency detected.

    Checks both keyword-based patterns AND numeric vital signs (e.g., temperature ≥40°C).
    """
    text_lower = text.lower()
    for keyword in EMERGENCY_KEYWORDS_VI + EMERGENCY_KEYWORDS_EN:
        if keyword.lower() in text_lower:
            return True

    # Check for dangerously high temperature
    if detect_high_temperature(text) is not None:
        return True

    return False


def get_emergency_keywords_found(text: str) -> list[str]:
    """Return list of emergency keywords found in text."""
    text_lower = text.lower()
    found = []
    for keyword in EMERGENCY_KEYWORDS_VI + EMERGENCY_KEYWORDS_EN:
        if keyword.lower() in text_lower:
            found.append(keyword)

    # Check temperature
    temp_info = detect_high_temperature(text)
    if temp_info:
        found.append(f"high_temperature:{temp_info['value']}°{temp_info['unit']}")

    return found


def _is_negated(text_lower: str, keyword_lower: str) -> bool:
    """Check if a keyword match is preceded by a negation prefix."""
    kw_pos = text_lower.find(keyword_lower)
    if kw_pos < 0:
        return False

    prefix_text = text_lower[:kw_pos]

    for neg in _NEGATION_PREFIXES_EN + _NEGATION_PREFIXES_VI:
        if prefix_text.endswith(neg):
            return True
    return False


def detect_emergency_with_negation(text: str) -> bool:
    """Enhanced emergency detection that respects negation.

    Returns False for patterns like "I do NOT have chest pain" or
    "toi khong bi dau nguc". Falls back to standard detection for
    non-negated matches.

    Vital signs (temperature) are never negated — "I don't have 42°C"
    still triggers because the value itself is dangerous.
    """
    text_lower = text.lower()

    for keyword in EMERGENCY_KEYWORDS_VI + EMERGENCY_KEYWORDS_EN:
        kw_lower = keyword.lower()
        if kw_lower not in text_lower:
            continue

        if not _is_negated(text_lower, kw_lower):
            return True

    # Vital signs check (not affected by negation)
    if detect_high_temperature(text) is not None:
        return True

    return False


# === Tier 2: Context-aware red flag detection ===

# Cross-complaint red flag combinations (not tied to a single protocol)
CROSS_COMPLAINT_RED_FLAGS = [
    {
        "id": "stroke_signs",
        "pattern_en": "FAST stroke signs: face droop, arm weakness, speech difficulty",
        "pattern_vi": "Dau hieu dot quy FAST: meo mieng, yeu tay, noi kho",
        "action": "911",
        "message_en": "These could be signs of a stroke. Please call 911 immediately.",
        "message_vi": "Day co the la dau hieu dot quy. Vui long goi 911 ngay lap tuc.",
        "keyword_groups": [
            ["face droop", "facial drooping", "drooping", "meo mieng"],
            ["arm weakness", "one side weak", "yeu mot ben", "yeu nua nguoi"],
            ["slurred speech", "speech difficulty", "noi ngong", "noi kho"],
        ],
        "min_groups": 1,  # Any 1 group match triggers
    },
    {
        "id": "anaphylaxis",
        "pattern_en": "Throat swelling / hives + difficulty breathing after exposure",
        "pattern_vi": "Sung hong / noi me day + kho tho sau khi tiep xuc",
        "action": "911",
        "message_en": "These symptoms could be anaphylaxis. Please call 911 and use EpiPen if available.",
        "message_vi": "Nhung trieu chung nay co the la soc phan ve. Vui long goi 911 va dung EpiPen neu co.",
        "keyword_groups": [
            ["throat swelling", "throat closing", "throat is closing", "sung hong", "nghet tho",
             "noi me day", "nổi mề đay", "hives", "swollen face", "phu mat", "phù mặt"],
            ["can't breathe", "difficulty breathing", "kho tho", "cannot breathe", "khó thở"],
        ],
        "min_groups": 2,  # Both groups must match
    },
    {
        "id": "alcohol_withdrawal",
        "pattern_en": "Alcohol withdrawal: tremor + confusion + seizure",
        "pattern_vi": "Cai ruou: run + lon xon + co giat",
        "action": "ER",
        "message_en": "Alcohol withdrawal can be dangerous. Please go to the nearest ER immediately.",
        "message_vi": "Cai ruou co the nguy hiem. Vui long den phong cap cuu gan nhat ngay.",
        "keyword_groups": [
            ["withdrawal", "cai ruou", "bo ruou"],
            ["tremor", "shaking", "run", "run tay"],
        ],
        "min_groups": 2,
    },
]


def detect_contextual_red_flags(
    text: str,
    complaint_category: str | None = None,
    conversation_history: list[str] | None = None,
) -> list[dict]:
    """Detect red flags based on complaint category context.

    Checks both complaint-specific red flags and cross-complaint patterns.
    Uses multi-keyword group matching for higher accuracy.

    Args:
        text: Current patient message text.
        complaint_category: Active complaint protocol ID (e.g., "chest_pain").
        conversation_history: Previous messages for context (optional).

    Returns:
        List of detected red flags, each with:
        - id: Red flag identifier
        - action: "911" | "ER" | "urgent_review"
        - message_en: English emergency message
        - message_vi: Vietnamese emergency message
        - keywords_found: Keywords that triggered detection
    """
    text_lower = text.lower()

    # Combine with recent conversation for context
    full_context = text_lower
    if conversation_history:
        recent = " ".join(conversation_history[-4:]).lower()  # Last 4 messages
        full_context = recent + " " + text_lower

    detected: list[dict] = []

    # Check complaint-specific red flags
    if complaint_category:
        protocol = get_complaint_protocol(complaint_category)
        for red_flag in protocol.get("red_flags", []):
            keywords_found = []
            for kw in red_flag.get("keywords", []):
                if kw.lower() in full_context:
                    keywords_found.append(kw)

            if keywords_found:
                detected.append({
                    "id": red_flag["id"],
                    "action": red_flag["action"],
                    "message_en": red_flag["message_en"],
                    "message_vi": red_flag["message_vi"],
                    "keywords_found": keywords_found,
                })

    # Check cross-complaint red flags
    for cross_flag in CROSS_COMPLAINT_RED_FLAGS:
        groups_matched = 0
        all_keywords_found = []

        for group in cross_flag["keyword_groups"]:
            group_matched = False
            for kw in group:
                if kw.lower() in full_context:
                    all_keywords_found.append(kw)
                    group_matched = True
            if group_matched:
                groups_matched += 1

        if groups_matched >= cross_flag["min_groups"]:
            detected.append({
                "id": cross_flag["id"],
                "action": cross_flag["action"],
                "message_en": cross_flag["message_en"],
                "message_vi": cross_flag["message_vi"],
                "keywords_found": all_keywords_found,
            })

    # Sort by severity: 911 first, then ER, then urgent_review
    severity_order = {"911": 0, "ER": 1, "urgent_review": 2}
    detected.sort(key=lambda f: severity_order.get(f["action"], 3))

    return detected


