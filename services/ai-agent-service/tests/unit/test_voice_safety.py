"""Tests for voice_safety.py — real-time + post-hoc safety checks."""

import pytest
from unittest.mock import MagicMock

from app.domain.services.voice_safety import (
    quick_emergency_check,
    get_emergency_details,
    extract_cultural_expressions,
    run_post_session_safety,
)


class TestQuickEmergencyCheck:
    def test_detects_vietnamese_emergency(self):
        assert quick_emergency_check("t\u00f4i b\u1ecb \u0111au ng\u1ef1c") is True

    def test_detects_english_emergency(self):
        assert quick_emergency_check("I have chest pain") is True

    def test_no_emergency(self):
        assert quick_emergency_check("t\u00f4i b\u1ecb \u0111au b\u1ee5ng") is False

    def test_empty_text(self):
        assert quick_emergency_check("") is False


class TestGetEmergencyDetails:
    def test_returns_keywords_found(self):
        keywords = get_emergency_details("t\u00f4i b\u1ecb \u0111au ng\u1ef1c v\u00e0 kh\u00f3 th\u1edf")
        assert len(keywords) > 0

    def test_empty_for_non_emergency(self):
        assert get_emergency_details("t\u00f4i b\u1ecb \u0111au b\u1ee5ng") == []


class TestExtractCulturalExpressions:
    def test_detects_nong_trong(self):
        result = extract_cultural_expressions("t\u00f4i b\u1ecb n\u00f3ng trong ng\u01b0\u1eddi")
        assert len(result) > 0

    def test_no_cultural_expression(self):
        result = extract_cultural_expressions("I have a headache")
        assert len(result) == 0


class TestRunPostSessionSafety:
    @pytest.mark.asyncio
    async def test_detects_emergency_in_transcript(self):
        session = {"is_emergency": False, "cultural_expressions": []}
        transcript = [
            {"role": "user", "text": "t\u00f4i b\u1ecb \u0111au ng\u1ef1c", "timestamp": "2026-01-01T00:00:00"},
        ]
        result = await run_post_session_safety(session, transcript, phi_deidentifier=None)
        assert result["is_emergency"] is True
        assert session["is_emergency"] is True

    @pytest.mark.asyncio
    async def test_extracts_cultural_expressions(self):
        session = {"is_emergency": False, "cultural_expressions": []}
        transcript = [
            {"role": "user", "text": "t\u00f4i b\u1ecb n\u00f3ng trong ng\u01b0\u1eddi", "timestamp": "2026-01-01T00:00:00"},
        ]
        result = await run_post_session_safety(session, transcript, phi_deidentifier=None)
        assert len(result["cultural_expressions"]) > 0

    @pytest.mark.asyncio
    async def test_phi_deidentification(self):
        mock_phi = MagicMock()
        mock_phi.deidentify.return_value = ("toi bi dau", {"Nguyen Van A": {"pseudonym": "[REF-abc]", "phi_type": "name"}})

        session = {"is_emergency": False, "cultural_expressions": []}
        transcript = [
            {"role": "user", "text": "toi la Nguyen Van A, toi bi dau", "timestamp": "2026-01-01T00:00:00"},
        ]
        result = await run_post_session_safety(session, transcript, phi_deidentifier=mock_phi)
        assert result["phi_detected"] is True

    @pytest.mark.asyncio
    async def test_empty_transcript(self):
        session = {"is_emergency": False, "cultural_expressions": []}
        result = await run_post_session_safety(session, [], phi_deidentifier=None)
        assert result["is_emergency"] is False

    @pytest.mark.asyncio
    async def test_updates_session(self):
        session = {"is_emergency": False, "cultural_expressions": [], "voice_transcripts": []}
        transcript = [
            {"role": "user", "text": "t\u00f4i b\u1ecb \u0111au b\u1ee5ng", "timestamp": "2026-01-01T00:00:00"},
            {"role": "assistant", "text": "khi n\u00e0o b\u1eaft \u0111\u1ea7u?", "timestamp": "2026-01-01T00:00:01"},
        ]
        await run_post_session_safety(session, transcript, phi_deidentifier=None)
        assert len(session["voice_transcripts"]) == 2
