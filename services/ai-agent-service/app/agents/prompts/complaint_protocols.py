"""Complaint Protocol Data Layer — 11 clinical protocols for intelligent intake.

Each protocol defines complaint-specific HPI questions, red flags,
ROS focus areas, and cultural notes for the Vietnamese American population.
Based on clinical-intake-protocol.md.
"""

from __future__ import annotations

import unicodedata
from typing import NotRequired, TypedDict


def _strip_vietnamese_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics for keyword matching.

    Examples: 'đau ngực' → 'dau nguc', 'khó thở' → 'kho tho'
    """
    # Handle đ/Đ separately (not decomposable by NFD)
    text = text.replace("đ", "d").replace("Đ", "D")
    # Decompose + strip combining marks
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# === Data Types ===


class RedFlag(TypedDict):
    """A complaint-specific red flag pattern."""

    id: str  # e.g., "chest_pain_active_with_dyspnea"
    pattern_en: str  # English description
    pattern_vi: str  # Vietnamese description
    action: str  # "911" | "ER" | "urgent_review"
    message_en: str  # Emergency message in English
    message_vi: str  # Emergency message in Vietnamese
    keywords: list[str]  # Keywords that indicate this red flag (lowercase)


class ScreeningQuestion(TypedDict):
    """An explicit safety screening question for enforced red flag screening."""

    id: str  # e.g., "cp_active_now"
    question_en: str
    question_vi: str
    rationale: str  # Why this question matters


class SafetyNetting(TypedDict):
    """Complaint-specific safety netting for end of conversation."""

    worsening_signs_vi: str
    worsening_signs_en: str
    follow_up: str  # e.g., "48 hours", "24 hours"
    escalation: str  # e.g., "115 / 911"


class ComplaintProtocol(TypedDict):
    """A complaint-specific clinical intake protocol."""

    id: str  # e.g., "hypertension", "chest_pain"
    name_en: str
    name_vi: str
    keywords_en: list[str]  # CC classification keywords (English, lowercase)
    keywords_vi: list[str]  # CC classification keywords (Vietnamese, lowercase)
    hpi_additions: list[str]  # Additional HPI questions beyond OLDCARTS
    relevant_oldcarts: list[str]  # Which OLDCARTS fields are clinically relevant
    red_flags: list[RedFlag]
    ros_focus: list[str]  # Which ROS systems to target
    cultural_notes: str  # Cultural context for the LLM
    priority_order: str  # "red_flags_first" for chest_pain, "standard" for most
    clinical_reasoning: NotRequired[dict]  # Clinical decision support for LLM
    screening_questions: NotRequired[list[ScreeningQuestion]]  # Enforced safety questions
    safety_netting: NotRequired[SafetyNetting]  # End-of-conversation safety net


# All 8 OLDCARTS fields — canonical reference list
OLDCARTS_ALL = [
    "onset", "location", "duration", "character",
    "aggravating", "alleviating", "timing", "severity",
]


# === 11 Complaint Protocols ===


PROTOCOLS: dict[str, ComplaintProtocol] = {
    # --- Tier 1: #1 Hypertension ---
    "hypertension": {
        "id": "hypertension",
        "name_en": "Hypertension Management / BP Concerns",
        "name_vi": "Quản lý tăng huyết áp",
        "keywords_en": [
            "blood pressure", "high blood pressure", "hypertension", "bp",
            "bp high", "pressure high",
        ],
        "keywords_vi": [
            "huyết áp", "huyết áp cao", "tăng huyết áp", "cao huyết áp",
            "áp huyết", "huyết áp lên",
        ],
        "hpi_additions": [
            "Home BP readings? What device do you use?",
            "Headaches, vision changes, chest pain, or shortness of breath?",
            "Dietary habits — salt intake, fish sauce (nuoc mam) usage?",
            "Current BP medications? Taking them regularly?",
            "Previous highest BP reading?",
        ],
        "relevant_oldcarts": ["onset", "duration", "aggravating", "severity"],
        "red_flags": [
            {
                "id": "hypertensive_emergency",
                "pattern_en": "BP >180/120 with headache/vision changes/chest pain",
                "pattern_vi": "HA >180/120 kem dau dau/thay doi thi luc/dau nguc",
                "action": "ER",
                "message_en": "Your blood pressure symptoms need immediate medical attention. Please go to the nearest ER.",
                "message_vi": "Trieu chung huyet ap cua ban can duoc cham soc y te ngay. Vui long den phong cap cuu gan nhat.",
                "keywords": ["180", "vision changes", "thay doi thi luc", "mat mo"],
            },
        ],
        "ros_focus": ["cardiovascular", "neurological", "renal"],
        "cultural_notes": (
            "Vietnamese Americans have high prevalence of hypertension. "
            "Ask specifically about fish sauce (nuoc mam) usage as it is very high in sodium. "
            "Many patients track BP at home — ask about their device and readings."
        ),
        "priority_order": "standard",
        "clinical_reasoning": {
            "risk_stratification": (
                "Assess for hypertensive emergency vs urgency:\n"
                "- BP >180/120 WITH symptoms (headache, vision changes, chest pain, SOB, confusion) = EMERGENCY\n"
                "- BP >180/120 WITHOUT symptoms = urgent but not emergency\n"
                "- Ask about home BP readings and trends"
            ),
            "investigation_strategy": (
                "1. Current symptoms? (headache, vision changes, chest pain, SOB, confusion)\n"
                "2. Last known BP reading? How high?\n"
                "3. Taking medications regularly? Any missed doses?\n"
                "IF symptoms present + suspected high BP → emergency_suspected"
            ),
            "danger_combinations": [
                "high BP + headache + vision changes → hypertensive emergency → ER",
                "high BP + chest pain → possible ACS or aortic dissection → 911",
                "high BP + confusion → hypertensive encephalopathy → ER",
                "high BP + pregnancy → preeclampsia → ER",
            ],
            "pmh_modifiers": [
                "Known HTN + medication non-compliance → higher risk of crisis",
                "Prior stroke + high BP → higher risk of recurrence",
            ],
        },
        "screening_questions": [
            {
                "id": "htn_symptoms_now",
                "question_en": "Are you having headaches, vision changes, or chest pain RIGHT NOW?",
                "question_vi": "Ban co dang bi dau dau, thay doi thi luc, hoac dau nguc NGAY LUC NAY khong?",
                "rationale": "Screen for hypertensive emergency with end-organ damage",
            },
            {
                "id": "htn_bp_reading",
                "question_en": "Do you know your recent blood pressure reading? Was it above 180/120?",
                "question_vi": "Ban co biet chi so huyet ap gan day khong? Co tren 180/120 khong?",
                "rationale": "Quantify severity — BP >180/120 with symptoms = emergency",
            },
            {
                "id": "htn_confusion",
                "question_en": "Are you feeling confused, dizzy, or having trouble speaking?",
                "question_vi": "Ban co cam thay lon xon, chong mat, hoac kho noi khong?",
                "rationale": "Screen for hypertensive encephalopathy",
            },
        ],
        "safety_netting": {
            "worsening_signs_vi": "Neu dau dau du doi, mat mo, dau nguc, kho tho, hoac lon xon → goi 115 ngay",
            "worsening_signs_en": "If severe headache, vision changes, chest pain, SOB, or confusion → call 911",
            "follow_up": "48 hours",
            "escalation": "115 / 911",
        },
    },

    # --- Tier 1: #2 Diabetes ---
    "diabetes": {
        "id": "diabetes",
        "name_en": "Diabetes / Elevated Blood Sugar",
        "name_vi": "Tieu duong / Duong huyet cao",
        "keywords_en": [
            "diabetes", "blood sugar", "sugar high", "diabetic",
            "glucose", "a1c", "insulin",
        ],
        "keywords_vi": [
            "tieu duong", "duong huyet", "duong cao", "duong len",
            "dai thao duong", "tieu duong type",
        ],
        "hpi_additions": [
            "Known diabetic? Type 1 or 2? When diagnosed?",
            "Last A1c or fasting glucose? Home glucose readings?",
            "Increased urination, thirst, or hunger? Unintentional weight loss?",
            "Numbness or tingling in feet? Vision changes?",
            "Diet — rice consumption frequency, sweet drinks (tra sua/boba)?",
            "Current diabetes medications? Insulin?",
        ],
        "relevant_oldcarts": ["onset", "duration", "aggravating", "severity"],
        "red_flags": [
            {
                "id": "dka_symptoms",
                "pattern_en": "Symptoms of DKA: nausea/vomiting + confusion + rapid breathing",
                "pattern_vi": "Trieu chung DKA: buon non/oi + lon xon + tho nhanh",
                "action": "ER",
                "message_en": "These symptoms could indicate a diabetic emergency. Please go to the nearest ER immediately.",
                "message_vi": "Nhung trieu chung nay co the la tinh trang khan cap tieu duong. Vui long den phong cap cuu ngay.",
                "keywords": [
                    "nausea", "vomiting", "confusion", "rapid breathing",
                    "buon non", "oi", "lon xon", "tho nhanh",
                ],
            },
        ],
        "ros_focus": ["endocrine", "neurological", "ophthalmologic", "renal"],
        "cultural_notes": (
            "Vietnamese Americans have one of the highest diabetes incidence rates among Asian subgroups. "
            "Ask about rice consumption frequency — many patients eat rice 2-3 times daily. "
            "Sweet drinks like tra sua (boba/milk tea) are very popular. "
            "Use Asian-specific BMI cutoffs: overweight >= 23, obese >= 27.5."
        ),
        "priority_order": "standard",
        "clinical_reasoning": {
            "risk_stratification": (
                "Assess for DKA / HHS (diabetic emergencies):\n"
                "- Known diabetic + nausea/vomiting + confusion + rapid breathing = DKA risk\n"
                "- Very high glucose + extreme thirst + altered mental status = HHS risk\n"
                "- Type 1 diabetics at higher DKA risk; Type 2 at higher HHS risk"
            ),
            "investigation_strategy": (
                "1. Known diabetic? Type 1 or 2?\n"
                "2. Current symptoms: nausea, vomiting, confusion, rapid breathing?\n"
                "3. Last glucose reading? Last meal?\n"
                "4. Insulin/medication compliance?\n"
                "IF nausea + confusion + rapid breathing → emergency_suspected (DKA)"
            ),
            "danger_combinations": [
                "diabetic + nausea + confusion + rapid breathing → DKA → ER",
                "diabetic + extreme thirst + altered mental status → HHS → ER",
                "diabetic + fruity breath odor + drowsiness → DKA → ER",
                "diabetic + not eating + taking insulin → hypoglycemia risk → urgent",
            ],
            "pmh_modifiers": [
                "Type 1 DM → lower threshold for DKA concern",
                "Prior DKA episodes → higher risk of recurrence",
                "Elderly + Type 2 DM → HHS risk",
            ],
        },
        "screening_questions": [
            {
                "id": "dm_nausea_confusion",
                "question_en": "Are you having nausea, vomiting, or feeling confused right now?",
                "question_vi": "Ban co dang bi buon non, oi mua, hoac cam thay lon xon khong?",
                "rationale": "Screen for DKA/HHS — nausea + confusion = emergency",
            },
            {
                "id": "dm_breathing",
                "question_en": "Are you breathing faster than usual or having trouble catching your breath?",
                "question_vi": "Ban co dang tho nhanh hon binh thuong hoac kho tho khong?",
                "rationale": "Kussmaul breathing is hallmark of DKA",
            },
            {
                "id": "dm_glucose_reading",
                "question_en": "Do you know your current blood sugar? When did you last eat?",
                "question_vi": "Ban co biet chi so duong huyet hien tai khong? Lan cuoi an la khi nao?",
                "rationale": "Quantify hypo/hyperglycemia risk",
            },
        ],
        "safety_netting": {
            "worsening_signs_vi": "Neu buon non/oi tang, lon xon, tho nhanh, hoac mat y thuc → goi 115 ngay",
            "worsening_signs_en": "If worsening nausea/vomiting, confusion, rapid breathing, or loss of consciousness → call 911",
            "follow_up": "24 hours",
            "escalation": "115 / 911",
        },
    },

    # --- Tier 1: #3 URI / Cough ---
    "uri_cough": {
        "id": "uri_cough",
        "name_en": "Upper Respiratory Infection / Cough / Cold",
        "name_vi": "Nhiem trung ho hap tren / Ho / Cam",
        "keywords_en": [
            "cough", "cold", "flu", "sore throat", "runny nose",
            "congestion", "stuffy nose", "phlegm", "mucus",
            "fever", "chills", "high temperature",
        ],
        "keywords_vi": [
            "ho", "cam", "cum", "dau hong", "so mui",
            "nghet mui", "chay nuoc mui", "dam", "viem hong",
            "trung gio",
            "sot", "sốt", "nhiet do cao", "lanh run", "ớn lạnh",
            "kho tho", "kho tho duoc",  # dyspnea / respiratory distress
        ],
        "hpi_additions": [
            "Fever? Maximum temperature?",
            "Cough — productive or dry? Color of sputum?",
            "Sore throat, nasal congestion, post-nasal drip?",
            "Sick contacts? Recent travel?",
            "TB screening history? (Important for Vietnamese population)",
            "Duration — less than 3 weeks or longer?",
        ],
        "relevant_oldcarts": ["onset", "duration", "character", "aggravating", "timing", "severity"],
        "red_flags": [
            {
                "id": "meningitis_signs",
                "pattern_en": "High fever + stiff neck",
                "pattern_vi": "Sot cao + cung co",
                "action": "ER",
                "message_en": "High fever with stiff neck needs immediate evaluation. Please go to the nearest ER.",
                "message_vi": "Sot cao kem cung co can duoc kham ngay. Vui long den phong cap cuu gan nhat.",
                "keywords": ["stiff neck", "cung co", "cung gay"],
            },
            {
                "id": "respiratory_distress",
                "pattern_en": "Difficulty breathing or coughing blood",
                "pattern_vi": "Kho tho hoac ho ra mau",
                "action": "ER",
                "message_en": "Difficulty breathing or coughing blood needs emergency care. Please call 911.",
                "message_vi": "Kho tho hoac ho ra mau can cap cuu. Vui long goi 911.",
                "keywords": [
                    "difficulty breathing", "coughing blood", "hemoptysis",
                    "kho tho", "ho ra mau",
                ],
            },
        ],
        "ros_focus": ["ENT", "pulmonary", "constitutional"],
        "cultural_notes": (
            "TB screening is critical for Vietnamese immigrant population. "
            "Many Vietnamese patients attribute colds to 'trung gio' (catching wind) — "
            "acknowledge this cultural concept and ask follow-up questions. "
            "Ask about traditional remedies like cao gio (coining), giac hoi (cupping)."
        ),
        "priority_order": "standard",
        "clinical_reasoning": {
            "risk_stratification": (
                "Assess for serious respiratory infection vs simple URI:\n"
                "- High fever (>39°C) + productive cough + SOB = pneumonia risk\n"
                "- High fever + stiff neck = meningitis concern\n"
                "- Cough >3 weeks in Vietnamese patient = TB screening critical\n"
                "- Hemoptysis (coughing blood) = always HIGH risk"
            ),
            "investigation_strategy": (
                "1. Fever? Maximum temperature?\n"
                "2. Difficulty breathing or SOB?\n"
                "3. Coughing blood?\n"
                "4. Stiff neck or worst headache?\n"
                "IF high fever + SOB → emergency_suspected\n"
                "IF hemoptysis → emergency_suspected"
            ),
            "danger_combinations": [
                "high fever + stiff neck → meningitis → ER",
                "coughing blood → hemoptysis workup → ER",
                "high fever + SOB + productive cough → pneumonia → urgent/ER",
                "SOB + can't speak full sentences → respiratory distress → 911",
            ],
            "pmh_modifiers": [
                "Immunosuppressed + fever → lower threshold for concern",
                "COPD/asthma + respiratory infection → higher pneumonia risk",
                "Vietnamese immigrant + chronic cough → TB screening priority",
            ],
        },
        "screening_questions": [
            {
                "id": "uri_breathing",
                "question_en": "Are you having difficulty breathing or shortness of breath?",
                "question_vi": "Ban co dang kho tho hoac thieu hoi khong?",
                "rationale": "Screen for respiratory distress / pneumonia",
            },
            {
                "id": "uri_fever_neck",
                "question_en": "Do you have a fever? Any stiff neck or the worst headache of your life?",
                "question_vi": "Ban co sot khong? Co cung co hoac dau dau du doi nhat chua tung co khong?",
                "rationale": "Screen for meningitis",
            },
            {
                "id": "uri_blood_cough",
                "question_en": "Have you coughed up any blood?",
                "question_vi": "Ban co ho ra mau khong?",
                "rationale": "Hemoptysis is always high risk",
            },
        ],
        "safety_netting": {
            "worsening_signs_vi": "Neu kho tho tang, ho ra mau, sot cao khong ha, hoac cung co → goi 115 ngay",
            "worsening_signs_en": "If worsening breathing difficulty, coughing blood, persistent high fever, or stiff neck → call 911",
            "follow_up": "72 hours",
            "escalation": "115 / 911",
        },
    },

    # --- Tier 1: #4 Headache ---
    "headache": {
        "id": "headache",
        "name_en": "Headache",
        "name_vi": "Dau dau",
        "keywords_en": [
            "headache", "head pain", "migraine", "head hurts",
            "head ache", "tension headache",
        ],
        "keywords_vi": [
            "dau dau", "nhuc dau", "dau nua dau", "dau dau du doi",
            "nhu bua dap",
        ],
        "hpi_additions": [
            "Location — frontal, temporal, occipital, or one-sided?",
            "Aura or visual disturbances before the headache?",
            "Is this the worst headache of your life? Sudden thunderclap onset?",
            "Nausea/vomiting? Sensitivity to light or sound?",
            "Triggers — stress, food, sleep changes, menstrual cycle?",
            "How many headaches per week or month?",
            "Any history of head trauma?",
        ],
        "relevant_oldcarts": ["onset", "location", "duration", "character", "aggravating", "alleviating", "timing", "severity"],
        "red_flags": [
            {
                "id": "thunderclap_headache",
                "pattern_en": "Thunderclap headache / worst headache of life",
                "pattern_vi": "Dau dau dot ngot du doi nhat / dau nhat trong doi",
                "action": "911",
                "message_en": "A sudden severe headache needs immediate evaluation. Please call 911.",
                "message_vi": "Dau dau dot ngot du doi can duoc kham ngay. Vui long goi 911.",
                "keywords": [
                    "worst headache", "thunderclap", "worst of my life",
                    "dau nhat", "dot ngot du doi", "chua tung dau nhu vay",
                ],
            },
            {
                "id": "headache_neuro_deficit",
                "pattern_en": "Headache with neurological deficits or fever + stiff neck",
                "pattern_vi": "Dau dau kem trieu chung than kinh hoac sot + cung co",
                "action": "ER",
                "message_en": "Headache with neurological symptoms needs emergency evaluation. Please go to the ER.",
                "message_vi": "Dau dau kem trieu chung than kinh can cap cuu. Vui long den phong cap cuu.",
                "keywords": [
                    "numbness", "weakness", "vision loss", "slurred speech",
                    "te", "yeu", "mat thi luc", "noi ngong",
                ],
            },
        ],
        "ros_focus": ["neurological", "ophthalmologic", "ENT"],
        "cultural_notes": (
            "New headache in patients over 50 should always warrant concern. "
            "Ask about traditional remedies like dau xanh (green oil), cao sao vang."
        ),
        "priority_order": "standard",
        "clinical_reasoning": {
            "risk_stratification": (
                "Assess for life-threatening headache causes:\n"
                "- Thunderclap onset (maximal in seconds) = SAH until proven otherwise → CRITICAL\n"
                "- Headache + fever + stiff neck = meningitis → HIGH\n"
                "- New headache + focal neuro deficit (weakness, vision, speech) = mass/stroke → HIGH\n"
                "- Headache + papilledema signs (vision changes, worse lying down) = raised ICP → HIGH\n"
                "- New headache in patient >50 + jaw claudication = giant cell arteritis → HIGH"
            ),
            "investigation_strategy": (
                "1. Is this the WORST headache of your life? Did it come on suddenly?\n"
                "2. Any fever or stiff neck?\n"
                "3. Any numbness, weakness, vision changes, or difficulty speaking?\n"
                "IF thunderclap onset → emergency_suspected immediately\n"
                "IF fever + stiff neck → emergency_suspected"
            ),
            "danger_combinations": [
                "worst headache ever + sudden onset → possible SAH → 911",
                "headache + fever + stiff neck → meningitis → ER",
                "headache + vision loss + weakness → stroke/mass → 911",
                "headache + confusion + high fever → encephalitis → ER",
                "new headache + age >50 + jaw pain → giant cell arteritis → urgent",
            ],
            "pmh_modifiers": [
                "Prior aneurysm or SAH → thunderclap headache is higher risk",
                "Known HTN + severe headache → risk of hemorrhagic stroke",
                "Immunosuppressed + headache + fever → lower threshold for meningitis concern",
            ],
        },
        "screening_questions": [
            {
                "id": "ha_thunderclap",
                "question_en": "Is this the WORST headache of your life? Did it come on suddenly, like a thunderclap?",
                "question_vi": "Day co phai la con dau dau DU DOI NHAT trong doi ban khong? No co den dot ngot nhu set danh khong?",
                "rationale": "Screen for SAH — thunderclap headache is neurosurgical emergency",
            },
            {
                "id": "ha_fever_neck",
                "question_en": "Do you have a fever with a stiff neck?",
                "question_vi": "Ban co bi sot kem cung co khong?",
                "rationale": "Screen for meningitis",
            },
            {
                "id": "ha_neuro_deficit",
                "question_en": "Any numbness, weakness, vision changes, or difficulty speaking?",
                "question_vi": "Ban co bi te, yeu, thay doi thi luc, hoac kho noi khong?",
                "rationale": "Screen for stroke / intracranial mass",
            },
        ],
        "safety_netting": {
            "worsening_signs_vi": "Neu dau dau dot ngot du doi, cung co, te/yeu nua nguoi, mat thi luc, kho noi → goi 115 ngay",
            "worsening_signs_en": "If sudden severe headache, stiff neck, one-sided numbness/weakness, vision loss, speech difficulty → call 911",
            "follow_up": "24 hours",
            "escalation": "115 / 911",
        },
    },

    # --- Tier 1: #5 Back Pain / Joint Pain ---
    "back_joint_pain": {
        "id": "back_joint_pain",
        "name_en": "Back Pain / Joint Pain",
        "name_vi": "Dau lung / Dau khop",
        "keywords_en": [
            "back pain", "joint pain", "knee pain", "shoulder pain",
            "hip pain", "neck pain", "arthritis", "spine",
        ],
        "keywords_vi": [
            "dau lung", "dau khop", "dau goi", "dau vai",
            "dau hong", "dau co", "vierm khop", "cot song",
        ],
        "hpi_additions": [
            "Upper or lower back? Which joints?",
            "Does the pain travel down your legs? Numbness or tingling?",
            "Any changes in bowel or bladder control?",
            "Any injury or trauma?",
            "Worse with movement or rest?",
            "What is your occupation — physical labor?",
            "Any weakness in your legs?",
        ],
        "relevant_oldcarts": ["onset", "location", "duration", "character", "aggravating", "alleviating", "timing", "severity"],
        "red_flags": [
            {
                "id": "cauda_equina",
                "pattern_en": "Loss of bowel/bladder control + saddle anesthesia + progressive weakness",
                "pattern_vi": "Mat kiem soat tieu tien/dai tien + te vung ngoi + yeu dan",
                "action": "ER",
                "message_en": "Loss of bowel/bladder control with back pain is an emergency. Please go to the ER immediately.",
                "message_vi": "Mat kiem soat tieu tien/dai tien kem dau lung la truong hop khan cap. Vui long den phong cap cuu ngay.",
                "keywords": [
                    "bladder control", "bowel control", "saddle",
                    "mat kiem soat tieu", "mat kiem soat dai tien", "te vung ngoi",
                ],
            },
        ],
        "ros_focus": ["musculoskeletal", "neurological", "urological"],
        "cultural_notes": (
            "Many Vietnamese patients do physical labor — ask about occupation. "
            "Ask about traditional treatments like bam huyet (acupressure), xoa bop (massage)."
        ),
        "priority_order": "standard",
        "clinical_reasoning": {
            "risk_stratification": (
                "Assess for cauda equina syndrome and spinal emergencies:\n"
                "- Loss of bowel/bladder control = CRITICAL (cauda equina)\n"
                "- Saddle anesthesia (numbness between legs) = CRITICAL\n"
                "- Progressive bilateral leg weakness = CRITICAL\n"
                "- Back pain + fever = spinal epidural abscess → HIGH\n"
                "- Back pain after significant trauma = fracture risk → HIGH"
            ),
            "investigation_strategy": (
                "1. Any changes in bowel or bladder control?\n"
                "2. Any numbness in the area between your legs?\n"
                "3. Any progressive weakness in your legs?\n"
                "IF any of these positive → emergency_suspected (cauda equina)\n"
                "IF back pain + fever → emergency_suspected (spinal infection)"
            ),
            "danger_combinations": [
                "back pain + bladder/bowel dysfunction → cauda equina → ER immediately",
                "back pain + saddle numbness + leg weakness → cauda equina → ER",
                "back pain + fever + IV drug use → spinal epidural abscess → ER",
                "back pain after fall/trauma + unable to move → spinal fracture → 911",
                "back pain + leg numbness progressing upward → cord compression → ER",
            ],
            "pmh_modifiers": [
                "History of cancer + new back pain → metastatic compression concern",
                "Osteoporosis + back pain after minor fall → compression fracture risk",
                "IV drug use + back pain + fever → epidural abscess concern",
            ],
        },
        "screening_questions": [
            {
                "id": "bjp_bowel_bladder",
                "question_en": "Have you noticed any changes in bowel or bladder control?",
                "question_vi": "Ban co thay doi ve kiem soat tieu tien hoac dai tien khong?",
                "rationale": "Screen for cauda equina syndrome — surgical emergency",
            },
            {
                "id": "bjp_saddle_numbness",
                "question_en": "Any numbness in the area between your legs (the area you'd sit on a saddle)?",
                "question_vi": "Ban co bi te o vung giua hai chan (vung ngoi) khong?",
                "rationale": "Saddle anesthesia = cauda equina until proven otherwise",
            },
            {
                "id": "bjp_leg_weakness",
                "question_en": "Any progressive weakness in your legs, or difficulty walking?",
                "question_vi": "Ban co bi yeu dan o chan hoac kho di lai khong?",
                "rationale": "Progressive bilateral weakness = cord compression emergency",
            },
        ],
        "safety_netting": {
            "worsening_signs_vi": "Neu mat kiem soat tieu tien/dai tien, te vung ngoi, yeu hai chan → den cap cuu NGAY",
            "worsening_signs_en": "If loss of bowel/bladder control, saddle numbness, or bilateral leg weakness → go to ER IMMEDIATELY",
            "follow_up": "48 hours",
            "escalation": "115 / 911",
        },
    },

    # --- Tier 1: #6 Abdominal / GI ---
    "abdominal_gi": {
        "id": "abdominal_gi",
        "name_en": "Abdominal Pain / GI Complaints",
        "name_vi": "Dau bung / Van de tieu hoa",
        "keywords_en": [
            "stomach pain", "abdominal pain", "belly pain", "nausea",
            "vomiting", "diarrhea", "constipation", "bloating",
            "heartburn", "acid reflux", "indigestion",
        ],
        "keywords_vi": [
            "dau bung", "dau da day", "buon non", "oi",
            "tieu chay", "tao bon", "day bung", "day hoi",
            "trao nguoc", "kho tieu",
        ],
        "hpi_additions": [
            "Where exactly — upper/lower, left/right, around the navel?",
            "Related to meals? Worse after eating?",
            "Nausea or vomiting? Diarrhea or constipation?",
            "Any blood in stool? Black or tarry stools?",
            "When was your last bowel movement?",
            "Any diet changes? Spicy food tolerance?",
            "Alcohol use?",
            "Have you ever been screened for Hepatitis B? (Important for Vietnamese population)",
        ],
        "relevant_oldcarts": ["onset", "location", "duration", "character", "aggravating", "alleviating", "timing", "severity"],
        "red_flags": [
            {
                "id": "acute_abdomen",
                "pattern_en": "Severe RLQ pain + fever (appendicitis) or rigid abdomen",
                "pattern_vi": "Dau bung duoi phai du doi + sot hoac bung cung",
                "action": "ER",
                "message_en": "Severe abdominal pain with fever needs emergency evaluation. Please go to the ER.",
                "message_vi": "Dau bung du doi kem sot can duoc kham cap cuu. Vui long den phong cap cuu.",
                "keywords": [
                    "rigid abdomen", "severe abdominal", "bloody stool",
                    "bung cung", "dau bung du doi", "di cau ra mau",
                ],
            },
        ],
        "ros_focus": ["GI", "hepatobiliary", "urological", "gynecological"],
        "cultural_notes": (
            "Hepatitis B screening is CRITICAL for Vietnamese population — 1 in 12 are chronic carriers. "
            "Leading cause of liver cancer. Many are unaware of their status. "
            "Frame screening as routine: 'This is a standard test we recommend for everyone.' "
            "Vietnamese terminology: viem gan B (Hepatitis B), gan (liver), ung thu gan (liver cancer)."
        ),
        "priority_order": "standard",
        "clinical_reasoning": {
            "risk_stratification": (
                "Assess for surgical abdomen and GI emergencies:\n"
                "- Severe RLQ pain + fever = appendicitis until proven otherwise → HIGH\n"
                "- Rigid/board-like abdomen = peritonitis → CRITICAL\n"
                "- Vomiting blood or bloody/black stool = GI bleed → CRITICAL\n"
                "- Severe epigastric pain radiating to back = pancreatitis → HIGH\n"
                "- Abdominal pain + pregnancy = ectopic pregnancy concern → HIGH"
            ),
            "investigation_strategy": (
                "1. Where exactly is the pain? (RLQ = appendix, epigastric = pancreas/ulcer)\n"
                "2. Any fever?\n"
                "3. Any blood in stool or vomiting blood?\n"
                "4. Is your belly hard/rigid?\n"
                "IF RLQ + fever → emergency_suspected (appendicitis)\n"
                "IF hematemesis or melena → emergency_suspected"
            ),
            "danger_combinations": [
                "RLQ pain + fever + rebound tenderness → appendicitis → ER",
                "severe abdominal pain + rigid abdomen → peritonitis → 911",
                "vomiting blood + dizziness → upper GI bleed → 911",
                "epigastric pain + radiating to back + vomiting → pancreatitis → ER",
                "abdominal pain + pregnancy + vaginal bleeding → ectopic → 911",
                "abdominal pain + distension + no bowel movement → obstruction → ER",
            ],
            "pmh_modifiers": [
                "Prior abdominal surgery → higher risk of adhesive obstruction",
                "On blood thinners + abdominal pain → internal bleeding risk",
                "Hepatitis B carrier (common in Vietnamese) → liver cancer screening",
                "Elderly + abdominal pain → lower threshold (atypical presentations)",
            ],
        },
        "screening_questions": [
            {
                "id": "gi_blood",
                "question_en": "Any blood in your stool, or have you vomited blood?",
                "question_vi": "Ban co di cau ra mau, hoac oi ra mau khong?",
                "rationale": "GI bleeding is always high risk — hematemesis/hematochezia",
            },
            {
                "id": "gi_severity_location",
                "question_en": "Is the pain severe? Is it in the lower right side of your belly?",
                "question_vi": "Dau co du doi khong? Co o phia ben phai bung duoi khong?",
                "rationale": "Screen for appendicitis — RLQ pain + severity",
            },
            {
                "id": "gi_fever_rigid",
                "question_en": "Do you have a fever? Is your belly very tender or hard to touch?",
                "question_vi": "Ban co sot khong? Bung co rat dau khi cham vao hoac cung khong?",
                "rationale": "Fever + rigid abdomen = peritonitis → surgical emergency",
            },
        ],
        "safety_netting": {
            "worsening_signs_vi": "Neu oi ra mau, di cau ra mau, dau bung tang du doi, bung cung, sot cao → goi 115 ngay",
            "worsening_signs_en": "If vomiting blood, bloody stool, worsening severe pain, rigid abdomen, high fever → call 911",
            "follow_up": "24 hours",
            "escalation": "115 / 911",
        },
    },

    # --- Tier 1: #7 Mental Health ---
    "mental_health": {
        "id": "mental_health",
        "name_en": "Anxiety / Depression / Insomnia",
        "name_vi": "Lo au / Tram cam / Mat ngu",
        "keywords_en": [
            "depressed", "depression", "anxiety", "anxious", "can't sleep",
            "insomnia", "sad", "stressed", "panic", "worry",
            "hopeless", "no energy", "don't want to live",
            "suicide", "suicidal", "want to die",
        ],
        "keywords_vi": [
            "tram cam", "lo au", "mat ngu", "buon", "stress",
            "khong muon song", "chan nan", "tuyet vong",
            "lo lang", "hoang loan", "khong ngu duoc",
            "tu tu", "muon chet",
        ],
        "hpi_additions": [
            "PHQ-2: Have you lost interest in things you used to enjoy?",
            "PHQ-2: Have you been feeling down, depressed, or hopeless?",
            "Sleep — trouble falling asleep or staying asleep? Hours per night?",
            "Appetite changes? Weight changes?",
            "Concentration? Energy level?",
            "SAFETY SCREENING (MANDATORY): Have you had thoughts of hurting yourself or not wanting to be alive?",
            "Stressors — immigration, family, financial, cultural adjustment?",
            "Traditional coping — meditation, temple, family support?",
        ],
        "relevant_oldcarts": ["onset", "duration", "aggravating", "alleviating", "timing", "severity"],
        "red_flags": [
            {
                "id": "suicidal_ideation",
                "pattern_en": "Active suicidal ideation with plan",
                "pattern_vi": "Y dinh tu tu voi ke hoach cu the",
                "action": "911",
                "message_en": "I'm concerned about your safety. Please call 988 (Suicide & Crisis Lifeline) or go to your nearest ER immediately. You are not alone.",
                "message_vi": "Toi rat lo lang cho su an toan cua ban. Xin hay goi 988 (Duong day khung hoang) hoac den phong cap cuu gan nhat. Ban khong co don.",
                "keywords": [
                    "kill myself", "suicide", "end my life", "don't want to live",
                    "want to die", "self-harm",
                    "tu tu", "khong muon song", "muon chet", "tu hai",
                    "cham dut cuoc song",
                ],
            },
        ],
        "ros_focus": ["psychiatric", "neurological", "constitutional"],
        "cultural_notes": (
            "Mental health stigma is significant in Vietnamese culture. "
            "Normalize screening: 'These are questions we ask everyone.' "
            "Many Vietnamese patients express psychological distress as PHYSICAL symptoms (somatization) — "
            "'I feel tired all the time' or 'my chest feels heavy' may indicate depression. "
            "Probe further when physical complaints seem disproportionate. "
            "Frame questions gently and without judgment."
        ),
        "priority_order": "standard",
        "clinical_reasoning": {
            "risk_stratification": (
                "MANDATORY safety screening for ALL mental health presentations:\n"
                "- Active suicidal ideation WITH plan or means = CRITICAL → 911 + 988\n"
                "- Passive ideation ('don't want to be alive', 'better off dead') = HIGH\n"
                "- Self-harm with current crisis/escalation = HIGH\n"
                "- Homicidal ideation = CRITICAL\n"
                "- Psychosis with command hallucinations = HIGH\n"
                "Note: Vietnamese patients may express distress somatically — 'heavy chest',\n"
                "'no energy', 'can't eat' may mask severe depression."
            ),
            "investigation_strategy": (
                "MANDATORY FIRST QUESTION (cannot be skipped):\n"
                "1. 'Have you had thoughts of hurting yourself or not wanting to be alive?'\n"
                "IF YES → immediately assess:\n"
                "2. 'Do you have a plan for how you would hurt yourself?'\n"
                "IF plan exists → emergency_confirmed\n"
                "IF passive ideation without plan → emergency_suspected, continue assessment"
            ),
            "danger_combinations": [
                "suicidal ideation + specific plan → CRITICAL → 911 + 988 Lifeline",
                "suicidal ideation + access to means (guns, pills) → CRITICAL",
                "self-harm + escalating frequency → HIGH",
                "psychosis + command hallucinations → HIGH",
                "depression + recent loss + social isolation + substance use → HIGH risk",
                "prior suicide attempt + current crisis → CRITICAL",
            ],
            "pmh_modifiers": [
                "Prior suicide attempt → significantly higher risk",
                "History of substance abuse → higher risk",
                "Recent bereavement or major life change → higher risk",
                "Chronic pain + depression → higher risk",
            ],
        },
        "screening_questions": [
            {
                "id": "mh_mood_check",
                "question_en": "How has your mood been recently?",
                "question_vi": "Gan day tam trang ban the nao?",
                "rationale": "Low-threat mood check — PHQ-2 gateway step 1",
            },
            {
                "id": "mh_phq2",
                "question_en": "Over the past 2 weeks, have you felt down, depressed, or lost interest in things you used to enjoy?",
                "question_vi": "Trong 2 tuan qua, ban co cam thay buon, chan nan, hoac mat hung thu voi nhung dieu truoc day ban thich khong?",
                "rationale": "PHQ-2 screening — gateway to safety questions",
            },
        ],
        "safety_netting": {
            "worsening_signs_vi": "Neu ban co suy nghi tu hai ban than hoac khong muon song → goi 988 (Suicide Lifeline) hoac 115 ngay",
            "worsening_signs_en": "If you have thoughts of harming yourself or not wanting to live → call 988 (Suicide Lifeline) or 911 immediately",
            "follow_up": "24 hours",
            "escalation": "988 / 115 / 911",
        },
    },

    # --- Tier 1: #8 Skin Rash ---
    "skin_rash": {
        "id": "skin_rash",
        "name_en": "Skin Rash / Dermatologic Complaints",
        "name_vi": "Phat ban / Van de da lieu",
        "keywords_en": [
            "rash", "skin", "itchy", "itch", "hives", "eczema",
            "acne", "bump", "blister", "red spots",
        ],
        "keywords_vi": [
            "phat ban", "ngua", "noi me day", "mun",
            "da", "viem da", "do da", "noi bong nuoc",
        ],
        "hpi_additions": [
            "Where on your body? Is it spreading?",
            "Itchy, painful, or neither?",
            "Any new soaps, detergents, or medications recently?",
            "Do you have a photo you can share? (Very helpful for skin issues)",
            "Any fever along with the rash?",
            "Anyone around you with a similar rash?",
        ],
        "relevant_oldcarts": ["onset", "location", "duration", "character", "aggravating", "timing", "severity"],
        "red_flags": [
            {
                "id": "sjs_concern",
                "pattern_en": "Rapidly spreading rash + fever + mucosal involvement (SJS)",
                "pattern_vi": "Ban lan nhanh + sot + ton thuong niem mac",
                "action": "ER",
                "message_en": "A rapidly spreading rash with fever and mouth/eye involvement needs emergency care. Please go to the ER.",
                "message_vi": "Ban lan nhanh kem sot va ton thuong mieng/mat can cap cuu. Vui long den phong cap cuu.",
                "keywords": [
                    "spreading rash", "mouth sores", "eye", "blistering",
                    "lan nhanh", "lot mieng", "bong nuoc",
                ],
            },
        ],
        "ros_focus": ["dermatologic", "constitutional", "allergic_immunologic"],
        "cultural_notes": (
            "Ask about cao gio (coining) — traditional Vietnamese treatment that leaves marks on skin. "
            "These marks should not be confused with abuse or pathology."
        ),
        "priority_order": "standard",
        "clinical_reasoning": {
            "risk_stratification": (
                "Assess for Stevens-Johnson Syndrome (SJS) and severe allergic reactions:\n"
                "- Rapidly spreading rash + fever + mucosal involvement = SJS → HIGH\n"
                "- New medication in past 2 weeks + rash + fever = drug reaction → HIGH\n"
                "- Rash + throat swelling + difficulty breathing = anaphylaxis → CRITICAL\n"
                "- Petechiae (non-blanching pinpoint dots) + fever = meningococcemia → CRITICAL"
            ),
            "investigation_strategy": (
                "1. Is the rash spreading rapidly? Over how many hours?\n"
                "2. Any fever with the rash?\n"
                "3. Any mouth sores, eye redness, or genital sores? (mucosal involvement)\n"
                "4. Any new medications in the past 2 weeks?\n"
                "IF rapidly spreading + fever + mucosal → emergency_suspected (SJS)"
            ),
            "danger_combinations": [
                "rapidly spreading rash + fever + mucosal involvement → SJS/TEN → ER",
                "rash + throat swelling + SOB → anaphylaxis → 911",
                "non-blanching petechiae + fever → meningococcemia → 911",
                "new medication + widespread rash + fever → drug hypersensitivity → ER",
                "blistering rash + skin peeling → TEN → ER",
            ],
            "pmh_modifiers": [
                "Prior drug allergy → higher risk with new medications",
                "Immunosuppressed + rash + fever → lower threshold for concern",
            ],
        },
        "screening_questions": [
            {
                "id": "skin_spreading_fever",
                "question_en": "Is the rash spreading rapidly? Do you have a fever?",
                "question_vi": "Phat ban co lan nhanh khong? Ban co sot khong?",
                "rationale": "Rapidly spreading rash + fever = SJS/meningococcemia concern",
            },
            {
                "id": "skin_mucosal",
                "question_en": "Any sores in your mouth, red eyes, or sores in the genital area?",
                "question_vi": "Ban co bi lot mieng, do mat, hoac lot o vung kin khong?",
                "rationale": "Mucosal involvement = SJS/TEN → emergency",
            },
            {
                "id": "skin_breathing",
                "question_en": "Any throat swelling or difficulty breathing?",
                "question_vi": "Ban co bi sung hong hoac kho tho khong?",
                "rationale": "Anaphylaxis screening — throat swelling + SOB = critical",
            },
        ],
        "safety_netting": {
            "worsening_signs_vi": "Neu phat ban lan nhanh, sot tang, lot mieng/mat, kho tho, hoac da bong troc → goi 115 ngay",
            "worsening_signs_en": "If rash spreads rapidly, worsening fever, mouth/eye sores, breathing difficulty, or skin peeling → call 911",
            "follow_up": "24 hours",
            "escalation": "115 / 911",
        },
    },

    # --- Tier 1: #9 Urinary ---
    "urinary": {
        "id": "urinary",
        "name_en": "Urinary Symptoms (UTI / Frequency / Dysuria)",
        "name_vi": "Trieu chung tieu tien (Nhiem trung tieu / Tieu nhieu / Tieu buot)",
        "keywords_en": [
            "urinary", "uti", "burning urination", "frequent urination",
            "blood in urine", "painful urination", "bladder",
        ],
        "keywords_vi": [
            "tieu buot", "tieu nhieu", "tieu ra mau", "nhiem trung tieu",
            "dau khi di tieu", "bang quang",
        ],
        "hpi_additions": [
            "Burning with urination? How often are you going?",
            "Any urgency — feeling like you can't hold it?",
            "Blood in urine? Cloudy or foul-smelling?",
            "Flank pain? Fever or chills?",
            "Any vaginal discharge? (if applicable)",
            "History of UTIs? How many in the past year?",
            "Sexually active?",
        ],
        "relevant_oldcarts": ["onset", "duration", "character", "aggravating", "timing", "severity"],
        "red_flags": [
            {
                "id": "pyelonephritis",
                "pattern_en": "High fever + flank pain (pyelonephritis) or urinary retention",
                "pattern_vi": "Sot cao + dau hong lung (viem be than) hoac bi tieu",
                "action": "ER",
                "message_en": "High fever with flank pain needs urgent evaluation. Please go to the ER.",
                "message_vi": "Sot cao kem dau hong lung can kham gap. Vui long den phong cap cuu.",
                "keywords": [
                    "high fever", "flank pain", "can't urinate", "retention",
                    "sot cao", "dau hong lung", "bi tieu", "khong tieu duoc",
                ],
            },
        ],
        "ros_focus": ["genitourinary", "constitutional", "gynecological"],
        "cultural_notes": (
            "Urinary and reproductive health topics may be sensitive. "
            "Use respectful, clinical language."
        ),
        "priority_order": "standard",
        "clinical_reasoning": {
            "risk_stratification": (
                "Assess for pyelonephritis and urinary retention:\n"
                "- High fever + flank pain = pyelonephritis → HIGH\n"
                "- Complete inability to urinate = acute retention → HIGH\n"
                "- UTI symptoms + pregnancy = higher risk → urgent\n"
                "- Hematuria + flank pain = kidney stone → urgent (but check for infection)"
            ),
            "investigation_strategy": (
                "1. Any fever or chills?\n"
                "2. Any flank pain (pain in your back on either side)?\n"
                "3. Can you urinate at all? Or complete inability?\n"
                "IF high fever + flank pain → emergency_suspected (pyelonephritis)"
            ),
            "danger_combinations": [
                "high fever + flank pain + chills → pyelonephritis → ER",
                "UTI + high fever + confusion → urosepsis → ER",
                "complete urinary retention + pain → acute retention → ER",
                "hematuria + severe flank pain + fever → infected stone → ER",
            ],
            "pmh_modifiers": [
                "Pregnant + UTI symptoms → lower threshold for treatment",
                "Diabetic + UTI → higher risk of complicated infection",
                "Recurrent UTIs → may still be serious if systemic symptoms present",
            ],
        },
        "screening_questions": [
            {
                "id": "uri_fever_flank",
                "question_en": "Do you have a fever or chills? Any pain in your back on either side?",
                "question_vi": "Ban co sot hoac lanh run khong? Co dau o lung hai ben hong khong?",
                "rationale": "Screen for pyelonephritis — fever + flank pain = kidney infection",
            },
            {
                "id": "uri_retention",
                "question_en": "Can you urinate at all? Or is it completely blocked?",
                "question_vi": "Ban co tieu duoc khong? Hay hoan toan khong tieu duoc?",
                "rationale": "Complete urinary retention = acute emergency",
            },
            {
                "id": "uri_blood",
                "question_en": "Do you see blood in your urine?",
                "question_vi": "Ban co thay mau trong nuoc tieu khong?",
                "rationale": "Hematuria may indicate stones, infection, or malignancy",
            },
        ],
        "safety_netting": {
            "worsening_signs_vi": "Neu sot tang, dau hong lung du doi, khong tieu duoc, hoac lon xon → den cap cuu ngay",
            "worsening_signs_en": "If worsening fever, severe flank pain, inability to urinate, or confusion → go to ER immediately",
            "follow_up": "48 hours",
            "escalation": "115 / 911",
        },
    },

    # --- Tier 1: #10 Fatigue ---
    "fatigue": {
        "id": "fatigue",
        "name_en": "Fatigue / Weakness",
        "name_vi": "Met moi / Yeu",
        "keywords_en": [
            "fatigue", "tired", "exhausted", "weak", "no energy",
            "always tired", "weakness",
        ],
        "keywords_vi": [
            "met moi", "kiet suc", "khong co suc",
            "luc nao cung met", "uon oai",
        ],
        "hpi_additions": [
            "Sudden onset or gradual? When did it start?",
            "Sleep quality and quantity — hours per night?",
            "Weight changes? Appetite changes?",
            "Exercise tolerance — has it gotten worse?",
            "Feeling sad or losing interest in things? (Depression overlap)",
            "Diet — any nutritional concerns?",
            "Heavy periods? (if applicable — iron deficiency)",
            "Any new medications recently?",
        ],
        "relevant_oldcarts": ["onset", "duration", "aggravating", "alleviating", "timing", "severity"],
        "red_flags": [
            {
                "id": "sudden_weakness",
                "pattern_en": "Sudden onset weakness (especially one-sided) — stroke",
                "pattern_vi": "Yeu dot ngot (dac biet mot ben) — dot quy",
                "action": "911",
                "message_en": "Sudden one-sided weakness could be a stroke. Please call 911 immediately.",
                "message_vi": "Yeu dot ngot mot ben co the la dot quy. Vui long goi 911 ngay.",
                "keywords": [
                    "sudden weakness", "one-sided", "one side",
                    "yeu dot ngot", "mot ben", "nua nguoi",
                ],
            },
        ],
        "ros_focus": ["constitutional", "endocrine", "hematologic", "cardiac", "psychiatric"],
        "cultural_notes": (
            "Vietnamese patients may describe fatigue as 'yeu than' (weak kidneys) — "
            "a traditional concept that can mean fatigue, lower back pain, or sexual dysfunction. "
            "Acknowledge and ask follow-up questions."
        ),
        "priority_order": "standard",
        "clinical_reasoning": {
            "risk_stratification": (
                "Assess for stroke and severe anemia:\n"
                "- Sudden onset weakness (especially one-sided) = stroke → CRITICAL\n"
                "- Fatigue + pallor + tachycardia = severe anemia → HIGH\n"
                "- Fatigue + confusion = multiple dangerous causes → HIGH\n"
                "- Fatigue + weight loss + night sweats = malignancy concern → urgent"
            ),
            "investigation_strategy": (
                "1. Did the weakness come on SUDDENLY? Especially one side?\n"
                "2. Any confusion, vision changes, speech difficulty?\n"
                "3. Any lightheadedness, racing heart, or pallor?\n"
                "IF sudden + one-sided → emergency_suspected (stroke)\n"
                "IF confusion + other symptoms → emergency_suspected"
            ),
            "danger_combinations": [
                "sudden weakness + one-sided → stroke → 911",
                "fatigue + confusion + fever → sepsis/meningitis → ER",
                "fatigue + racing heart + chest pain → cardiac/PE → ER",
                "fatigue + heavy bleeding (menstrual or GI) + dizziness → severe anemia → ER",
                "progressive weakness ascending from legs → Guillain-Barré → ER",
            ],
            "pmh_modifiers": [
                "Known cancer + new fatigue + weight loss → disease progression concern",
                "Heart failure + worsening fatigue → decompensation concern",
                "Diabetes + fatigue + confusion → hypoglycemia/DKA concern",
            ],
        },
        "screening_questions": [
            {
                "id": "fatigue_sudden_onesided",
                "question_en": "Did the weakness come on SUDDENLY, especially on one side of your body?",
                "question_vi": "Su yeu co den DOT NGOT khong, dac biet la o mot ben nguoi?",
                "rationale": "Sudden one-sided weakness = stroke until proven otherwise",
            },
            {
                "id": "fatigue_neuro",
                "question_en": "Any confusion, vision changes, difficulty speaking, or numbness?",
                "question_vi": "Ban co bi lon xon, thay doi thi luc, kho noi, hoac te khong?",
                "rationale": "Neurological deficits with fatigue = stroke/mass",
            },
            {
                "id": "fatigue_cardiac",
                "question_en": "Any chest pain, racing heart, or feeling faint?",
                "question_vi": "Ban co dau nguc, tim dap nhanh, hoac cam giac sap ngat khong?",
                "rationale": "Cardiac causes of fatigue — anemia, heart failure, PE",
            },
        ],
        "safety_netting": {
            "worsening_signs_vi": "Neu yeu dot ngot mot ben, lon xon, kho noi, dau nguc, hoac ngat → goi 115 ngay",
            "worsening_signs_en": "If sudden one-sided weakness, confusion, speech difficulty, chest pain, or fainting → call 911",
            "follow_up": "48 hours",
            "escalation": "115 / 911",
        },
    },

    # --- Tier 2: #14 Chest Pain (included for safety criticality) ---
    "chest_pain": {
        "id": "chest_pain",
        "name_en": "Chest Pain",
        "name_vi": "Dau nguc",
        "keywords_en": [
            "chest pain", "chest tightness", "chest pressure",
            "chest hurts", "heart pain",
            "shortness of breath", "difficulty breathing",
        ],
        "keywords_vi": [
            "dau nguc", "tuc nguc", "nang nguc", "dau tim",
            "dau nguc trai",
            "kho tho",  # dyspnea often presents with chest pain
        ],
        "hpi_additions": [
            "SAFETY Q1: Is the chest pain happening RIGHT NOW?",
            "SAFETY Q2: Are you also having shortness of breath, sweating, nausea, or pain in your jaw/arm/back?",
            "SAFETY Q3: Do you have a history of heart disease, stents, or bypass surgery?",
            "Location — center, left, right?",
            "Character — pressure/squeezing vs sharp/stabbing vs burning?",
            "Does it spread to your arm, jaw, back, or shoulder?",
            "How long does it last — seconds, minutes, or hours?",
            "Can you reproduce it by pressing on the area?",
            "Related to exertion, rest, breathing, eating, or position?",
            "Sweating, lightheadedness, palpitations, fainting?",
            "Similar episodes before? What was diagnosed?",
            "Recent illness, cough, fever?",
            "GERD symptoms — worse after meals, relieved by antacids?",
            "Risk factors: smoking, diabetes, high BP, high cholesterol, family history of early heart disease?",
        ],
        "relevant_oldcarts": ["onset", "location", "duration", "character", "aggravating", "alleviating", "timing", "severity"],
        "red_flags": [
            {
                "id": "acs_active",
                "pattern_en": "Active chest pain + diaphoresis/dyspnea/syncope",
                "pattern_vi": "Dau nguc dang xay ra + do mo hoi/kho tho/ngat",
                "action": "911",
                "message_en": "Please call 911 immediately. Your chest pain symptoms need emergency evaluation.",
                "message_vi": "Vui long goi 911 ngay lap tuc. Dau nguc co the la dau hieu nghiem trong.",
                "keywords": [
                    "chest pain now", "sweating", "can't breathe",
                    "dau nguc ngay", "do mo hoi", "kho tho",
                ],
            },
            {
                "id": "aortic_dissection",
                "pattern_en": "Tearing/ripping chest pain radiating to back",
                "pattern_vi": "Dau nguc nhu xe/rach lan ra lung",
                "action": "911",
                "message_en": "Tearing chest pain radiating to your back needs immediate emergency care. Please call 911.",
                "message_vi": "Dau nguc nhu xe lan ra lung can cap cuu ngay. Vui long goi 911.",
                "keywords": [
                    "tearing", "ripping", "radiating to back",
                    "xe", "rach", "lan ra lung",
                ],
            },
            {
                "id": "chest_pain_with_leg_swelling",
                "pattern_en": "Chest pain + unilateral leg swelling (PE)",
                "pattern_vi": "Dau nguc + sung mot chan (thuyen tac phoi)",
                "action": "911",
                "message_en": "Chest pain with leg swelling could indicate a blood clot. Please call 911.",
                "message_vi": "Dau nguc kem sung chan co the la cuc mau dong. Vui long goi 911.",
                "keywords": [
                    "leg swelling", "swollen leg", "one leg",
                    "sung chan", "phu chan",
                ],
            },
        ],
        "ros_focus": ["cardiovascular", "pulmonary", "GI", "musculoskeletal", "psychiatric"],
        "cultural_notes": (
            "Chest pain is the HIGHEST-STAKES triage complaint. "
            "The AI must err heavily toward escalation. "
            "If there is ANY ambiguity about whether the pain could be cardiac, "
            "recommend urgent/ER evaluation. "
            "Vietnamese emergency: 'Dau nguc co the la dau hieu nghiem trong. Xin hay goi 911 ngay lap tuc.'"
        ),
        "priority_order": "red_flags_first",
        "clinical_reasoning": {
            "risk_stratification": (
                "Evaluate using modified HEART score approach:\n"
                "- History: typical anginal features? (pressure/squeezing, exertional, relieved by rest)\n"
                "- Age: >45M or >55F increases risk\n"
                "- Risk factors: DM, HTN, hyperlipidemia, smoking, family CAD <55\n"
                "- Character: pressure/squeezing (cardiac) vs sharp/pleuritic vs burning (GERD)\n"
                "→ Typical + ≥2 risk factors = HIGH risk\n"
                "→ Atypical + 0 risk factors = LOW risk\n"
                "→ Active pain + ANY associated symptom = treat as HIGH until proven otherwise"
            ),
            "investigation_strategy": (
                "MANDATORY first 3 questions (safety screen — ask BEFORE any HPI):\n"
                "1. Is the chest pain happening RIGHT NOW? → acute vs past\n"
                "2. Associated symptoms? (SOB, sweating, nausea, radiation to arm/jaw/back)\n"
                "3. History of heart disease, stents, or bypass?\n\n"
                "IF active pain + ≥1 associated symptom → emergency_suspected\n"
                "IF resolved + no associated → risk=moderate, continue HPI\n"
                "IF active + no associated + no risk factors → risk=moderate, ask 1 more"
            ),
            "danger_combinations": [
                "chest pain + dyspnea + diaphoresis → likely ACS → 911",
                "chest pain + syncope → unstable cardiac → 911",
                "tearing chest pain + radiating to back → aortic dissection → 911",
                "chest pain + unilateral leg swelling → PE → 911",
                "chest pain + palpitations + near-syncope → dangerous arrhythmia → 911",
                "chest pain + prior MI/stents + any associated → high risk ACS → 911",
            ],
            "pmh_modifiers": [
                "Known CAD / prior MI / stents → ANY chest pain is higher baseline risk",
                "On blood thinners → bleeding risk if intervention needed",
                "Cocaine/stimulant use → coronary vasospasm risk even in young patients",
                "Family history of sudden cardiac death → lower threshold for concern",
            ],
        },
        "screening_questions": [
            {
                "id": "cp_active_now",
                "question_en": "Is the chest pain happening RIGHT NOW?",
                "question_vi": "Ban co dang bi dau nguc NGAY LUC NAY khong?",
                "rationale": "Active ACS needs immediate action — timing is critical",
            },
            {
                "id": "cp_associated",
                "question_en": "Are you also having shortness of breath, sweating, nausea, or pain spreading to your jaw, arm, or back?",
                "question_vi": "Ban co bi kho tho, do mo hoi, buon non, hoac dau lan ra ham/tay/lung khong?",
                "rationale": "Associated symptoms with chest pain = ACS until proven otherwise",
            },
            {
                "id": "cp_cardiac_history",
                "question_en": "Do you have a history of heart disease, stents, or bypass surgery?",
                "question_vi": "Ban co tien su benh tim, dat stent, hoac phau thuat bypass khong?",
                "rationale": "Prior CAD dramatically increases probability of ACS",
            },
        ],
        "safety_netting": {
            "worsening_signs_vi": "Neu dau nguc tang len, kho tho, dau lan ra tay/ham/lung, do mo hoi, hoac ngat → goi 115 ngay",
            "worsening_signs_en": "If chest pain worsens, SOB develops, pain radiates to arm/jaw/back, sweating, or fainting → call 911",
            "follow_up": "24 hours",
            "escalation": "115 / 911",
        },
    },
}

# Fallback protocol for unclassified complaints
FALLBACK_PROTOCOL: ComplaintProtocol = {
    "id": "general",
    "name_en": "General Complaint",
    "name_vi": "Trieu chung chung",
    "keywords_en": [],
    "keywords_vi": [],
    "hpi_additions": [
        "Any associated symptoms?",
        "Have you had similar problems before?",
        "What have you already tried? (OTC meds, home remedies, traditional treatments?)",
        "How is this affecting your daily life or work?",
    ],
    "relevant_oldcarts": list(OLDCARTS_ALL),
    "red_flags": [],
    "ros_focus": ["constitutional"],
    "cultural_notes": (
        "For unclassified complaints, be thorough with OLDCARTS and ask about "
        "traditional Vietnamese remedies the patient may have tried."
    ),
    "priority_order": "standard",
    "clinical_reasoning": {
        "risk_stratification": (
            "For unclassified complaints, apply general emergency principles:\n"
            "- Any trauma / injury with significant mechanism = at minimum MODERATE\n"
            "- Any altered consciousness or confusion = HIGH\n"
            "- Any uncontrolled bleeding = HIGH\n"
            "- Any difficulty breathing = HIGH\n"
            "- Use your clinical judgment — if something sounds dangerous, it probably is"
        ),
        "investigation_strategy": (
            "1. Is this an acute event or chronic/ongoing?\n"
            "2. Any danger signs: breathing difficulty, bleeding, confusion, chest pain?\n"
            "3. Any recent trauma or injury?\n"
            "IF any danger sign present → emergency_suspected"
        ),
        "danger_combinations": [
            "any complaint + altered consciousness → HIGH",
            "any complaint + uncontrolled bleeding → HIGH",
            "any complaint + difficulty breathing → HIGH",
            "significant trauma + any symptom → HIGH",
        ],
        "pmh_modifiers": [
            "Elderly + any acute change → lower threshold for concern",
            "Multiple comorbidities + acute complaint → higher risk",
        ],
    },
    "screening_questions": [
        {
            "id": "gen_breathing",
            "question_en": "Are you having any difficulty breathing?",
            "question_vi": "Ban co dang kho tho khong?",
            "rationale": "Breathing difficulty is always high risk regardless of complaint",
        },
        {
            "id": "gen_bleeding",
            "question_en": "Any uncontrolled bleeding or significant injury?",
            "question_vi": "Ban co dang chay mau khong kiem soat hoac chan thuong nang khong?",
            "rationale": "Active bleeding / trauma needs immediate assessment",
        },
        {
            "id": "gen_confusion",
            "question_en": "Are you feeling confused or having trouble thinking clearly?",
            "question_vi": "Ban co cam thay lon xon hoac kho suy nghi ro rang khong?",
            "rationale": "Altered mental status = many dangerous causes",
        },
    ],
    "safety_netting": {
        "worsening_signs_vi": "Neu kho tho, dau nguc, chay mau khong ngung, lon xon, hoac ngat → goi 115 ngay",
        "worsening_signs_en": "If breathing difficulty, chest pain, uncontrolled bleeding, confusion, or fainting → call 911",
        "follow_up": "48 hours",
        "escalation": "115 / 911",
    },
}


# === Classification ===


def classify_chief_complaint(text: str) -> str:
    """Classify patient's chief complaint text into a protocol category.

    Uses keyword matching against each protocol's keywords.
    Scores by total matched keyword character length (longer matches = more specific).
    Supports both Vietnamese with diacritics and ASCII-folded input.
    Returns protocol ID (e.g., "hypertension", "chest_pain") or "general" if no match.
    """
    text_lower = text.lower()
    text_ascii = _strip_vietnamese_diacritics(text_lower)

    # Check each protocol's keywords
    best_match: str | None = None
    best_score = 0

    for protocol_id, protocol in PROTOCOLS.items():
        score = 0
        for kw in protocol["keywords_en"] + protocol["keywords_vi"]:
            kw_lower = kw.lower()
            # Skip very short keywords (< 3 chars) to avoid false positives
            # from partial word matches (e.g., "oi" in "toi", "met" in "something")
            if len(kw_lower) < 3:
                continue
            # Match against both original text and ASCII-folded version
            if kw_lower in text_lower or kw_lower in text_ascii:
                # Weight by keyword length — longer = more specific
                score += len(kw_lower)
        if score > best_score:
            best_score = score
            best_match = protocol_id

    return best_match if best_match and best_score > 0 else "general"


def get_complaint_protocol(category: str | None) -> ComplaintProtocol:
    """Get the complaint protocol for a given category.

    Returns the specific protocol or FALLBACK_PROTOCOL for unknown/general categories.
    """
    if category and category in PROTOCOLS:
        return PROTOCOLS[category]
    return FALLBACK_PROTOCOL


def get_relevant_oldcarts(protocol: ComplaintProtocol) -> list[str]:
    """Return the OLDCARTS fields relevant for a protocol.

    Falls back to all 8 fields if 'relevant_oldcarts' is not defined.
    """
    return protocol.get("relevant_oldcarts", list(OLDCARTS_ALL))
