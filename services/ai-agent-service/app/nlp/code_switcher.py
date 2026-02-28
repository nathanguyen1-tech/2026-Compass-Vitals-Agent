"""Code Switcher — Xử lý code-switching Vietnamese ↔ English."""

import re


# Vietnamese-specific diacritical characters
_VI_CHARS = set(
    "àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợ"
    "ùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆ"
    "ÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ"
)

_EN_WORD_PATTERN = re.compile(r"\b[a-zA-Z]{3,}\b")


class CodeSwitcher:
    """Detect language và normalize mixed Vietnamese-English text."""

    def detect_language(self, text: str) -> str:
        """Phát hiện ngôn ngữ: 'vi', 'en', hoặc 'mixed'."""
        has_vi = any(c in _VI_CHARS for c in text)
        has_en = bool(_EN_WORD_PATTERN.search(text))

        if has_vi and has_en:
            return "mixed"
        elif has_vi:
            return "vi"
        return "en"

    def normalize(self, text: str) -> str:
        """Normalize mixed text để LLM hiểu tốt hơn."""
        language = self.detect_language(text)
        if language == "mixed":
            return f"[CODE-SWITCHING: Vietnamese-English] {text}"
        return text
