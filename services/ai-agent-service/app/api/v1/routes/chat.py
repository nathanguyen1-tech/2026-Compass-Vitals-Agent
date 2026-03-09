"""Chat API endpoint — POST /api/v1/chat.

Connects patient messages to the Intake Agent.
"""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter
from langchain_core.messages import HumanMessage

from app.agents.intake_agent import intake_node
from app.api.v1.schemas.chat import ChatRequest, ChatResponse
from app.config import settings
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()
router = APIRouter()

# In-memory session store (will migrate to PostgreSQL + Redis later)
_sessions: dict[str, dict] = {}

# Initialize services
_phi = PHIDeidentifier(encryption_key=settings.phi_encryption_key) if settings.phi_encryption_key else None
_gateway = (
    LLMGateway(
        openai_api_key=settings.openai_api_key,
        phi_deidentifier=_phi,
        primary_model=settings.primary_llm_model,
        screening_model=settings.screening_llm_model,
    )
    if settings.openai_api_key and _phi
    else None
)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a patient chat message through the Intake Agent."""
    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    session = _sessions.get(session_id)

    is_new_session = False
    if session is None:
        is_new_session = True
        session = {
            "messages": [],
            "patient_id": str(uuid.uuid4()),  # Stub — will come from auth
            "case_id": str(uuid.uuid4()),
            "organization_id": str(uuid.uuid4()),
            "intake_data": {},
            "intake_complete": False,
            "is_emergency": False,
            "detected_language": "vi",
            "cultural_expressions": [],
            "voice_transcripts": [],
            "input_mode": "text",
            "intake_tracker": None,
            "existing_history": None,  # Will come from patient profile
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _sessions[session_id] = session

    # For new sessions with empty/greeting-only messages, get the greeting first
    if is_new_session and (not request.message or not request.message.strip()):
        from app.agents.intake_agent import _initial_greeting

        greeting_result = _initial_greeting(session)
        greeting_messages = greeting_result.get("messages", [])
        session["messages"].extend(greeting_messages)
        session["intake_tracker"] = greeting_result.get("intake_tracker")
        session["detected_language"] = greeting_result.get("detected_language", "vi")

        ai_response = ""
        if greeting_messages:
            last_msg = greeting_messages[-1]
            ai_response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        return ChatResponse(
            response=ai_response,
            session_id=session_id,
            agent_state="intake",
            is_complete=False,
            detected_language=session["detected_language"],
            is_emergency=False,
            cultural_expressions=[],
            intake_progress=0.0,
            current_phase="greeting",
        )

    # Add patient message to session
    session["messages"].append(HumanMessage(content=request.message))

    # === Emergency guard: block further intake if session already in emergency ===
    if session.get("is_emergency"):
        logger.info(
            "chat.emergency_session_blocked",
            session_id=session_id,
            case_id=session["case_id"],
        )
        return ChatResponse(
            response=(
                "Phien kham nay da duoc chuyen sang tinh trang khan cap. "
                "Vui long goi 911 hoac den phong cap cuu gan nhat.\n\n"
                "This session has been escalated to emergency status. "
                "Please call 911 or go to the nearest ER."
            ),
            session_id=session_id,
            agent_state="intake",
            is_complete=False,
            detected_language=session.get("detected_language", "vi"),
            is_emergency=True,
            cultural_expressions=session.get("cultural_expressions", []),
            intake_progress=None,
            current_phase="emergency",
        )

    # Run Intake Agent
    if _gateway and _phi:
        result = await intake_node(
            state=session,
            llm_gateway=_gateway,
            phi_deidentifier=_phi,
        )
    else:
        # Fallback if no API key configured
        result = {
            "messages": [
                HumanMessage(
                    content="[LLM not configured] Received: " + request.message
                )
            ],
            "detected_language": "vi",
            "is_emergency": False,
            "cultural_expressions": [],
        }

    # Update session with results
    new_messages = result.get("messages", [])
    session["messages"].extend(new_messages)
    session["detected_language"] = result.get("detected_language", session["detected_language"])
    session["is_emergency"] = result.get("is_emergency", False)
    session["cultural_expressions"] = result.get(
        "cultural_expressions", session["cultural_expressions"]
    )
    session["intake_tracker"] = result.get("intake_tracker", session.get("intake_tracker"))
    session["intake_data"] = result.get("intake_data", session.get("intake_data"))
    session["intake_complete"] = result.get("intake_complete", session.get("intake_complete", False))

    # Extract AI response text
    ai_response = ""
    if new_messages:
        last_msg = new_messages[-1]
        ai_response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    logger.info(
        "chat.processed",
        session_id=session_id,
        case_id=session["case_id"],
        detected_language=session["detected_language"],
        is_emergency=session["is_emergency"],
    )

    # Calculate progress from tracker
    intake_progress = None
    current_phase = None
    tracker_data = session.get("intake_tracker")
    if tracker_data:
        from app.agents.tools.intake_tracker import IntakeTracker

        t = IntakeTracker(data=tracker_data)
        intake_progress = t.get_completeness_score()
        current_phase = t.phase

    return ChatResponse(
        response=ai_response,
        session_id=session_id,
        agent_state="intake",
        is_complete=session.get("intake_complete", False),
        detected_language=session["detected_language"],
        is_emergency=session["is_emergency"],
        cultural_expressions=session["cultural_expressions"],
        intake_progress=intake_progress,
        current_phase=current_phase,
    )
