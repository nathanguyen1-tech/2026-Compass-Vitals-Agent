"""SOAP Note Generator — GPT-4 clinical narrative for MD review.

Unlike care_plan_generator (pure Python), this calls GPT-4 to write
a professional SOAP note from the full CareFlowState.
"""

import json
from datetime import datetime, timezone

import structlog
from langchain_core.messages import HumanMessage

from app.agents.prompts.soap_prompt import SOAP_SYSTEM_PROMPT
from app.agents.state import CareFlowState
from app.api.v1.schemas.flow import SOAPNoteResponse, SOAPSection
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()


def _build_soap_context(state: CareFlowState) -> str:
    """Build comprehensive context from ALL state fields for the SOAP prompt."""
    parts = []

    parts.append(f"CASE ID: {state.get('case_id', 'unknown')}")
    parts.append(f"SEVERITY: {state.get('severity', 'routine')}")
    parts.append(f"DETECTED LANGUAGE: {state.get('detected_language', 'vi')}")

    # --- Intake Data (Subjective source) ---
    intake_data = state.get("intake_data")
    if intake_data:
        parts.append("\n=== INTAKE DATA (for Subjective) ===")
        for key, value in intake_data.items():
            if value is not None:
                parts.append(f"  {key}: {value}")

    # --- Intake Tracker (additional structured fields) ---
    tracker = state.get("intake_tracker")
    if tracker and isinstance(tracker, dict):
        parts.append("\n=== INTAKE TRACKER ===")
        for key, value in tracker.items():
            if value:
                parts.append(f"  {key}: {value}")

    # --- Conversation Excerpts (for HPI narrative) ---
    messages = state.get("messages", [])
    if messages:
        parts.append("\n=== RELEVANT CONVERSATION EXCERPTS ===")
        for msg in messages[-15:]:
            role = "Patient" if isinstance(msg, HumanMessage) else "AI Agent"
            content = msg.content if hasattr(msg, "content") else str(msg)
            parts.append(f"  [{role}]: {content[:500]}")

    # --- Cultural Expressions ---
    cultural = state.get("cultural_expressions", [])
    if cultural:
        parts.append("\n=== CULTURAL EXPRESSIONS ===")
        for expr in cultural:
            if isinstance(expr, dict):
                parts.append(
                    f"  '{expr.get('original', '')}' => {expr.get('medical_meaning', '')}"
                )

    # --- Screening Result (Objective + Assessment source) ---
    screening = state.get("screening_result")
    if screening and isinstance(screening, dict):
        parts.append("\n=== SCREENING RESULT (for Objective/Assessment) ===")
        clinical_impression = screening.get("clinical_impression", "")
        if clinical_impression:
            parts.append(f"  Clinical Impression: {clinical_impression}")
        key_findings = screening.get("key_findings", [])
        if key_findings:
            parts.append(f"  Key Findings: {', '.join(key_findings)}")
        red_flags = screening.get("red_flags", [])
        if red_flags:
            parts.append(f"  Red Flags: {', '.join(red_flags)}")

    # --- Differential Diagnoses ---
    dx_list = state.get("differential_diagnoses", [])
    if dx_list:
        parts.append("\n=== DIFFERENTIAL DIAGNOSES ===")
        for dx in dx_list:
            name = dx.get("name", "Unknown")
            name_vi = dx.get("name_vi", "")
            conf = dx.get("confidence", 0)
            reasoning = dx.get("reasoning", "")
            parts.append(f"  - {name} ({name_vi}) [{conf}%]: {reasoning}")

    # --- Order Recommendations (Plan source) ---
    orders = state.get("order_recommendations", [])
    if orders:
        parts.append("\n=== ORDER RECOMMENDATIONS (for Plan) ===")
        for i, order in enumerate(orders, 1):
            order_type = order.get("type", "unknown")
            parts.append(f"  Order #{i} ({order_type}):")
            for key, value in order.items():
                if key != "type":
                    parts.append(f"    {key}: {value}")

    # --- Drug Interactions ---
    interactions = state.get("drug_interactions", [])
    if interactions:
        parts.append("\n=== DRUG INTERACTIONS ===")
        for inter in interactions:
            pair = inter.get("drug_pair", [])
            sev = inter.get("severity", "unknown")
            desc = inter.get("description", "")
            parts.append(f"  {' + '.join(pair)} [{sev}]: {desc}")

    # --- Allergy Alerts ---
    allergies = state.get("allergy_alerts", [])
    if allergies:
        parts.append("\n=== ALLERGY ALERTS ===")
        for alert in allergies:
            parts.append(f"  - {alert}")

    # --- Critic Validation ---
    critic = state.get("critic_validation")
    if critic and isinstance(critic, dict):
        parts.append("\n=== CRITIC VALIDATION ===")
        parts.append(f"  Status: {critic.get('status', 'unknown')}")
        parts.append(f"  Safety Score: {critic.get('overall_safety_score', 'N/A')}")
        parts.append(f"  Summary: {critic.get('summary', '')}")
        issues = critic.get("issues", [])
        if issues:
            parts.append("  Issues:")
            for issue in issues:
                parts.append(
                    f"    [{issue.get('severity', '')}] "
                    f"{issue.get('category', '')}: "
                    f"{issue.get('description', '')}"
                )

    # --- Flags ---
    if state.get("is_emergency"):
        parts.append("\n*** EMERGENCY CASE ***")

    if state.get("needs_human_review"):
        reason = state.get("human_review_reason", "")
        parts.append(f"\n*** NEEDS HUMAN REVIEW: {reason} ***")

    return "\n".join(parts)


def _parse_soap_response(response_text: str) -> dict:
    """Parse JSON from LLM response with fallback."""
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("soap.json_parse_failed", response_preview=text[:200])
        return {
            "subjective": {"content": response_text, "content_vi": ""},
            "objective": {"content": "Unable to parse structured response.", "content_vi": ""},
            "assessment": {"content": "Unable to parse structured response.", "content_vi": ""},
            "plan": {"content": "Unable to parse structured response.", "content_vi": ""},
            "safety_concerns": ["SOAP note parsing failed — manual review required"],
        }


async def generate_soap_note(
    state: CareFlowState,
    session_id: str,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> SOAPNoteResponse:
    """Generate a SOAP note from the complete CareFlowState using GPT-4."""
    case_id = state.get("case_id", "unknown")

    # === Step 1: Build comprehensive context ===
    soap_context = _build_soap_context(state)

    # === Step 2: PHI De-identification ===
    deidentified_context, phi_mapping = phi_deidentifier.deidentify(soap_context)

    # === Step 3: Build LLM Messages ===
    llm_messages = [
        {"role": "system", "content": SOAP_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Generate a complete SOAP note for the following "
                f"clinical encounter:\n\n{deidentified_context}"
            ),
        },
    ]

    # === Step 4: Call LLM via Gateway ===
    response = await llm_gateway.generate(
        messages=llm_messages,
        agent_type="soap",
        case_id=case_id,
        temperature=0.3,
        max_tokens=4096,
    )

    # === Step 5: Re-identify response ===
    ai_response_text = response.content
    if phi_mapping:
        ai_response_text = phi_deidentifier.reidentify(ai_response_text, phi_mapping)

    # === Step 6: Parse response ===
    parsed = _parse_soap_response(ai_response_text)

    # === Step 7: Build SOAPNoteResponse ===
    safety_concerns = parsed.get("safety_concerns", [])

    critic = state.get("critic_validation") or {}

    # Primary diagnosis from differential
    dx_list = state.get("differential_diagnoses", [])
    primary_dx = ""
    if dx_list:
        primary = max(dx_list, key=lambda d: d.get("confidence", 0))
        primary_dx = primary.get("name", "")

    soap_note = SOAPNoteResponse(
        case_id=case_id,
        session_id=session_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        subjective=SOAPSection(
            **parsed.get("subjective", {"content": "", "content_vi": ""})
        ),
        objective=SOAPSection(
            **parsed.get("objective", {"content": "", "content_vi": ""})
        ),
        assessment=SOAPSection(
            **parsed.get("assessment", {"content": "", "content_vi": ""})
        ),
        plan=SOAPSection(
            **parsed.get("plan", {"content": "", "content_vi": ""})
        ),
        severity=state.get("severity", "routine") or "routine",
        primary_diagnosis=primary_dx,
        confidence_score=state.get("confidence_score", 0) or 0,
        critic_safety_score=(critic.get("overall_safety_score", 0) or 0) / 100.0,
        needs_human_review=state.get("needs_human_review", False),
        human_review_reason=state.get("human_review_reason"),
        safety_concerns=safety_concerns,
    )

    logger.info(
        "soap.generated",
        case_id=case_id,
        session_id=session_id,
        severity=soap_note.severity,
        has_safety_concerns=len(safety_concerns) > 0,
    )

    return soap_note
