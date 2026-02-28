"""Emergency Detector — Phát hiện triệu chứng khẩn cấp trong text."""

EMERGENCY_KEYWORDS_VI = [
    "đau ngực", "khó thở", "không thở được", "tê nửa người",
    "mất ý thức", "bất tỉnh", "chảy máu nhiều", "co giật",
    "đau ngực trái", "đau lan ra cánh tay", "đột ngột yếu nửa người",
    "méo miệng", "nói ngọng đột ngột", "mất thị lực đột ngột",
    "ngất", "ngất xỉu", "hôn mê",
]

EMERGENCY_KEYWORDS_EN = [
    "chest pain", "difficulty breathing", "can't breathe", "numbness",
    "unconscious", "severe bleeding", "seizure", "stroke signs",
    "sudden weakness", "facial drooping", "slurred speech",
    "loss of consciousness", "fainting", "heart attack",
]


def detect_emergency(text: str) -> bool:
    """Check if text contains emergency symptoms. Returns True if emergency detected."""
    text_lower = text.lower()
    for keyword in EMERGENCY_KEYWORDS_VI + EMERGENCY_KEYWORDS_EN:
        if keyword.lower() in text_lower:
            return True
    return False


def get_emergency_keywords_found(text: str) -> list[str]:
    """Return list of emergency keywords found in text."""
    text_lower = text.lower()
    found = []
    for keyword in EMERGENCY_KEYWORDS_VI + EMERGENCY_KEYWORDS_EN:
        if keyword.lower() in text_lower:
            found.append(keyword)
    return found
