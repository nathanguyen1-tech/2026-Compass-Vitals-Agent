"""Chat V2 API endpoint — POST /api/v1/chat-v2.

Connects patient messages to Intake Agent V2 (trust-LLM architecture).
Runs alongside V1 (/api/v1/chat) for A/B comparison.
"""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter
from langchain_core.messages import HumanMessage

from app.agents.intake_agent_v2 import intake_node_v2, _initial_greeting_v2
from app.api.v1.schemas.chat import ChatRequest, ChatResponse
from app.config import settings
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()
router = APIRouter()

# Separate session store — V2 sessions never mix with V1
_sessions_v2: dict[str, dict] = {}

# Reuse same services
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


@router.post("/chat-v2", response_model=ChatResponse)
async def chat_v2(request: ChatRequest):
    """Process a patient chat message through Intake Agent V2."""
    session_id = request.session_id or str(uuid.uuid4())
    session = _sessions_v2.get(session_id)

    is_new_session = False
    if session is None:
        is_new_session = True
        session = {
            "messages": [],
            "patient_id": str(uuid.uuid4()),
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
            "existing_history": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _sessions_v2[session_id] = session

    # New session with empty message → greeting
    if is_new_session and (not request.message or not request.message.strip()):
        greeting_result = _initial_greeting_v2(session)
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
            agent_state="intake_v2",
            is_complete=False,
            detected_language=session["detected_language"],
            is_emergency=False,
            cultural_expressions=[],
            intake_progress=0.0,
            current_phase="greeting",
        )

    # Add patient message
    session["messages"].append(HumanMessage(content=request.message))

    # Emergency guard
    if session.get("is_emergency"):
        return ChatResponse(
            response=(
                "Phi\u00ean kh\u00e1m n\u00e0y \u0111\u00e3 \u0111\u01b0\u1ee3c chuy\u1ec3n sang t\u00ecnh tr\u1ea1ng kh\u1ea9n c\u1ea5p. "
                "Vui l\u00f2ng g\u1ecdi 911 ho\u1eb7c \u0111\u1ebfn ph\u00f2ng c\u1ea5p c\u1ee9u g\u1ea7n nh\u1ea5t.\n\n"
                "This session has been escalated to emergency status. "
                "Please call 911 or go to the nearest ER."
            ),
            session_id=session_id,
            agent_state="intake_v2",
            is_complete=False,
            detected_language=session.get("detected_language", "vi"),
            is_emergency=True,
            cultural_expressions=session.get("cultural_expressions", []),
            intake_progress=None,
            current_phase="emergency",
        )

    # Run Intake Agent V2
    if _gateway and _phi:
        result = await intake_node_v2(
            state=session,
            llm_gateway=_gateway,
            phi_deidentifier=_phi,
        )
    else:
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

    # Update session
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

    # Extract AI response
    ai_response = ""
    if new_messages:
        last_msg = new_messages[-1]
        ai_response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    logger.info(
        "chat_v2.processed",
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
        agent_state="intake_v2",
        is_complete=session.get("intake_complete", False),
        detected_language=session["detected_language"],
        is_emergency=session["is_emergency"],
        cultural_expressions=session["cultural_expressions"],
        intake_progress=intake_progress,
        current_phase=current_phase,
    )
