"""Tests for Emergency Detector — Vietnamese + English emergency symptom detection."""

from app.agents.tools.emergency_detector import detect_emergency, get_emergency_keywords_found


def test_detects_dau_nguc():
    assert detect_emergency("Tôi bị đau ngực rất nặng") is True


def test_detects_kho_tho():
    assert detect_emergency("Tôi khó thở quá") is True


def test_detects_bat_tinh():
    assert detect_emergency("Bệnh nhân bất tỉnh") is True


def test_detects_chest_pain_en():
    assert detect_emergency("I have severe chest pain") is True


def test_detects_cant_breathe_en():
    assert detect_emergency("I can't breathe") is True


def test_no_emergency_normal_symptoms():
    assert detect_emergency("Tôi bị đau bụng 2 ngày") is False


def test_no_emergency_english():
    assert detect_emergency("I have a mild headache") is False


def test_get_keywords_found():
    keywords = get_emergency_keywords_found("Tôi bị đau ngực và khó thở")
    assert "đau ngực" in keywords
    assert "khó thở" in keywords


def test_get_keywords_empty():
    keywords = get_emergency_keywords_found("Tôi bị đau bụng")
    assert keywords == []
