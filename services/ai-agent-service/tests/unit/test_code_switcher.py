"""Tests for Code Switcher — language detection vi/en/mixed."""

from app.nlp.code_switcher import CodeSwitcher


def test_detect_vietnamese():
    cs = CodeSwitcher()
    assert cs.detect_language("Tôi bị đau bụng") == "vi"


def test_detect_english():
    cs = CodeSwitcher()
    assert cs.detect_language("I have a headache") == "en"


def test_detect_mixed():
    cs = CodeSwitcher()
    assert cs.detect_language("Con bị fever 3 ngày rồi") == "mixed"


def test_detect_mixed_complex():
    cs = CodeSwitcher()
    assert cs.detect_language("Tôi bị đau họng nuốt very difficult") == "mixed"


def test_normalize_mixed_adds_tag():
    cs = CodeSwitcher()
    result = cs.normalize("Con bị fever 3 ngày rồi")
    assert result.startswith("[CODE-SWITCHING:")


def test_normalize_pure_vi_unchanged():
    cs = CodeSwitcher()
    text = "Tôi bị đau bụng"
    assert cs.normalize(text) == text


def test_normalize_pure_en_unchanged():
    cs = CodeSwitcher()
    text = "I have a stomachache"
    assert cs.normalize(text) == text
