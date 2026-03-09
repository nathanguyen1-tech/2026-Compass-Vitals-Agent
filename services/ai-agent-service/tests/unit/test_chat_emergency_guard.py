"""Tests for Chat API emergency session guard.

After a session is flagged as emergency (is_emergency=True),
subsequent messages should be blocked with an emergency notice.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.routes.chat import _sessions, router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear in-memory sessions before each test."""
    _sessions.clear()
    yield
    _sessions.clear()


class TestEmergencySessionGuard:
    @pytest.mark.asyncio
    async def test_blocks_messages_after_emergency(self):
        """After is_emergency=True, subsequent messages should be blocked."""
        # Pre-seed a session that's already in emergency state
        _sessions["emergency-session"] = {
            "messages": [],
            "patient_id": "test-patient",
            "case_id": "test-case",
            "organization_id": "test-org",
            "intake_data": {},
            "intake_complete": False,
            "is_emergency": True,  # Already in emergency
            "detected_language": "vi",
            "cultural_expressions": [],
            "voice_transcripts": [],
            "input_mode": "text",
            "intake_tracker": None,
            "existing_history": None,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "toi van con dau",
                    "session_id": "emergency-session",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_emergency"] is True
        assert "emergency" in data["current_phase"]
        assert "911" in data["response"] or "cap cuu" in data["response"]
