"""Flow API endpoints — manage the multi-agent care flow pipeline.

POST /flow/{session_id}/run   — trigger care flow (Screening → Proposer → Critic)
GET  /flow/{session_id}/status — get current flow state
GET  /flow/{session_id}/care-plan — get generated care plan
"""

import structlog
from fastapi import APIRouter, HTTPException

from app.agents.care_flow_graph import build_care_flow_graph
from app.agents.care_plan_generator import generate_care_plan
from app.api.v1.schemas.flow import CarePlanResponse, FlowStatusResponse
from app.config import settings
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()
router = APIRouter()

# Re-use session store from chat module
from app.api.v1.routes.chat import _sessions, _gateway, _phi  # noqa: E402


@router.post("/flow/{session_id}/run", response_model=FlowStatusResponse)
async def run_care_flow(session_id: str):
    """Trigger the care flow pipeline: Screening → Proposer → Critic.

    Requires intake to be complete (at least some messages in the session).
    """
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.get("messages"):
        raise HTTPException(status_code=400, detail="No intake data — chat with intake agent first")

    if not _gateway or not _phi:
        raise HTTPException(status_code=503, detail="LLM not configured — set OPENAI_API_KEY")

    # Mark intake as complete
    session["intake_complete"] = True

    # Initialize flow state fields if not present
    session.setdefault("screening_result", None)
    session.setdefault("severity", None)
    session.setdefault("differential_diagnoses", [])
    session.setdefault("confidence_score", None)
    session.setdefault("confidence_breakdown", None)
    session.setdefault("order_recommendations", [])
    session.setdefault("drug_interactions", [])
    session.setdefault("allergy_alerts", [])
    session.setdefault("critic_validation", None)
    session.setdefault("critic_approved", False)
    session.setdefault("critic_issues", [])
    session.setdefault("_critic_loops", 0)
    session.setdefault("current_station", 0)
    session.setdefault("flow_type", None)
    session.setdefault("needs_human_review", False)
    session.setdefault("human_review_reason", None)
    session.setdefault("correlation_id", session_id)

    # Build and run the care flow graph
    graph = build_care_flow_graph(_gateway, _phi)

    logger.info("flow.started", session_id=session_id, case_id=session.get("case_id"))

    try:
        result = await graph.ainvoke(session)
    except Exception as e:
        logger.error("flow.failed", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Care flow failed: {e}")

    # Update session with graph results
    for key in [
        "messages", "screening_result", "severity", "differential_diagnoses",
        "confidence_score", "order_recommendations", "drug_interactions",
        "allergy_alerts", "critic_validation", "critic_approved", "critic_issues",
        "_critic_loops", "needs_human_review", "human_review_reason", "is_emergency",
    ]:
        if key in result:
            session[key] = result[key]

    # Generate care plan if critic approved
    care_plan = None
    if session.get("critic_approved"):
        care_plan = generate_care_plan(session, session_id)
        session["_care_plan"] = care_plan.model_dump()

    current_agent = "complete" if session.get("critic_approved") else "critic"

    logger.info(
        "flow.completed",
        session_id=session_id,
        severity=session.get("severity"),
        critic_approved=session.get("critic_approved"),
        care_plan_ready=care_plan is not None,
    )

    return FlowStatusResponse(
        session_id=session_id,
        current_agent=current_agent,
        intake_complete=True,
        screening_complete=session.get("screening_result") is not None,
        proposer_complete=len(session.get("order_recommendations", [])) > 0,
        critic_complete=session.get("critic_validation") is not None,
        critic_approved=session.get("critic_approved"),
        care_plan_ready=care_plan is not None,
        is_emergency=session.get("is_emergency", False),
        severity=session.get("severity"),
    )


@router.get("/flow/{session_id}/status", response_model=FlowStatusResponse)
async def get_flow_status(session_id: str):
    """Get current state of the care flow pipeline."""
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return FlowStatusResponse(
        session_id=session_id,
        current_agent=_determine_current_agent(session),
        intake_complete=session.get("intake_complete", False),
        screening_complete=session.get("screening_result") is not None,
        proposer_complete=len(session.get("order_recommendations", [])) > 0,
        critic_complete=session.get("critic_validation") is not None,
        critic_approved=session.get("critic_approved"),
        care_plan_ready="_care_plan" in session,
        is_emergency=session.get("is_emergency", False),
        severity=session.get("severity"),
    )


@router.get("/flow/{session_id}/care-plan", response_model=CarePlanResponse)
async def get_care_plan(session_id: str):
    """Get the generated care plan."""
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if "_care_plan" not in session:
        raise HTTPException(status_code=404, detail="Care plan not yet generated — run flow first")

    return CarePlanResponse(**session["_care_plan"])


def _determine_current_agent(session: dict) -> str:
    """Determine which agent is currently active based on session state."""
    if session.get("critic_approved") or "_care_plan" in session:
        return "complete"
    if session.get("critic_validation") is not None:
        return "critic"
    if session.get("order_recommendations"):
        return "proposer"
    if session.get("screening_result") is not None:
        return "screening"
    if session.get("intake_complete"):
        return "screening"  # Screening hasn't run yet
    return "intake"
