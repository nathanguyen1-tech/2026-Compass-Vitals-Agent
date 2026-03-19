"""Pydantic schemas cho Sessions history API."""

from pydantic import BaseModel


class SessionSummary(BaseModel):
    session_id: str
    created_at: str
    updated_at: str
    status: str
    soap_note_ready: bool
    care_plan_ready: bool
    primary_diagnosis: str | None
    severity: str | None
    message_count: int
