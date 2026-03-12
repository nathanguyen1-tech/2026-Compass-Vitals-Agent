"""Clinical Scoring Engine — Rule-based clinical decision scores.

Independent of LLM judgment. Calculates evidence-based risk scores from
intake data collected by IntakeTracker.

Scores implemented:
- HEART score proxy (chest pain → ACS risk)
- Wells PE proxy (PE risk)
- qSOFA proxy (sepsis risk)
- PHQ-2 (depression screening gateway)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.tools.intake_tracker import IntakeTracker


# === HEART Score Proxy ===
# Modified: no ECG/troponin available in telemedicine intake.
# Uses History + Age proxy + Risk factors = 0-6 range.


def calculate_heart_score_proxy(tracker: IntakeTracker) -> dict:
    """Calculate modified HEART score proxy from intake data.

    Components (no ECG/troponin in telemedicine):
    - History (0-2): typical anginal features
    - Age proxy (0-1): based on risk factor mentions
    - Risk factors (0-3): DM, HTN, smoking, prior CAD, family hx

    Returns:
        {score: int, risk: str, components: dict, max_score: int}
        risk: "low" (0-2), "moderate" (3-4), "high" (5+)
    """
    components: dict[str, int] = {"history": 0, "age_proxy": 0, "risk_factors": 0}

    # --- History (0-2) ---
    # Look at character of pain + associated symptoms
    cc = (tracker.cc or "").lower()
    character = (tracker.hpi.get("character") or "").lower()
    all_text = f"{cc} {character}"

    # Typical anginal features: pressure, squeezing, tightness, heaviness
    typical_terms = ["pressure", "squeezing", "tightness", "heavy", "crushing",
                     "tuc", "nan", "de", "bop"]
    atypical_terms = ["sharp", "stabbing", "burning", "nhoi", "dam", "nong"]

    has_typical = any(t in all_text for t in typical_terms)
    has_atypical = any(t in all_text for t in atypical_terms)

    if has_typical and not has_atypical:
        components["history"] = 2  # Highly suspicious
    elif has_typical or not has_atypical:
        components["history"] = 1  # Moderately suspicious
    # else: 0 — slightly suspicious

    # Check for associated symptoms (SOB, diaphoresis, radiation)
    symptoms_text = " ".join(str(v) for v in tracker.hpi.values() if v)
    symptoms_text += " " + " ".join(tracker.active_symptoms)
    symptoms_lower = symptoms_text.lower()

    associated = ["shortness of breath", "kho tho", "sweating", "mo hoi",
                   "nausea", "buon non", "radiating", "lan ra", "jaw", "ham",
                   "arm", "tay", "syncope", "ngat"]
    associated_count = sum(1 for a in associated if a in symptoms_lower)
    if associated_count >= 2:
        components["history"] = min(2, components["history"] + 1)

    # --- Age proxy (0-1) ---
    # We don't have explicit age, but check PMH for age-related mentions
    pmh = (tracker.pmh or "").lower()
    if any(term in pmh for term in ["elderly", "gia", "cao tuoi", "senior"]):
        components["age_proxy"] = 1

    # --- Risk factors (0-3) ---
    rf_text = f"{pmh} {(tracker.medications or '').lower()} {(tracker.social_family or '').lower()}"
    rf_count = 0
    if any(t in rf_text for t in ["diabetes", "tieu duong", "dm", "a1c", "insulin", "metformin"]):
        rf_count += 1
    if any(t in rf_text for t in ["hypertension", "huyet ap", "htn", "bp", "amlodipine", "lisinopril"]):
        rf_count += 1
    if any(t in rf_text for t in ["smok", "hut thuoc", "tobacco", "cigarette", "thuoc la"]):
        rf_count += 1
    if any(t in rf_text for t in ["heart disease", "cad", "stent", "bypass", "mi ", "benh tim"]):
        rf_count += 1
    if any(t in rf_text for t in ["family heart", "gia dinh tim", "cholesterol", "lipid"]):
        rf_count += 1
    components["risk_factors"] = min(3, rf_count)

    score = sum(components.values())
    max_score = 6

    if score <= 2:
        risk = "low"
    elif score <= 4:
        risk = "moderate"
    else:
        risk = "high"

    return {"score": score, "risk": risk, "components": components, "max_score": max_score}


# === Wells PE Proxy ===


def calculate_wells_pe_proxy(tracker: IntakeTracker) -> dict:
    """Calculate Wells criteria proxy for PE from intake history.

    Simplified for telemedicine (no clinical exam):
    - Leg swelling/pain (0-3)
    - Immobilization/recent surgery (0-1.5)
    - Cancer history (0-1)
    - Hemoptysis (0-1)
    - Tachycardia proxy — patient reports racing heart (0-1.5)
    - PE most likely diagnosis (0-3) — based on symptom combination

    Returns:
        {score: float, risk: str, components: dict, max_score: float}
    """
    components: dict[str, float] = {}
    all_text = _collect_all_text(tracker)

    # Leg swelling/pain
    if any(t in all_text for t in ["leg swelling", "swollen leg", "calf pain",
                                    "sung chan", "phu chan", "dau bap chan"]):
        components["leg_signs"] = 3.0
    else:
        components["leg_signs"] = 0.0

    # Immobilization / recent surgery
    if any(t in all_text for t in ["surgery", "phau thuat", "immobil", "bed rest",
                                    "nam liet giuong", "cast", "bo bot"]):
        components["immobilization"] = 1.5
    else:
        components["immobilization"] = 0.0

    # Cancer
    if any(t in all_text for t in ["cancer", "ung thu", "tumor", "chemo", "radiation"]):
        components["cancer"] = 1.0
    else:
        components["cancer"] = 0.0

    # Hemoptysis
    if any(t in all_text for t in ["coughing blood", "hemoptysis", "ho ra mau"]):
        components["hemoptysis"] = 1.0
    else:
        components["hemoptysis"] = 0.0

    # Tachycardia proxy
    if any(t in all_text for t in ["racing heart", "heart pounding", "tim dap nhanh",
                                    "hoi hop", "palpitation"]):
        components["tachycardia_proxy"] = 1.5
    else:
        components["tachycardia_proxy"] = 0.0

    # PE most likely — SOB + chest pain + no clear other cause
    cc = (tracker.cc or "").lower()
    has_sob = any(t in all_text for t in ["shortness of breath", "kho tho", "dyspnea"])
    has_chest = any(t in all_text for t in ["chest pain", "dau nguc"])
    if has_sob and has_chest and components["leg_signs"] > 0:
        components["pe_likely"] = 3.0
    else:
        components["pe_likely"] = 0.0

    score = sum(components.values())
    max_score = 11.0

    if score < 2:
        risk = "low"
    elif score < 6:
        risk = "moderate"
    else:
        risk = "high"

    return {"score": score, "risk": risk, "components": components, "max_score": max_score}


# === qSOFA Proxy ===


def calculate_qsofa_proxy(tracker: IntakeTracker) -> dict:
    """Calculate qSOFA proxy from conversation data.

    Components (0-3):
    - Altered mental status (confusion, disorientation) = 1
    - Respiratory distress proxy (SOB, rapid breathing) = 1
    - Hypotension proxy (dizziness, lightheadedness, feeling faint) = 1

    Score ≥2 = high risk for sepsis.

    Returns:
        {score: int, risk: str, components: dict, max_score: int}
    """
    components: dict[str, int] = {}
    all_text = _collect_all_text(tracker)

    # Altered mental status
    if any(t in all_text for t in ["confused", "confusion", "disoriented", "lon xon",
                                    "noi lan", "not making sense", "lam ram"]):
        components["altered_mental"] = 1
    else:
        components["altered_mental"] = 0

    # Respiratory distress proxy
    if any(t in all_text for t in ["shortness of breath", "rapid breathing", "kho tho",
                                    "tho nhanh", "gasping", "can't breathe",
                                    "khong tho duoc"]):
        components["respiratory_distress"] = 1
    else:
        components["respiratory_distress"] = 0

    # Hypotension proxy
    if any(t in all_text for t in ["dizzy", "lightheaded", "faint", "chong mat",
                                    "xay xam", "hoa mat", "nearly passed out",
                                    "suyt ngat"]):
        components["hypotension_proxy"] = 1
    else:
        components["hypotension_proxy"] = 0

    score = sum(components.values())
    max_score = 3

    if score < 2:
        risk = "low"
    else:
        risk = "high"

    return {"score": score, "risk": risk, "components": components, "max_score": max_score}


# === PHQ-2 Score ===


def calculate_phq2_score(responses: dict) -> dict:
    """Calculate PHQ-2 depression screening score.

    Args:
        responses: dict with keys "interest" and "mood", values 0-3 each.
            0 = not at all, 1 = several days, 2 = more than half, 3 = nearly every day

    Returns:
        {score: int, risk: str, positive: bool, max_score: int}
        positive = True if score >= 3 (triggers PHQ-9 / safety screening)
    """
    interest = responses.get("interest", 0)
    mood = responses.get("mood", 0)

    # Clamp values
    interest = max(0, min(3, int(interest)))
    mood = max(0, min(3, int(mood)))

    score = interest + mood
    positive = score >= 3

    if score <= 1:
        risk = "low"
    elif score <= 2:
        risk = "moderate"
    else:
        risk = "high"

    return {"score": score, "risk": risk, "positive": positive, "max_score": 6}


# === Score Applicability ===


def get_applicable_scores(complaint_category: str | None) -> list[str]:
    """Return which clinical scores are applicable for a complaint category."""
    if not complaint_category:
        return ["qsofa"]

    mapping: dict[str, list[str]] = {
        "chest_pain": ["heart", "wells_pe", "qsofa"],
        "hypertension": ["heart", "qsofa"],
        "uri_cough": ["qsofa"],
        "headache": ["qsofa"],
        "back_joint_pain": ["qsofa"],
        "abdominal_gi": ["qsofa"],
        "mental_health": ["phq2"],
        "skin_rash": ["qsofa"],
        "urinary": ["qsofa"],
        "fatigue": ["qsofa", "heart"],
        "diabetes": ["qsofa"],
    }

    return mapping.get(complaint_category, ["qsofa"])


def calculate_score(score_type: str, tracker: IntakeTracker) -> dict:
    """Calculate a specific clinical score.

    Args:
        score_type: One of "heart", "wells_pe", "qsofa", "phq2"
        tracker: IntakeTracker with collected data.

    Returns:
        Score result dict or empty dict if score_type unknown.
    """
    calculators = {
        "heart": calculate_heart_score_proxy,
        "wells_pe": calculate_wells_pe_proxy,
        "qsofa": calculate_qsofa_proxy,
    }

    calc = calculators.get(score_type)
    if calc:
        return calc(tracker)
    return {}


# === Helpers ===


def _collect_all_text(tracker: IntakeTracker) -> str:
    """Collect all text from tracker fields for keyword scanning."""
    parts = []
    if tracker.cc:
        parts.append(tracker.cc)
    for v in tracker.hpi.values():
        if v:
            parts.append(str(v))
    for v in tracker.hpi_additional.values():
        parts.append(str(v))
    for v in tracker.ros_systems.values():
        parts.append(str(v))
    if tracker.pmh:
        parts.append(tracker.pmh)
    if tracker.medications:
        parts.append(tracker.medications)
    if tracker.social_family:
        parts.append(tracker.social_family)
    parts.extend(tracker.active_symptoms)
    return " ".join(parts).lower()
