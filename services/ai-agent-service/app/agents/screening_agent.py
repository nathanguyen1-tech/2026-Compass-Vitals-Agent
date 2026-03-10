"""Screening Agent — Clinical assessment and severity classification.

Replaces Physician's initial assessment role. Evaluates intake data,
classifies severity, and generates differential diagnoses.
"""

import json
from datetime import datetime, timezone

import structlog
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.prompts.screening_prompt import SCREENING_SYSTEM_PROMPT
from app.agents.state import CareFlowState
from app.agents.tools.emergency_detector import detect_emergency
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier
from app.nlp.code_switcher import CodeSwitcher
from app.nlp.cultural_mapper import CulturalMapper

logger = structlog.get_logger()

code_switcher = CodeSwitcher()
cultural_mapper = CulturalMapper()


def _build_intake_summary(state: CareFlowState) -> str:
    """Build a text summary of intake data for the screening prompt."""
    intake_data = state.get("intake_data")
    messages = state.get("messages", [])
    cultural_expressions = state.get("cultural_expressions", [])

    parts = []

    # Include structured intake data if available
    if intake_data:
        parts.append("STRUCTURED INTAKE DATA:")
        for key, value in intake_data.items():
            parts.append(f"  {key}: {value}")

    # Include conversation history as context
    if messages:
        parts.append("\nCONVERSATION HISTORY:")
        for msg in messages[-10:]:  # Last 10 messages max
            role = "Patient" if isinstance(msg, HumanMessage) else "Intake Agent"
            content = msg.content if hasattr(msg, "content") else str(msg)
            parts.append(f"  [{role}]: {content}")

    # Include cultural expressions
    if cultural_expressions:
        parts.append("\nCULTURAL EXPRESSIONS DETECTED:")
        for expr in cultural_expressions:
            parts.append(
                f"  '{expr.get('original', '')}' → {expr.get('medical_meaning', '')}"
            )

    return "\n".join(parts) if parts else "No intake data available."


def _parse_screening_response(response_text: str) -> dict:
    """Parse JSON from LLM response with fallback."""
    # Try to extract JSON from response
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("screening.json_parse_failed", response_preview=text[:200])
        return {
            "severity": "routine",
            "clinical_impression": response_text,
            "key_findings": [],
            "red_flags": [],
            "differential_diagnoses": [],
            "recommended_urgency": "Unable to parse structured response",
        }


async def screening_node(
    state: CareFlowState,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> dict:
    """Screening Agent LangGraph node function.

    Reads intake data from state, evaluates clinical severity,
    generates differential diagnoses.
    """
    case_id = state.get("case_id", "unknown")

    # === Step 1: Emergency Detection (check if already flagged) ===
    if state.get("is_emergency"):
        logger.warning("screening.emergency_bypass", case_id=case_id)
        return {
            "screening_result": {
                "severity": "emergency",
                "clinical_impression": "Emergency detected during intake — bypass screening.",
            },
            "severity": "emergency",
            "differential_diagnoses": [],
            "confidence_score": 1.0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Build intake summary for screening prompt
    intake_summary = _build_intake_summary(state)

    # === Step 2: NLP Pipeline ===
    detected_language = state.get("detected_language", "vi")

    # === Step 3: PHI De-identification ===
    deidentified_summary, phi_mapping = phi_deidentifier.deidentify(intake_summary)

    # === Step 4: Build LLM Messages ===
    cultural_context = ""
    cultural_expressions = state.get("cultural_expressions", [])
    if cultural_expressions:
        expr_info = "; ".join(
            f"'{e.get('original', '')}' → {e.get('medical_meaning', '')}"
            for e in cultural_expressions
        )
        cultural_context = f"\n\nCULTURAL CONTEXT: {expr_info}"

    llm_messages = [
        {"role": "system", "content": SCREENING_SYSTEM_PROMPT + cultural_context},
        {
            "role": "user",
            "content": f"Please evaluate the following patient intake data and provide your clinical assessment:\n\n{deidentified_summary}",
        },
    ]

    # === Step 5: Call LLM via Gateway ===
    response = await llm_gateway.generate(
        messages=llm_messages,
        agent_type="screening",
        case_id=case_id,
        temperature=0.2,
    )

    # === Step 6: Re-identify response if needed ===
    ai_response_text = response.content
    if phi_mapping:
        ai_response_text = phi_deidentifier.reidentify(ai_response_text, phi_mapping)

    # === Step 7: Parse and update state ===
    parsed = _parse_screening_response(ai_response_text)

    severity = parsed.get("severity", "routine")
    differential_diagnoses = parsed.get("differential_diagnoses", [])

    # Calculate confidence from top diagnosis
    confidence_score = None
    if differential_diagnoses:
        confidence_score = max(d.get("confidence", 0) for d in differential_diagnoses) / 100.0

    logger.info(
        "screening.completed",
        case_id=case_id,
        severity=severity,
        num_diagnoses=len(differential_diagnoses),
        confidence=confidence_score,
    )

    return {
        "messages": [AIMessage(content=ai_response_text)],
        "screening_result": parsed,
        "severity": severity,
        "differential_diagnoses": differential_diagnoses,
        "confidence_score": confidence_score,
        "is_emergency": severity == "emergency",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
