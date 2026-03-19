"""Chat V4 API endpoint — POST /api/v1/chat-v4.

Single LLM "Senior Doctor" architecture.
Runs on port 8004.
"""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter
from langchain_core.messages import HumanMessage

from app.agents.intake_agent_v4 import intake_node_v4
from app.api.v1.schemas.chat import ChatRequest, ChatResponse
from app.config import settings
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()
router = APIRouter()

_sessions_v4: dict[str, dict] = {}

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


@router.post("/chat-v4", response_model=ChatResponse)
async def chat_v4(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    case_id = str(uuid.uuid4())

    if session_id not in _sessions_v4:
        _sessions_v4[session_id] = {
            "messages": [],
            "case_id": case_id,
            "patient_id": str(uuid.uuid4()),
            "organization_id": "compass",
            "intake_tracker": None,
            "intake_data": None,
            "intake_complete": False,
            "is_emergency": False,
            "detected_language": "vi",
            "cultural_expressions": [],
            "confirmed_facts": {},
            "turn_count": 0,
            # V3 fields (kept for state compat)
            "differential_tracker": None,
            "last_asked_field": None,
            "narrative_done": False,
            "existing_history": None,
            "screening_result": None,
            "severity": None,
            "differential_diagnoses": [],
            "order_recommendations": [],
            "drug_interactions": [],
            "allergy_alerts": [],
            "critic_validation": None,
            "critic_approved": False,
            "critic_issues": [],
            "confidence_score": None,
            "confidence_breakdown": None,
            "current_station": 0,
            "flow_type": None,
            "needs_human_review": False,
            "human_review_reason": None,
            "_critic_loops": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "correlation_id": str(uuid.uuid4()),
        }

    session = _sessions_v4[session_id]

    if request.message:
        session["messages"].append(HumanMessage(content=request.message))

    from app.domain.services.phi_deidentifier import PHIDeidentifier as _PHI
    phi = _phi or _PHI(encryption_key=None)

    result = await intake_node_v4(state=session, llm_gateway=_gateway, phi_deidentifier=phi)

    new_messages = result.get("messages", [])
    session["messages"].extend(new_messages)
    session["intake_tracker"] = result.get("intake_tracker", session.get("intake_tracker"))
    session["intake_data"] = result.get("intake_data", session.get("intake_data"))
    session["intake_complete"] = result.get("intake_complete", session.get("intake_complete", False))
    session["is_emergency"] = result.get("is_emergency", False)
    session["detected_language"] = result.get("detected_language", session.get("detected_language", "vi"))
    session["cultural_expressions"] = result.get("cultural_expressions", session.get("cultural_expressions", []))
    session["confirmed_facts"] = result.get("confirmed_facts", session.get("confirmed_facts", {}))
    session["turn_count"] = result.get("turn_count", session.get("turn_count", 0))

    ai_response = ""
    if new_messages:
        last_msg = new_messages[-1]
        ai_response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    return ChatResponse(
        session_id=session_id,
        response=ai_response,
        agent_state="intake_v4",
        is_complete=session.get("intake_complete", False),
        detected_language=session.get("detected_language", "vi"),
        is_emergency=session.get("is_emergency", False),
        cultural_expressions=session.get("cultural_expressions", []),
    )
