"""Complaint Protocol Data Layer — 11 clinical protocols for intelligent intake.

Each protocol defines complaint-specific HPI questions, red flags,
ROS focus areas, and cultural notes for the Vietnamese American population.
Based on clinical-intake-protocol.md.
"""

from __future__ import annotations

from typing import TypedDict


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
        ],
        "keywords_vi": [
            "tram cam", "lo au", "mat ngu", "buon", "stress",
            "met moi", "khong muon song", "chan nan", "tuyet vong",
            "lo lang", "hoang loan", "khong ngu duoc",
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
    },

    # --- Tier 2: #14 Chest Pain (included for safety criticality) ---
    "chest_pain": {
        "id": "chest_pain",
        "name_en": "Chest Pain",
        "name_vi": "Dau nguc",
        "keywords_en": [
            "chest pain", "chest tightness", "chest pressure",
            "chest hurts", "heart pain",
        ],
        "keywords_vi": [
            "dau nguc", "tuc nguc", "nang nguc", "dau tim",
            "dau nguc trai",
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
}


# === Classification ===


def classify_chief_complaint(text: str) -> str:
    """Classify patient's chief complaint text into a protocol category.

    Uses keyword matching against each protocol's keywords.
    Scores by total matched keyword character length (longer matches = more specific).
    Returns protocol ID (e.g., "hypertension", "chest_pain") or "general" if no match.
    """
    text_lower = text.lower()

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
            if kw_lower in text_lower:
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
