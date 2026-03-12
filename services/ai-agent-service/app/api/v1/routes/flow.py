"""Flow API endpoints — manage the multi-agent care flow pipeline.

POST /flow/{session_id}/run       — trigger care flow (Screening → Proposer → Critic)
GET  /flow/{session_id}/status    — get current flow state
GET  /flow/{session_id}/care-plan — get generated care plan
GET  /flow/{session_id}/clinical-summary — get structured clinical summary for MD
GET  /flow/{session_id}/clinical-summary-v2 — LLM-generated clinical narrative for MD
GET  /flow/{session_id}/soap-note — get SOAP note narrative for MD
"""

import structlog
from fastapi import APIRouter, HTTPException

from app.agents.care_flow_graph import build_care_flow_graph
from app.agents.care_plan_generator import generate_care_plan
from app.agents.clinical_summary_generator import generate_clinical_summary
from app.agents.clinical_summary_v2_generator import generate_clinical_summary_v2
from app.agents.soap_note_generator import generate_soap_note
from app.api.v1.schemas.clinical_summary_v2 import ClinicalSummaryV2Response
from app.api.v1.schemas.flow import (
    CarePlanResponse,
    ClinicalSummaryResponse,
    FlowStatusResponse,
    SOAPNoteResponse,
)
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

    # Always generate clinical summary after screening (pure Python — no LLM needed)
    if session.get("screening_result") is not None:
        clinical_summary = generate_clinical_summary(session, session_id)
        session["_clinical_summary"] = clinical_summary.model_dump()

        # Generate Clinical Summary v2 (GPT-4 narrative — non-blocking on failure)
        try:
            clinical_summary_v2 = await generate_clinical_summary_v2(
                session, session_id, _gateway, _phi,
            )
            session["_clinical_summary_v2"] = clinical_summary_v2.model_dump()
        except Exception as e:
            logger.error(
                "clinical_summary_v2.generation_failed",
                session_id=session_id,
                error=str(e),
            )

    # Generate care plan + SOAP note after screening completes
    # (even if critic didn't approve — clinician still needs to see the data)
    care_plan = None
    if session.get("screening_result") is not None:
        care_plan = generate_care_plan(session, session_id)
        session["_care_plan"] = care_plan.model_dump()

        # Flag needs_human_review if critic didn't approve
        if not session.get("critic_approved"):
            session["needs_human_review"] = True
            session.setdefault(
                "human_review_reason",
                "Critic did not approve — manual physician review required",
            )

        # Generate SOAP note (GPT-4 — non-blocking on failure)
        try:
            soap_note = await generate_soap_note(session, session_id, _gateway, _phi)
            session["_soap_note"] = soap_note.model_dump()
        except Exception as e:
            logger.error("soap.generation_failed", session_id=session_id, error=str(e))

    current_agent = "complete" if care_plan is not None else "critic"

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
        clinical_summary_ready="_clinical_summary" in session,
        clinical_summary_v2_ready="_clinical_summary_v2" in session,
        soap_note_ready="_soap_note" in session,
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
        clinical_summary_ready="_clinical_summary" in session,
        clinical_summary_v2_ready="_clinical_summary_v2" in session,
        soap_note_ready="_soap_note" in session,
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


@router.get("/flow/{session_id}/clinical-summary", response_model=ClinicalSummaryResponse)
async def get_clinical_summary(session_id: str):
    """Get the structured clinical summary (HPI, CC, ROS) for MD review."""
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if "_clinical_summary" not in session:
        # Generate on-demand if screening has been done
        if session.get("screening_result") is None and not session.get("intake_complete"):
            raise HTTPException(
                status_code=404,
                detail="Clinical summary not available — run flow first",
            )
        clinical_summary = generate_clinical_summary(session, session_id)
        session["_clinical_summary"] = clinical_summary.model_dump()

    return ClinicalSummaryResponse(**session["_clinical_summary"])


@router.get(
    "/flow/{session_id}/clinical-summary-v2",
    response_model=ClinicalSummaryV2Response,
)
async def get_clinical_summary_v2(session_id: str):
    """Get the LLM-generated Clinical Summary v2 (HPI, CC, ROS narratives)."""
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if "_clinical_summary_v2" not in session:
        # Generate on-demand if screening has been done
        if session.get("screening_result") is None and not session.get("intake_complete"):
            raise HTTPException(
                status_code=404,
                detail="Clinical summary v2 not available — run flow first",
            )
        if not _gateway or not _phi:
            raise HTTPException(status_code=503, detail="LLM not configured")

        clinical_summary_v2 = await generate_clinical_summary_v2(
            session, session_id, _gateway, _phi,
        )
        session["_clinical_summary_v2"] = clinical_summary_v2.model_dump()

    return ClinicalSummaryV2Response(**session["_clinical_summary_v2"])


@router.get("/flow/{session_id}/soap-note", response_model=SOAPNoteResponse)
async def get_soap_note(session_id: str):
    """Get the SOAP note narrative for MD review."""
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if "_soap_note" not in session:
        # Generate on-demand if care plan exists
        if "_care_plan" not in session:
            raise HTTPException(
                status_code=404,
                detail="SOAP note not available — care plan not yet generated",
            )
        if not _gateway or not _phi:
            raise HTTPException(status_code=503, detail="LLM not configured")

        soap_note = await generate_soap_note(session, session_id, _gateway, _phi)
        session["_soap_note"] = soap_note.model_dump()

    return SOAPNoteResponse(**session["_soap_note"])


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
