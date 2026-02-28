"""Tests for PHI De-identification Pipeline — 100% coverage required (safety-critical)."""

import pytest
from cryptography.fernet import Fernet

from app.domain.services.phi_deidentifier import PHIDeidentifier


@pytest.fixture
def phi():
    key = Fernet.generate_key().decode()
    return PHIDeidentifier(encryption_key=key)


class TestContainsPHI:
    def test_detects_vietnamese_name(self, phi):
        assert phi.contains_phi("Bệnh nhân Nguyễn Văn An bị đau bụng") is True

    def test_detects_english_name(self, phi):
        assert phi.contains_phi("Patient John Smith has a headache") is True

    def test_detects_ssn(self, phi):
        assert phi.contains_phi("SSN: 123-45-6789") is True

    def test_detects_phone(self, phi):
        assert phi.contains_phi("Call (713) 555-1234") is True

    def test_detects_email(self, phi):
        assert phi.contains_phi("Contact patient@email.com") is True

    def test_detects_dob(self, phi):
        assert phi.contains_phi("DOB: 05/10/1968") is True

    def test_detects_address(self, phi):
        assert phi.contains_phi("Lives at 123 Main St") is True

    def test_detects_zip(self, phi):
        assert phi.contains_phi("Houston TX 77001") is True

    def test_detects_mrn(self, phi):
        assert phi.contains_phi("MRN-001234") is True

    def test_detects_ip(self, phi):
        assert phi.contains_phi("IP: 192.168.1.100") is True

    def test_no_phi_in_clean_text(self, phi):
        assert phi.contains_phi("Tôi bị đau bụng 2 ngày rồi") is False

    def test_no_phi_in_medical_terms(self, phi):
        assert phi.contains_phi("viêm ruột thừa cấp") is False


class TestDeidentify:
    def test_replaces_vietnamese_name(self, phi):
        text = "Bệnh nhân Nguyễn Văn An bị sốt"
        result, mapping = phi.deidentify(text)
        assert "Nguyễn Văn An" not in result
        assert "[REF-" in result
        assert "Nguyễn Văn An" in mapping

    def test_replaces_phone(self, phi):
        text = "Gọi số (713) 555-1234 để liên hệ"
        result, mapping = phi.deidentify(text)
        assert "(713) 555-1234" not in result
        assert "[REF-" in result

    def test_replaces_email(self, phi):
        text = "Email: patient@hospital.com"
        result, mapping = phi.deidentify(text)
        assert "patient@hospital.com" not in result

    def test_replaces_ssn(self, phi):
        text = "SSN là 123-45-6789"
        result, mapping = phi.deidentify(text)
        assert "123-45-6789" not in result

    def test_clean_text_unchanged(self, phi):
        text = "Tôi bị đau đầu mấy ngày"
        result, mapping = phi.deidentify(text)
        assert result == text
        assert mapping == {}

    def test_multiple_phi_replaced(self, phi):
        text = "Nguyễn Văn An, SSN 123-45-6789, email an@test.com"
        result, mapping = phi.deidentify(text)
        assert "Nguyễn Văn An" not in result
        assert "123-45-6789" not in result
        assert "an@test.com" not in result
        assert len(mapping) >= 3


class TestReidentify:
    def test_roundtrip(self, phi):
        original = "Bệnh nhân Nguyễn Văn An bị đau bụng, gọi (713) 555-1234"
        deidentified, mapping = phi.deidentify(original)
        reidentified = phi.reidentify(deidentified, mapping)
        assert reidentified == original


class TestEncryptDecryptMapping:
    def test_roundtrip(self, phi):
        mapping = {
            "Nguyễn Văn An": {"pseudonym": "[REF-abc12345]", "phi_type": "vietnamese_name"},
        }
        encrypted = phi.encrypt_mapping(mapping)
        assert isinstance(encrypted, bytes)
        decrypted = phi.decrypt_mapping(encrypted)
        assert decrypted == mapping
