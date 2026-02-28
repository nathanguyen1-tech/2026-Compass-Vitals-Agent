"""PHI De-identification Pipeline — HIPAA Safe Harbor method.

De-identify PHI trước mọi LLM call. Re-identify sau khi nhận response.
PHI không bao giờ được gửi tới external LLM APIs.
"""

import json
import re
import uuid

import structlog
from cryptography.fernet import Fernet

logger = structlog.get_logger()

# 18 HIPAA Safe Harbor PHI patterns
PHI_PATTERNS: dict[str, re.Pattern] = {
    "vietnamese_name": re.compile(
        r"\b(Nguyễn|Trần|Lê|Phạm|Hoàng|Huỳnh|Phan|Vũ|Võ|Đặng|Bùi|Đỗ|Hồ|Ngô|Dương|Lý)"
        r"\s+\w+(\s+\w+)?\b"
    ),
    "name": re.compile(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b(\+1\s?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"),
    "date_of_birth": re.compile(r"\b(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/\d{4}\b"),
    "address": re.compile(r"\b\d+\s[A-Z][a-z]+\s(St|Ave|Blvd|Rd|Dr|Ln|Ct|Way)\b"),
    "zip_code": re.compile(r"\b\d{5}(-\d{4})?\b"),
    "mrn": re.compile(r"\b(MRN|mrn)[- ]?\d{4,}\b"),
    "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
}


class PHIDeidentifier:
    """De-identify PHI trước khi gửi LLM. Re-identify sau khi nhận response."""

    def __init__(self, encryption_key: str):
        self.fernet = Fernet(encryption_key.encode())

    def deidentify(self, text: str) -> tuple[str, dict]:
        """De-identify text. Trả về (de-identified_text, mapping)."""
        mapping: dict[str, dict] = {}
        result = text

        for phi_type, pattern in PHI_PATTERNS.items():
            for match in pattern.finditer(result):
                original = match.group()
                if original not in mapping:
                    pseudonym = f"[REF-{uuid.uuid4().hex[:8]}]"
                    mapping[original] = {
                        "pseudonym": pseudonym,
                        "phi_type": phi_type,
                    }

        # Replace all found PHI with pseudonyms
        for original, info in mapping.items():
            result = result.replace(original, info["pseudonym"])

        if mapping:
            logger.info(
                "phi.deidentified",
                phi_types_found=[v["phi_type"] for v in mapping.values()],
                count=len(mapping),
            )

        return result, mapping

    def reidentify(self, text: str, mapping: dict) -> str:
        """Re-identify text (chỉ cho internal use — MD dashboard display)."""
        result = text
        for original, info in mapping.items():
            result = result.replace(info["pseudonym"], original)
        return result

    def contains_phi(self, text: str) -> bool:
        """Kiểm tra text có chứa PHI không (dùng trong PHI Verification Gate)."""
        for phi_type, pattern in PHI_PATTERNS.items():
            if pattern.search(text):
                return True
        return False

    def encrypt_mapping(self, mapping: dict) -> bytes:
        """Mã hóa mapping để lưu vào DB."""
        return self.fernet.encrypt(json.dumps(mapping).encode())

    def decrypt_mapping(self, encrypted: bytes) -> dict:
        """Giải mã mapping từ DB."""
        return json.loads(self.fernet.decrypt(encrypted).decode())
