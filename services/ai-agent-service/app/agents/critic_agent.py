"""Critic Agent — Safety validation of treatment orders.

Replaces Pharmacist + Peer Review role. Validates Proposer's recommendations
for drug interactions, contraindications, dosage, and completeness.
"""

import json
from datetime import datetime, timezone

import structlog
from langchain_core.messages import AIMessage

from app.agents.prompts.critic_prompt import CRITIC_SYSTEM_PROMPT
from app.agents.state import CareFlowState
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()


def _build_orders_context(state: CareFlowState) -> str:
    """Build context from order recommendations for the critic prompt."""
    order_recommendations = state.get("order_recommendations", [])
    drug_interactions = state.get("drug_interactions", [])
    allergy_alerts = state.get("allergy_alerts", [])
    screening_result = state.get("screening_result", {})
    severity = state.get("severity", "routine")
    differential_diagnoses = state.get("differential_diagnoses", [])

    parts = [f"SEVERITY: {severity}"]

    # Screening context
    if screening_result:
        clinical_impression = screening_result.get("clinical_impression", "")
        if clinical_impression:
            parts.append(f"CLINICAL IMPRESSION: {clinical_impression}")

    if differential_diagnoses:
        parts.append("\nDIFFERENTIAL DIAGNOSES:")
        for dx in differential_diagnoses:
            name = dx.get("name", "Unknown")
            confidence = dx.get("confidence", 0)
            parts.append(f"  - {name} ({confidence}%)")

    # Orders to validate
    if order_recommendations:
        parts.append("\nORDERS TO VALIDATE:")
        for i, order in enumerate(order_recommendations, 1):
            order_type = order.get("type", "unknown")
            parts.append(f"\n  Order #{i} ({order_type}):")
            for key, value in order.items():
                if key != "type":
                    parts.append(f"    {key}: {value}")

    # Pre-flagged interactions
    if drug_interactions:
        parts.append("\nFLAGGED DRUG INTERACTIONS:")
        for interaction in drug_interactions:
            pair = interaction.get("drug_pair", [])
            sev = interaction.get("severity", "unknown")
            desc = interaction.get("description", "")
            parts.append(f"  - {' + '.join(pair)} [{sev}]: {desc}")

    if allergy_alerts:
        parts.append("\nALLERGY ALERTS:")
        for alert in allergy_alerts:
            parts.append(f"  - {alert}")

    return "\n".join(parts)


def _parse_critic_response(response_text: str) -> dict:
    """Parse JSON from LLM response with fallback."""
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("critic.json_parse_failed", response_preview=text[:200])
        return {
            "status": "needs_modification",
            "overall_safety_score": 50,
            "summary": "Unable to parse structured validation response.",
            "issues": [
                {
                    "severity": "warning",
                    "category": "missing_order",
                    "description": "Critic response could not be parsed",
                    "recommendation": "Manual review required",
                }
            ],
            "approved_orders": [],
            "modifications_required": [],
        }


async def critic_node(
    state: CareFlowState,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> dict:
    """Critic Agent LangGraph node function.

    Reads order recommendations from state, validates safety,
    returns approval/rejection with issues.
    """
    case_id = state.get("case_id", "unknown")

    # Build orders context
    orders_context = _build_orders_context(state)

    # === PHI De-identification ===
    deidentified_context, phi_mapping = phi_deidentifier.deidentify(orders_context)

    # === Build LLM Messages ===
    llm_messages = [
        {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Please validate the following treatment orders for safety:\n\n{deidentified_context}",
        },
    ]

    # === Call LLM via Gateway ===
    response = await llm_gateway.generate(
        messages=llm_messages,
        agent_type="critic",
        case_id=case_id,
        temperature=0.1,  # Low temperature for consistent safety validation
    )

    # === Re-identify response if needed ===
    ai_response_text = response.content
    if phi_mapping:
        ai_response_text = phi_deidentifier.reidentify(ai_response_text, phi_mapping)

    # === Parse and update state ===
    parsed = _parse_critic_response(ai_response_text)

    status = parsed.get("status", "needs_modification")
    critic_approved = status == "approved"
    issues = parsed.get("issues", [])

    # Track loop count for Proposer re-runs
    critic_loops = state.get("_critic_loops", 0) + 1

    logger.info(
        "critic.completed",
        case_id=case_id,
        status=status,
        approved=critic_approved,
        num_issues=len(issues),
        safety_score=parsed.get("overall_safety_score"),
        loop=critic_loops,
    )

    return {
        "messages": [AIMessage(content=ai_response_text)],
        "critic_validation": parsed,
        "critic_approved": critic_approved,
        "critic_issues": issues,
        "confidence_score": (parsed.get("overall_safety_score", 50)) / 100.0,
        "needs_human_review": status == "rejected" or critic_loops >= 2,
        "human_review_reason": (
            f"Critic {status}: {len(issues)} issues found"
            if not critic_approved
            else None
        ),
        "_critic_loops": critic_loops,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
