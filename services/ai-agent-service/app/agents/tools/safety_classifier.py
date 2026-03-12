"""Safety Classifier — LLM-based emergency triage for messages that bypass keyword detection.

Layer 1.5 in the emergency detection stack. Called only when keyword layers
produce no match AND the primary LLM's risk markers are absent or ambiguous.

Uses GPT-4o-mini with a focused classification prompt (no conversation,
no OLDCARTS, just: "is this dangerous?"). Typical latency: 150-300ms.
"""

from __future__ import annotations

import json

import structlog
from pydantic import BaseModel

from app.domain.services.llm_gateway import LLMGateway

logger = structlog.get_logger()


class SafetyClassification(BaseModel):
    """Result from the safety classifier."""

    risk_level: str  # "none" | "low" | "moderate" | "high" | "critical"
    is_emergency: bool
    reasoning: str
    category: str  # "cardiac", "trauma", "toxic_ingestion", "anaphylaxis", etc.


SAFETY_CLASSIFIER_PROMPT = """\
You are a medical triage safety classifier. Your ONLY job is to assess whether
a patient's message describes a medical emergency or dangerous situation.

Consider ALL types of emergencies including but not limited to:
- Trauma / injury (falls from height, accidents, burns, choking, drowning, strangulation)
- Toxic ingestion (swallowed batteries, chemicals, medications, poisons)
- Anaphylaxis / severe allergic reactions (throat swelling, hives + breathing difficulty)
- Cardiac events (chest pain, collapse, syncope)
- Neurological events (stroke signs, seizures, sudden weakness)
- Respiratory distress (can't breathe, choking, foreign body)
- Pediatric emergencies (child not breathing, lethargic, not drinking, high fever + rash)
- Obstetric emergencies (bleeding in pregnancy, preeclampsia signs)
- Mental health crises (suicidal ideation, self-harm, psychosis)
- Environmental (electric shock, heat stroke, hypothermia, animal envenomation)
- Hemorrhage (vomiting blood, rectal bleeding, uncontrolled bleeding)

CRITICAL RULES:
- ANY situation involving a child in danger = at minimum HIGH risk
- Toxic ingestion (batteries, chemicals, medications) = CRITICAL
- Throat/face swelling after exposure = CRITICAL (anaphylaxis)
- Fall from height (>1m, stairs, roof, floor) = HIGH
- When in doubt, classify as HIGH. Over-triage is always safer than under-triage.
- Consider the message in BOTH Vietnamese and English context.
- Respond in valid JSON only. No other text.

Respond with ONLY this JSON (no markdown, no explanation):
{"risk_level":"none|low|moderate|high|critical","is_emergency":true|false,"reasoning":"brief reason","category":"category_name"}"""


async def classify_safety(
    patient_message: str,
    conversation_summary: str | None = None,
    complaint_category: str | None = None,
    llm_gateway: LLMGateway | None = None,
    case_id: str = "",
) -> SafetyClassification | None:
    """Classify a patient message for emergency risk using a dedicated LLM call.

    Args:
        patient_message: The raw patient message text.
        conversation_summary: Brief summary of conversation so far (optional).
        complaint_category: Active complaint protocol ID (optional).
        llm_gateway: LLM gateway instance. If None, returns None (graceful skip).
        case_id: For logging.

    Returns:
        SafetyClassification or None if the call fails (fail-open).
    """
    if not llm_gateway:
        return None

    user_content = f"Patient message: {patient_message}"
    if conversation_summary:
        user_content += f"\nConversation context: {conversation_summary}"
    if complaint_category:
        user_content += f"\nComplaint category: {complaint_category}"

    messages = [
        {"role": "system", "content": SAFETY_CLASSIFIER_PROMPT},
        {"role": "user", "content": user_content},
    ]

    try:
        response = await llm_gateway.generate(
            messages=messages,
            agent_type="safety_classifier",
            case_id=case_id,
            temperature=0.0,
            max_tokens=256,
        )
        # Strip markdown fences if present
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        data = json.loads(content)
        return SafetyClassification(**data)
    except Exception as exc:
        logger.warning(
            "safety_classifier.failed",
            case_id=case_id,
            error=str(exc),
        )
        return None  # Fail-open: don't block the flow


def should_run_classifier(
    keyword_detected: bool,
    llm_risk_level: str | None,
    message_count: int,
) -> bool:
    """Smart gate: decide if the safety classifier LLM call is needed.

    Returns True when keyword detection found nothing AND the primary LLM
    either didn't report risk or reported low risk.
    """
    # If keywords already caught something, no need for classifier
    if keyword_detected:
        return False

    # If the primary LLM reported moderate+ risk, it's already handling it
    if llm_risk_level and llm_risk_level in ("moderate", "high", "critical"):
        return False

    # First substantive message with no keyword match — always run
    if message_count <= 1:
        return True

    # Primary LLM said "low" or didn't emit risk_level at all → run classifier
    return True
