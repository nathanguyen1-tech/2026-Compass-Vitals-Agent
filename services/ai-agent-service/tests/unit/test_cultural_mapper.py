"""Tests for Cultural Mapper — Vietnamese cultural health expression recognition."""

from app.nlp.cultural_mapper import CulturalMapper


def test_detects_nong_trong():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Tôi bị nóng trong người")
    assert len(result) == 1
    assert "inflammation" in result[0]["medical_terms"]


def test_detects_trung_gio():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Tôi bị trúng gió hôm qua")
    assert len(result) == 1
    assert "fever" in result[0]["medical_terms"]


def test_detects_boc_hoa():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Tôi hay bị bốc hỏa")
    assert len(result) == 1
    assert "hot flashes" in result[0]["medical_terms"]


def test_detects_yeu_than():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Bác sĩ nói tôi bị yếu thận")
    assert len(result) == 1
    assert "fatigue" in result[0]["medical_terms"]


def test_no_match_normal_text():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Tôi bị đau bụng 2 ngày")
    assert result == []


def test_multiple_expressions():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Tôi bị nóng trong người và trúng gió")
    assert len(result) == 2


def test_case_insensitive():
    mapper = CulturalMapper()
    result = mapper.map_expressions("tôi bị NÓNG TRONG người")
    assert len(result) == 1
