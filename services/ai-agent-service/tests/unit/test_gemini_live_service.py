"""Tests for GeminiLiveService initialization and config."""

from app.domain.services.gemini_live_service import (
    GeminiLiveService,
    VOICE_SYSTEM_INSTRUCTION,
    SAVE_INTAKE_FIELD_TOOL,
)


class TestGeminiLiveService:
    def test_init(self):
        service = GeminiLiveService(
            api_key="test-key",
            model="test-model",
            voice="Kore",
        )
        assert service.model == "test-model"
        assert service.voice == "Kore"

    def test_system_instruction_contains_oldcarts(self):
        assert "OLDCARTS" in VOICE_SYSTEM_INSTRUCTION
        assert "save_intake_field" in VOICE_SYSTEM_INSTRUCTION

    def test_system_instruction_contains_emergency_keywords(self):
        assert "dau nguc" in VOICE_SYSTEM_INSTRUCTION
        assert "kho tho" in VOICE_SYSTEM_INSTRUCTION

    def test_tool_declaration_has_save_field(self):
        names = [f["name"] for f in SAVE_INTAKE_FIELD_TOOL["function_declarations"]]
        assert "save_intake_field" in names
        assert "mark_intake_complete" in names

    def test_save_field_has_oldcarts_enum(self):
        save_fn = SAVE_INTAKE_FIELD_TOOL["function_declarations"][0]
        field_enum = save_fn["parameters"]["properties"]["field"]["enum"]
        assert "onset" in field_enum
        assert "location" in field_enum
        assert "duration" in field_enum
        assert "severity" in field_enum
        assert "chief_complaint" in field_enum
