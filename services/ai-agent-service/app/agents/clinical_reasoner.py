"""Clinical Reasoner — V3 Intake Agent, LLM Call 1 (hidden from patient).

Explicit clinical reasoning: what do we know, what's missing,
what's the differential, what's the highest-yield next question.
Output: structured JSON — validated by code before use.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import structlog

from app.agents.prompts.reasoner_prompt import REASONER_SYSTEM_PROMPT, REASONER_USER_TEMPLATE
from app.agents.tools.differential_tracker import DifferentialTracker
from app.domain.services.llm_gateway import LLMGateway

logger = structlog.get_logger()

# Fallback reasoner output when JSON parse fails
_FALLBACK_REASONER_OUTPUT = {
    "known_facts": {},
    "answer_quality": {},
    "running_differential": [],
    "next_question_target": "cc",
    "reason_for_target": "Fallback: could not parse reasoner output",
    "skip_counts": {},
    "complaint_category": "general",
    "emergency_score": 0,
    "emergency_reasoning": "Fallback — manual review recommended",
    "intake_complete": False,
    "intake_complete_reason": None,
}


def _build_conversation_history(messages: list) -> str:
    """Format last N messages as readable history."""
    from langchain_core.messages import HumanMessage, AIMessage

    lines = []
    for msg in messages[-16:]:  # Last 16 = ~8 turns
        content = msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(msg, HumanMessage):
            lines.append(f"Patient: {content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"Intake Agent: {content}")
    return "\n".join(lines)


def _parse_reasoner_json(raw: str) -> dict:
    """Parse JSON from reasoner, with robust fallback."""
    text = raw.strip()

    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()

    try:
        parsed = json.loads(text)
        # Validate minimum required keys
        required_keys = {"next_question_target", "emergency_score", "running_differential"}
        if not required_keys.issubset(parsed.keys()):
            raise ValueError(f"Missing keys: {required_keys - parsed.keys()}")
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(
            "reasoner.json_parse_failed",
            error=str(e),
            preview=text[:300],
        )
        return dict(_FALLBACK_REASONER_OUTPUT)


async def run_clinical_reasoner(
    messages: list,
    patient_message: str,
    differential_tracker: DifferentialTracker,
    llm_gateway: LLMGateway,
    case_id: str,
    cultural_context: str = "",
    phi_deidentifier=None,
    last_asked_field: str = "unknown",
    narrative_done: bool = False,
) -> dict:
    """Run Clinical Reasoner: LLM Call 1.

    Args:
        messages: Full conversation history (LangChain messages)
        patient_message: Latest patient message (clean text)
        differential_tracker: Current clinical state
        llm_gateway: LLM gateway for API calls
        case_id: For logging
        cultural_context: Cultural expressions detected

    Returns:
        Parsed reasoner JSON dict (never None — fallback on error)
    """
    current_year = datetime.now(timezone.utc).year

    # Build clinical state summary
    clinical_state = differential_tracker.summary_for_reasoner()
    if cultural_context:
        clinical_state += f"\n\nCULTURAL EXPRESSIONS DETECTED:\n{cultural_context}"

    # Build conversation history
    history = _build_conversation_history(messages[:-1])  # Exclude last msg (= patient_message)

    # Use replace() not .format() — prompt contains JSON {} that would conflict
    system_prompt = REASONER_SYSTEM_PROMPT.replace("{current_year}", str(current_year))

    user_prompt = (
        REASONER_USER_TEMPLATE
        .replace("{clinical_state_summary}", clinical_state or "First turn — no prior data.")
        .replace("{narrative_done}", str(narrative_done).lower())
        .replace("{last_asked_field}", last_asked_field or "unknown (first turn)")
        .replace("{conversation_history}", history or "No prior conversation.")
        .replace("{patient_message}", patient_message)
    )

    # Deidentify user_prompt to satisfy gateway PHI check
    if phi_deidentifier is not None:
        user_prompt, _ = phi_deidentifier.deidentify(user_prompt)

    llm_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await llm_gateway.generate(
            messages=llm_messages,
            agent_type="intake_v3_reasoner",
            case_id=case_id,
            temperature=0.1,  # Low temp: want consistent structured JSON
        )
        raw = response.content
    except Exception as e:
        logger.error("reasoner.llm_call_failed", case_id=case_id, error=str(e))
        # Smart fallback: reuse last known next_target from DifferentialTracker
        fallback = dict(_FALLBACK_REASONER_OUTPUT)
        if differential_tracker.next_target:
            fallback["next_question_target"] = differential_tracker.next_target
            fallback["reason_for_target"] = "Fallback: reusing last known target"
        return fallback

    parsed = _parse_reasoner_json(raw)

    logger.info(
        "reasoner.completed",
        case_id=case_id,
        next_target=parsed.get("next_question_target"),
        emergency_score=parsed.get("emergency_score", 0),
        differential_count=len(parsed.get("running_differential", [])),
        intake_complete=parsed.get("intake_complete", False),
    )

    return parsed
