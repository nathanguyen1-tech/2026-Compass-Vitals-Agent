"""Intake Facts Extractor V4.

Two purposes:
1. Per-turn: lightweight keyword/pattern extraction for code-side fact tracking
2. End-of-session: full LLM extraction pass → structured IntakeScreeningPayload
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Literal

# ─── Per-turn keyword extraction ──────────────────────────────────────────────

# Patterns to detect confirmed facts from patient text (safety-by-code)
_NEGATIVE_WORDS = [
    "không có", "không bị", "không sốt", "không buồn nôn", "không nôn",
    "không tiêu chảy", "không táo bón", "không tiểu buốt", "không khó thở",
    "không hồi hộp", "bình thường", "bình thường hết", "ổn hết", "không gì hết",
    "không có gì", "không thấy gì", "không dùng thuốc", "không uống thuốc",
    "không hút thuốc", "không uống rượu", "không dị ứng", "không bệnh nền",
    "khỏe mạnh", "no", "none", "normal", "negative",
]

_PMH_NEGATIVES    = ["không có bệnh nền", "không bệnh", "khỏe mạnh", "no medical history"]
_MEDS_NEGATIVES   = ["không dùng thuốc", "không uống thuốc", "no medication"]
_ALLERGY_NEGATIVES= ["không dị ứng", "no allergy", "no allergies"]
_SMOKE_NEGATIVES  = ["không hút thuốc", "không hút", "chưa hút", "no smoking"]
_ALCOHOL_NEGATIVES= ["không uống rượu", "không uống bia", "không uống rượu bia", "no alcohol"]

_GENDER_FEMALE = ["nữ", "female", "phụ nữ", "con gái", "bà", "cô", "chị", "em gái"]
_GENDER_MALE   = ["nam", "male", "đàn ông", "con trai", "ông", "chú", "anh", "em trai"]

_FEVER_POSITIVE   = ["sốt", "nóng người", "nóng sốt", "fever"]
_NAUSEA_POSITIVE  = ["buồn nôn", "nôn", "muốn ói", "ói"]
_ANOREXIA_POSITIVE= ["chán ăn", "mất cảm giác ngon", "không muốn ăn", "không ăn được"]
_WEIGHT_LOSS      = ["sụt cân", "gầy đi", "giảm cân không cố ý", "sút cân"]
_NIGHT_SWEATS     = ["đổ mồ hôi đêm", "mồ hôi đêm", "night sweats"]
_DIAPHORESIS      = ["đổ mồ hôi lạnh", "mồ hôi lạnh", "vã mồ hôi", "toát mồ hôi"]
_DYSPNEA_POSITIVE = ["khó thở", "hụt hơi", "thở không ra", "shortness of breath"]
_CHEST_PAIN       = ["đau ngực", "tức ngực", "nặng ngực", "chest pain", "chest tightness"]
_SYNCOPE          = ["ngất", "xỉu", "mất ý thức", "té xỉu", "blackout", "syncope"]
_WORST_HEADACHE   = ["chưa bao giờ đau như vậy", "đau đầu tệ nhất", "đau đầu dữ nhất",
                     "worst headache", "thunderclap"]
_RADIATION_ARM    = ["lan cánh tay", "lan tay trái", "lan lên vai", "lan hàm",
                     "radiation to arm", "left arm pain"]
_VAGINAL_BLEEDING = ["ra máu âm đạo", "xuất huyết âm đạo", "chảy máu âm đạo",
                     "vaginal bleeding", "ra huyết"]
_NECK_STIFFNESS   = ["cứng cổ", "neck stiffness", "cổ cứng"]

# ─── Red flag combo detection ─────────────────────────────────────────────────

RED_FLAG_COMBOS = [
    # (set of flags needed, min count to trigger, name)
    # NOTE: chest_pain alone is NOT emergency — needs combo
    ({"chest_pain", "diaphoresis"}, 2, "ACS_combo"),
    ({"chest_pain", "dyspnea", "diaphoresis"}, 2, "ACS_PE_combo"),
    ({"chest_pain", "radiation_arm"}, 2, "ACS_radiation_combo"),
    ({"chest_pain", "syncope"}, 2, "cardiac_syncope_chest"),
    ({"worst_headache_ever"}, 1, "SAH_thunderclap"),
    ({"headache", "neck_stiffness", "fever"}, 3, "meningitis_combo"),
    ({"syncope", "chest_pain"}, 2, "cardiac_syncope"),
    ({"pelvic_pain", "vaginal_bleeding"}, 2, "ectopic_combo"),
    ({"back_pain", "leg_weakness"}, 2, "cauda_equina"),
    ({"hemoptysis"}, 1, "hemoptysis_emergency"),
]


def extract_facts_from_text(text: str, existing_facts: dict) -> dict:
    """Extract and update facts from patient message text.
    Returns updated facts dict.
    """
    facts = dict(existing_facts)
    t = text.lower()

    # Gender — check female first (more specific), then male
    # Also handle "26 tuổi nữ" pattern (number + tuổi + gender word)
    if not facts.get("gender"):
        # Female keywords
        if any(w in t for w in _GENDER_FEMALE):
            facts["gender"] = "female"
        # Male keywords — only if no female keyword found
        elif any(w in t for w in _GENDER_MALE):
            facts["gender"] = "male"

    # Age — extract number + "tuổi", or standalone plausible age number
    if not facts.get("age"):
        # Pattern 1: "26 tuổi" / "years old"
        m = re.search(r'(\d{1,3})\s*(?:tuổi|years?\s*old)', t)
        if not m:
            # Pattern 2: "tôi 30" / "mình 25" / bare number if only digits in message
            m = re.search(r'(?:tôi|mình|em|con|anh|chị|ông|bà|cô|chú)\s+(\d{1,3})\b', t)
        if not m:
            # Pattern 3: standalone number that's plausible age (message is very short)
            stripped = text.strip()
            if re.fullmatch(r'\d{1,3}', stripped):
                age_val = int(stripped)
                if 1 <= age_val <= 120:
                    facts["age"] = str(age_val)
                    m = None  # already set
        if m:
            age = int(m.group(1))
            if 1 <= age <= 120:
                facts["age"] = str(age)

    # Negative/normal answers
    if any(p in t for p in _PMH_NEGATIVES):      facts["pmh"] = facts.get("pmh") or "none"
    if any(p in t for p in _MEDS_NEGATIVES):     facts["medications"] = facts.get("medications") or "none"
    if any(p in t for p in _ALLERGY_NEGATIVES):  facts["allergies"] = facts.get("allergies") or "none"
    if any(p in t for p in _SMOKE_NEGATIVES):
        sh = facts.get("social_history", "") or ""
        if "không hút" not in sh:
            facts["social_history"] = (sh + "; không hút thuốc").strip("; ")
    if any(p in t for p in _ALCOHOL_NEGATIVES):
        sh = facts.get("social_history", "") or ""
        if "không uống" not in sh:
            facts["social_history"] = (sh + "; không uống rượu bia").strip("; ")

    # Positive symptom extraction
    _fever_negated = any(p in t for p in ["không sốt", "không bị sốt", "no fever", "chưa sốt"])
    if any(p in t for p in _FEVER_POSITIVE) and not _fever_negated and not facts.get("fever"):
        facts["fever"] = "yes"
    elif _fever_negated and not facts.get("fever"):
        facts["fever"] = "no"
    if any(p in t for p in _NAUSEA_POSITIVE)   and not facts.get("nausea"):
        facts["nausea"] = "yes"
    if any(p in t for p in _ANOREXIA_POSITIVE) and not facts.get("anorexia"):
        facts["anorexia"] = "yes"
    if any(p in t for p in _WEIGHT_LOSS)       and not facts.get("weight_loss"):
        facts["weight_loss"] = "yes"
    if any(p in t for p in _NIGHT_SWEATS)      and not facts.get("night_sweats"):
        facts["night_sweats"] = "yes"
    _negated = lambda keywords: any(neg + " " + kw in t for neg in ["không", "no ", "not ", "chưa"] for kw in keywords)
    if any(p in t for p in _DIAPHORESIS) and not _negated(["mồ hôi", "sweating"]) and not facts.get("diaphoresis"):
        facts["diaphoresis"] = "yes"
    if any(p in t for p in _DYSPNEA_POSITIVE) and not _negated(["khó thở", "shortness", "hụt hơi"]) and not facts.get("dyspnea"):
        facts["dyspnea"] = "yes"
    if any(p in t for p in _CHEST_PAIN)        and not facts.get("chest_pain_flag"):
        facts["chest_pain_flag"] = "yes"
    if any(p in t for p in _SYNCOPE)           and not facts.get("syncope"):
        facts["syncope"] = "yes"
    if any(p in t for p in _WORST_HEADACHE)    and not facts.get("worst_headache_ever"):
        facts["worst_headache_ever"] = "yes"
    if any(p in t for p in _RADIATION_ARM) and not _negated(["lan", "radiation"]) and not facts.get("radiation_arm"):
        facts["radiation_arm"] = "yes"
    if any(p in t for p in _VAGINAL_BLEEDING)  and not facts.get("vaginal_bleeding"):
        facts["vaginal_bleeding"] = "yes"
    if any(p in t for p in _NECK_STIFFNESS)    and not facts.get("neck_stiffness"):
        facts["neck_stiffness"] = "yes"

    # CC extraction — chief complaint
    if not facts.get("cc"):
        _cc_patterns = [
            (r'(?:bị|có)\s+(đau\s+\w+)', 'abdominal_pain'),
            (r'(đau\s+bụng)', 'abdominal_pain'),
            (r'(đau\s+ngực|tức\s+ngực)', 'chest_pain'),
            (r'(đau\s+đầu)', 'headache'),
            (r'(khó\s+thở|hụt\s+hơi)', 'respiratory'),
            (r'(tiểu\s+buốt|tiểu\s+rắt)', 'urinary'),
        ]
        for pat, cat in _cc_patterns:
            m_cc = re.search(pat, t)
            if m_cc:
                facts["cc"] = m_cc.group(1)
                if not facts.get("complaint_category"):
                    facts["complaint_category"] = cat
                break

    # Onset extraction
    if not facts.get("onset"):
        _onset_pats = [
            r'(?:bắt\s+đầu|khởi\s+phát|bị)\s+(?:từ\s+)?(\d+\s+(?:tiếng|giờ|ngày|tuần|tháng)\s+(?:trước|qua|nay))',
            r'(?:đau|bị)\s+(?:từ\s+)?(\w+\s+(?:hôm\s+qua|hôm\s+nay|sáng|tối|trưa))',
            r'(\d+\s+(?:tiếng|giờ|ngày|tuần)\s+trước)',
            r'(?:đau\s+)(đột\s+ngột|từ\s+từ|dần\s+dần)',
        ]
        for pat in _onset_pats:
            m_onset = re.search(pat, t)
            if m_onset:
                facts["onset"] = m_onset.group(1)
                break
        # Also capture suddenness
        if "đột ngột" in t and not facts.get("onset"):
            facts["onset"] = "đột ngột"
        elif "đột ngột" in t and facts.get("onset") and "đột ngột" not in facts["onset"]:
            facts["onset"] = facts["onset"] + " — đột ngột"

    # Location extraction (abdominal)
    if not facts.get("location"):
        _loc_map = [
            (["hố chậu phải", "rlq", "right lower"], "hố chậu phải"),
            (["hố chậu trái", "llq", "left lower"], "hố chậu trái"),
            (["thượng vị", "trên rốn", "epigastric", "dạ dày"], "thượng vị/trên rốn"),
            (["quanh rốn", "quanh rốn", "periumbilical"], "quanh rốn"),
            (["dưới rốn", "hạ vị", "hypogastric", "below navel"], "dưới rốn"),
            (["hông phải", "sườn phải", "right flank"], "hông sườn phải"),
            (["hông trái", "sườn trái", "left flank"], "hông sườn trái"),
            (["toàn bụng", "khắp bụng"], "toàn bụng"),
        ]
        for keywords, label in _loc_map:
            if any(kw in t for kw in keywords):
                facts["location"] = label
                break

    # Character extraction
    if not facts.get("character"):
        _char_map = [
            (["nhói", "nhói từng cơn", "stabbing", "sharp"], "nhói từng cơn"),
            (["âm ỉ", "dull", "aching"], "âm ỉ"),
            (["co thắt", "cramping", "spasm"], "co thắt"),
            (["bỏng rát", "burning"], "bỏng rát"),
            (["tức", "pressure", "nặng nề"], "tức/nặng"),
        ]
        for keywords, label in _char_map:
            if any(kw in t for kw in keywords):
                facts["character"] = label
                break

    # Radiation
    if not facts.get("radiation"):
        if any(p in t for p in ["không lan", "không phóng", "does not radiate", "không lan ra"]):
            facts["radiation"] = "không lan"

    # Bowel positive
    if not facts.get("bowel"):
        if any(p in t for p in ["tiêu chảy", "diarrhea", "táo bón", "constipation", "phân có máu", "blood in stool"]):
            facts["bowel"] = "abnormal - " + ("tiêu chảy" if "tiêu chảy" in t else "thay đổi")

    # Bowel/urinary negative
    _bowel_normal = ["đại tiện bình thường", "đại tiện ổn", "không tiêu chảy", "không táo bón", "đại tiện không thay đổi"]
    _urinary_normal = ["tiểu bình thường", "tiểu tiện bình thường", "không tiểu buốt", "không tiểu rắt", "không đau rát"]
    _urinary_negative = ["không tiểu buốt", "không bất thường", "bình thường"]
    if any(p in t for p in _bowel_normal)    and not facts.get("bowel"):   facts["bowel"] = "normal"
    if any(p in t for p in _urinary_normal)  and not facts.get("urinary"): facts["urinary"] = "normal"

    # Urinary negative answer to question
    if not facts.get("urinary") and any(p in t for p in ["không", "no"] ) and "tiểu" in t:
        facts["urinary"] = "normal"

    # Severity extraction — "X/10" or "mức X" or "điểm X"
    if not facts.get("severity"):
        m = re.search(r'(\d{1,2})\s*/\s*10', t)
        if not m:
            m = re.search(r'(?:mức|điểm|đau)\s+(\d{1,2})\b', t)
        if m:
            score = int(m.group(1))
            if 1 <= score <= 10:
                facts["severity"] = f"{score}/10"

    # Functional impact
    _functional_impact = ["ảnh hưởng", "không đi lại được", "không đi được", "khó đi", "nằm một chỗ", "không làm việc", "không ngủ"]
    if facts.get("severity") and not facts.get("functional_status"):
        if any(p in t for p in _functional_impact):
            curr = facts.get("severity", "")
            facts["severity"] = curr + " — ảnh hưởng sinh hoạt"
            facts["functional_status"] = "impaired"

    # LMP extraction
    _lmp_patterns = [
        r"kinh\s+(?:nguyệt\s+)?(?:vừa|mới)\s+(?:xong|hết|có)",
        r"(?:tuần|tháng|ngày)\s+(?:trước|qua)",
        r"lần\s+cuối\s+(?:là|khoảng)",
        r"\d+\s+(?:tuần|ngày|tháng)\s+trước",
    ]
    if not facts.get("lmp"):
        for pat in _lmp_patterns:
            if re.search(pat, t):
                facts["lmp"] = "reported"
                break
    # LMP negative / not applicable
    if not facts.get("lmp") and any(p in t for p in ["không ra máu", "không có kinh", "mãn kinh", "chưa có kinh"]):
        facts["lmp"] = "not applicable"

    return facts


def check_red_flag_combos(facts: dict) -> tuple[bool, str]:
    """Check if confirmed facts match any emergency combo.
    Returns (is_emergency, combo_name).
    """
    # Build flag set from confirmed facts
    active_flags = set()
    if facts.get("chest_pain_flag") == "yes":  active_flags.add("chest_pain")
    if facts.get("diaphoresis") == "yes":       active_flags.add("diaphoresis")
    if facts.get("dyspnea") == "yes":           active_flags.add("dyspnea")
    if facts.get("radiation_arm") == "yes":     active_flags.add("radiation_arm")
    if facts.get("worst_headache_ever") == "yes": active_flags.add("worst_headache_ever")
    if facts.get("neck_stiffness") == "yes":    active_flags.add("neck_stiffness")
    if facts.get("fever") == "yes":             active_flags.add("fever")
    if facts.get("syncope") == "yes":           active_flags.add("syncope")
    if facts.get("vaginal_bleeding") == "yes":  active_flags.add("vaginal_bleeding")
    # pelvic pain from cc or location
    cc = (facts.get("cc") or "").lower()
    loc = (facts.get("location") or "").lower()
    if any(w in cc + loc for w in ["bụng dưới", "hạ vị", "hố chậu", "vùng chậu", "pelvic"]):
        active_flags.add("pelvic_pain")
    if any(w in cc + loc for w in ["lưng", "back"]):
        active_flags.add("back_pain")

    for flag_set, threshold, name in RED_FLAG_COMBOS:
        if len(active_flags & flag_set) >= threshold:
            return True, name

    return False, ""


def detect_complaint_category(text: str, cc: str = "") -> str:
    """Detect complaint category from CC text."""
    combined = (text + " " + cc).lower()
    if any(w in combined for w in ["bụng", "abdominal", "dạ dày", "ruột", "gan", "mật"]):
        return "abdominal_pain"
    if any(w in combined for w in ["ngực", "tim", "chest", "cardiac", "tức ngực"]):
        return "chest_pain"
    if any(w in combined for w in ["đầu", "headache", "đau đầu", "migraine"]):
        return "headache"
    if any(w in combined for w in ["thở", "ho", "phổi", "respiratory", "cough"]):
        return "respiratory"
    if any(w in combined for w in ["tiểu", "nước tiểu", "thận", "urinary", "bladder"]):
        return "urinary"
    return "general"
