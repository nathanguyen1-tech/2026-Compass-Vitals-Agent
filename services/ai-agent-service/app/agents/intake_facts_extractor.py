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

    # Gender
    if not facts.get("gender"):
        if any(w in t for w in _GENDER_FEMALE):
            facts["gender"] = "female"
        elif any(w in t for w in _GENDER_MALE):
            facts["gender"] = "male"

    # Age — extract number before "tuổi" or "years old"
    if not facts.get("age"):
        m = re.search(r'(\d{1,3})\s*(?:tuổi|years?\s*old)', t)
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
    if any(p in t for p in _FEVER_POSITIVE)    and not facts.get("fever"):
        facts["fever"] = "yes"
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

    # Bowel/urinary negative
    _bowel_normal = ["đại tiện bình thường", "đại tiện ổn", "không tiêu chảy", "không táo bón"]
    _urinary_normal = ["tiểu bình thường", "tiểu tiện bình thường", "không tiểu buốt"]
    if any(p in t for p in _bowel_normal)   and not facts.get("bowel"):   facts["bowel"] = "normal"
    if any(p in t for p in _urinary_normal) and not facts.get("urinary"): facts["urinary"] = "normal"

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
