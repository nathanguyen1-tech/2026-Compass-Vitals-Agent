"""Medical Terminology — Bidirectional Vietnamese ↔ English medical terms."""

# Vietnamese → English medical terms
MEDICAL_TERMS: dict[str, str] = {
    # Triệu chứng
    "đau đầu": "headache",
    "đau bụng": "abdominal pain",
    "sốt": "fever",
    "ho": "cough",
    "khó thở": "dyspnea",
    "buồn nôn": "nausea",
    "nôn": "vomiting",
    "tiêu chảy": "diarrhea",
    "táo bón": "constipation",
    "chóng mặt": "dizziness",
    "mệt mỏi": "fatigue",
    "phát ban": "rash",
    "ngứa": "pruritus",
    "đau ngực": "chest pain",
    "đau khớp": "joint pain",
    "sưng": "swelling/edema",
    "đau lưng": "back pain",
    "đau họng": "sore throat",
    "sổ mũi": "runny nose",
    "nghẹt mũi": "nasal congestion",
    # Bệnh lý
    "tiểu đường": "diabetes mellitus",
    "cao huyết áp": "hypertension",
    "hen suyễn": "asthma",
    "viêm phổi": "pneumonia",
    "viêm ruột thừa": "appendicitis",
    "sỏi thận": "kidney stones/nephrolithiasis",
    "nhiễm trùng đường tiểu": "urinary tract infection",
    # Thuốc
    "thuốc hạ sốt": "antipyretic/acetaminophen",
    "thuốc giảm đau": "analgesic",
    "kháng sinh": "antibiotic",
    "thuốc ho": "cough suppressant",
    # Regional variants
    "cảm cúm": "influenza",
    "cảm": "cold/influenza",
    "bịnh": "disease/illness",
    "bệnh": "disease/illness",
}

# Reverse mapping: English → Vietnamese
ENGLISH_TO_VIETNAMESE: dict[str, str] = {v: k for k, v in MEDICAL_TERMS.items()}


def translate_vi_to_en(term: str) -> str | None:
    """Translate Vietnamese medical term to English. Returns None if not found."""
    return MEDICAL_TERMS.get(term.lower())


def translate_en_to_vi(term: str) -> str | None:
    """Translate English medical term to Vietnamese. Returns None if not found."""
    return ENGLISH_TO_VIETNAMESE.get(term.lower())
