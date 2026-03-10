"""Tests for Emergency Detector — Vietnamese + English emergency symptom detection."""

from app.agents.tools.emergency_detector import (
    detect_emergency,
    detect_emergency_with_negation,
    detect_high_temperature,
    get_emergency_keywords_found,
)


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


# === Temperature-based emergency detection ===


class TestHighTemperatureDetection:
    """Tests for numeric temperature detection in emergency detector."""

    # --- Celsius patterns ---

    def test_42_do_c(self):
        """42°C should trigger emergency."""
        result = detect_high_temperature("toi bi sot 42 do C")
        assert result is not None
        assert result["value"] == 42.0
        assert result["unit"] == "C"

    def test_42_degree_symbol(self):
        """42°C with degree symbol."""
        result = detect_high_temperature("nhiet do 42°C")
        assert result is not None
        assert result["value"] == 42.0

    def test_40_5_celsius(self):
        """40.5°C — above threshold."""
        result = detect_high_temperature("sot 40.5 do C")
        assert result is not None
        assert result["value"] == 40.5

    def test_40_exact_threshold(self):
        """Exactly 40°C should trigger."""
        result = detect_high_temperature("nhiet do 40 do C")
        assert result is not None
        assert result["value"] == 40.0

    def test_41_do_c_uppercase(self):
        """41 DO C with mixed case."""
        result = detect_high_temperature("sot 41 DO C")
        assert result is not None
        assert result["value"] == 41.0

    def test_sot_42_context_pattern(self):
        """'sot 42' — Vietnamese context pattern without explicit unit."""
        result = detect_high_temperature("toi sot 42")
        assert result is not None
        assert result["value"] == 42.0

    def test_fever_104_context_pattern(self):
        """'fever 104' — English context, but this is Celsius context."""
        # "fever 104" should NOT match Celsius (too high), should not match without F unit
        # Actually 104 in "fever 104" should be interpreted as needing explicit unit
        # Let's ensure the context pattern handles this correctly
        result = detect_high_temperature("fever 104")
        # 104°C is out of range (>50 sanity check), so should not match as Celsius
        # But it could match as context pattern for Celsius... sanity check prevents it
        assert result is None  # 104 > 50 for Celsius sanity

    # --- Fahrenheit patterns ---

    def test_104_fahrenheit(self):
        """104°F should trigger."""
        result = detect_high_temperature("temperature 104°F")
        assert result is not None
        assert result["value"] == 104.0
        assert result["unit"] == "F"

    def test_106_fahrenheit(self):
        """106°F — dangerously high."""
        result = detect_high_temperature("fever is 106 degrees F")
        assert result is not None
        assert result["value"] == 106.0
        assert result["unit"] == "F"

    # --- Below threshold: should NOT trigger ---

    def test_39_celsius_not_emergency(self):
        """39°C is high but not emergency threshold."""
        result = detect_high_temperature("sot 39 do C")
        assert result is None

    def test_38_5_not_emergency(self):
        """38.5°C — fever but not emergency."""
        result = detect_high_temperature("nhiet do 38.5°C")
        assert result is None

    def test_37_normal(self):
        """37°C is normal temperature."""
        result = detect_high_temperature("nhiet do 37 do C")
        assert result is None

    def test_100_f_not_emergency(self):
        """100°F — low-grade fever, not emergency."""
        result = detect_high_temperature("temp 100°F")
        assert result is None

    # --- No temperature: should NOT trigger ---

    def test_no_temperature_in_text(self):
        """Text without temperature values."""
        result = detect_high_temperature("toi bi dau bung 2 ngay")
        assert result is None

    def test_random_number_not_temperature(self):
        """A random number shouldn't be detected as temperature."""
        result = detect_high_temperature("toi 42 tuoi")
        assert result is None

    # --- Integration with detect_emergency ---

    def test_detect_emergency_triggers_on_42c(self):
        """detect_emergency() should catch 42°C."""
        assert detect_emergency("toi sot 42 do C") is True

    def test_detect_emergency_triggers_on_41c(self):
        """detect_emergency() should catch 41°C."""
        assert detect_emergency("nhiet do 41°C roi") is True

    def test_detect_emergency_no_trigger_39c(self):
        """detect_emergency() should NOT trigger on 39°C alone."""
        assert detect_emergency("sot 39 do C") is False

    def test_get_keywords_includes_temperature(self):
        """get_emergency_keywords_found() should include temperature info."""
        keywords = get_emergency_keywords_found("sot 42 do C")
        assert any("high_temperature" in kw for kw in keywords)

    # --- Vietnamese unicode variations ---

    def test_unicode_do_c(self):
        """Vietnamese with full unicode: 'độ C'."""
        result = detect_high_temperature("sốt 42 độ C")
        assert result is not None
        assert result["value"] == 42.0

    def test_comma_decimal(self):
        """European/Vietnamese comma decimal: 40,5°C."""
        result = detect_high_temperature("nhiet do 40,5 do C")
        assert result is not None
        assert result["value"] == 40.5


# === Expanded keywords tests ===


class TestExpandedKeywords:
    """Tests for newly added emergency keywords."""

    # --- Suicide / Self-harm ---

    def test_tu_tu_unicode(self):
        assert detect_emergency("toi muon tu tu") is False  # "tự tử" not "tu tu"
        assert detect_emergency("toi muon tự tử") is True

    def test_muon_chet_ascii(self):
        assert detect_emergency("toi muon chet") is True

    def test_khong_muon_song_ascii(self):
        assert detect_emergency("toi khong muon song") is True

    def test_want_to_die_en(self):
        assert detect_emergency("I want to die") is True

    def test_kill_myself_en(self):
        assert detect_emergency("I want to kill myself") is True

    def test_suicide_en(self):
        assert detect_emergency("thinking about suicide") is True

    # --- GI hemorrhage ---

    def test_oi_ra_mau_ascii(self):
        assert detect_emergency("toi bi oi ra mau") is True

    def test_non_ra_mau_unicode(self):
        assert detect_emergency("benh nhan nôn ra máu") is True

    def test_di_cau_ra_mau_ascii(self):
        assert detect_emergency("toi di cau ra mau") is True

    def test_vomiting_blood_en(self):
        assert detect_emergency("I am vomiting blood") is True

    def test_bloody_stool_en(self):
        assert detect_emergency("I have bloody stool") is True

    def test_coughing_blood_en(self):
        assert detect_emergency("I am coughing blood") is True

    # --- Anaphylaxis ---

    def test_throat_swelling_en(self):
        assert detect_emergency("my throat swelling is getting worse") is True

    def test_throat_closing_en(self):
        assert detect_emergency("I feel my throat closing") is True

    def test_anaphylaxis_en(self):
        assert detect_emergency("I think I have anaphylaxis") is True

    # --- Overdose ---

    def test_overdose_en(self):
        assert detect_emergency("I took an overdose of pills") is True

    def test_uong_thuoc_qua_lieu_ascii(self):
        assert detect_emergency("toi uong thuoc qua lieu") is True


# === Negation-aware detection tests ===


class TestNegationDetection:
    """Tests for detect_emergency_with_negation()."""

    # --- Negation should prevent emergency ---

    def test_negated_chest_pain_en(self):
        """'I do not have chest pain' should NOT trigger."""
        assert detect_emergency_with_negation("I do not have chest pain") is False

    def test_negated_dont_have_en(self):
        """'I don't have chest pain' should NOT trigger."""
        assert detect_emergency_with_negation("I don't have chest pain") is False

    def test_negated_khong_bi_vi(self):
        """'toi khong bi dau nguc' should NOT trigger."""
        assert detect_emergency_with_negation("toi khong bi đau ngực") is False

    def test_negated_deny_en(self):
        """'denies chest pain' should NOT trigger."""
        assert detect_emergency_with_negation("patient denies chest pain") is False

    def test_negated_negative_for_en(self):
        """'negative for difficulty breathing' should NOT trigger."""
        assert detect_emergency_with_negation("negative for difficulty breathing") is False

    # --- Non-negated should still trigger ---

    def test_non_negated_chest_pain(self):
        assert detect_emergency_with_negation("I have severe chest pain") is True

    def test_non_negated_kho_tho(self):
        assert detect_emergency_with_negation("toi bi khó thở qua") is True

    def test_non_negated_suicide(self):
        assert detect_emergency_with_negation("I want to kill myself") is True

    # --- Temperature not affected by negation ---

    def test_temperature_ignores_negation(self):
        """Vital signs bypass negation — dangerously high temp always triggers."""
        assert detect_emergency_with_negation("I don't have sot 42 do C") is True

    # --- Normal text should not trigger ---

    def test_normal_text_no_trigger(self):
        assert detect_emergency_with_negation("I have a mild headache for 2 days") is False
