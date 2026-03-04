"""Proposer Agent — Treatment recommendations (medications, labs, imaging, monitoring).

Replaces Physician's prescribing role. Reads screening results and proposes
structured treatment orders for Critic validation.
"""

import json
from datetime import datetime, timezone

import structlog
from langchain_core.messages import AIMessage

from app.agents.prompts.proposer_prompt import PROPOSER_SYSTEM_PROMPT
from app.agents.state import CareFlowState
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()


def _build_screening_context(state: CareFlowState) -> str:
    """Build context from screening results for the proposer prompt."""
    screening_result = state.get("screening_result", {})
    differential_diagnoses = state.get("differential_diagnoses", [])
    severity = state.get("severity", "routine")

    parts = [f"SEVERITY: {severity}"]

    if screening_result:
        clinical_impression = screening_result.get("clinical_impression", "")
        if clinical_impression:
            parts.append(f"CLINICAL IMPRESSION: {clinical_impression}")

        key_findings = screening_result.get("key_findings", [])
        if key_findings:
            parts.append("KEY FINDINGS: " + ", ".join(key_findings))

        red_flags = screening_result.get("red_flags", [])
        if red_flags:
            parts.append("RED FLAGS: " + ", ".join(red_flags))

    if differential_diagnoses:
        parts.append("\nDIFFERENTIAL DIAGNOSES:")
        for dx in differential_diagnoses:
            name = dx.get("name", "Unknown")
            confidence = dx.get("confidence", 0)
            reasoning = dx.get("reasoning", "")
            parts.append(f"  - {name} (confidence: {confidence}%): {reasoning}")

    return "\n".join(parts)


def _parse_proposer_response(response_text: str) -> dict:
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
        logger.warning("proposer.json_parse_failed", response_preview=text[:200])
        return {
            "medications": [],
            "lab_orders": [],
            "imaging": [],
            "monitoring_plan": {
                "follow_up_interval": "Unknown",
                "warning_signs": [],
                "instructions": response_text,
            },
            "drug_interactions": [],
            "allergy_alerts": [],
        }


async def proposer_node(
    state: CareFlowState,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> dict:
    """Proposer Agent LangGraph node function.

    Reads screening results from state, proposes treatment orders
    (medications, labs, imaging, monitoring).
    """
    case_id = state.get("case_id", "unknown")

    # Build screening context
    screening_context = _build_screening_context(state)

    # Include critic feedback if this is a re-run (loop from critic rejection)
    critic_issues = state.get("critic_issues", [])
    critic_feedback = ""
    if critic_issues:
        issues_text = "\n".join(
            f"  - [{issue.get('severity', 'warning')}] {issue.get('description', '')}: "
            f"{issue.get('recommendation', '')}"
            for issue in critic_issues
        )
        critic_feedback = f"\n\nPREVIOUS CRITIC FEEDBACK (you must address these issues):\n{issues_text}"

    # === PHI De-identification ===
    deidentified_context, phi_mapping = phi_deidentifier.deidentify(screening_context)

    # === Build LLM Messages ===
    cultural_expressions = state.get("cultural_expressions", [])
    cultural_context = ""
    if cultural_expressions:
        expr_info = "; ".join(
            f"'{e.get('original', '')}' → {e.get('medical_meaning', '')}"
            for e in cultural_expressions
        )
        cultural_context = f"\n\nCULTURAL CONTEXT: {expr_info}"

    llm_messages = [
        {
            "role": "system",
            "content": PROPOSER_SYSTEM_PROMPT + cultural_context + critic_feedback,
        },
        {
            "role": "user",
            "content": f"Based on the following screening results, propose treatment orders:\n\n{deidentified_context}",
        },
    ]

    # === Call LLM via Gateway ===
    response = await llm_gateway.generate(
        messages=llm_messages,
        agent_type="proposer",
        case_id=case_id,
        temperature=0.2,
    )

    # === Re-identify response if needed ===
    ai_response_text = response.content
    if phi_mapping:
        ai_response_text = phi_deidentifier.reidentify(ai_response_text, phi_mapping)

    # === Parse and update state ===
    parsed = _parse_proposer_response(ai_response_text)

    order_recommendations = []
    for med in parsed.get("medications", []):
        order_recommendations.append({"type": "medication", **med})
    for lab in parsed.get("lab_orders", []):
        order_recommendations.append({"type": "lab", **lab})
    for img in parsed.get("imaging", []):
        # Rename imaging's "type" field to "imaging_type" to avoid collision with our "type" key
        img_copy = {k: v for k, v in img.items() if k != "type"}
        img_copy["imaging_type"] = img.get("type", "")
        order_recommendations.append({"type": "imaging", **img_copy})

    # Include monitoring plan as a recommendation
    monitoring = parsed.get("monitoring_plan", {})
    if monitoring:
        order_recommendations.append({"type": "monitoring", **monitoring})

    drug_interactions = parsed.get("drug_interactions", [])
    allergy_alerts = parsed.get("allergy_alerts", [])

    logger.info(
        "proposer.completed",
        case_id=case_id,
        num_medications=len(parsed.get("medications", [])),
        num_labs=len(parsed.get("lab_orders", [])),
        num_imaging=len(parsed.get("imaging", [])),
        num_interactions=len(drug_interactions),
    )

    return {
        "messages": [AIMessage(content=ai_response_text)],
        "order_recommendations": order_recommendations,
        "drug_interactions": drug_interactions,
        "allergy_alerts": allergy_alerts,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
