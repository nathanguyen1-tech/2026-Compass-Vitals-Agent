"""Intake Agent — Thu thập triệu chứng qua conversational interview.

Thay thế vai trò Y tá triage (RN). FR9: Symptom Intake with Contextual Follow-up.
"""

from datetime import datetime, timezone

import structlog
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.prompts.intake_prompt import INTAKE_SYSTEM_PROMPT
from app.agents.state import CareFlowState
from app.agents.tools.emergency_detector import detect_emergency, get_emergency_keywords_found
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier
from app.nlp.code_switcher import CodeSwitcher
from app.nlp.cultural_mapper import CulturalMapper

logger = structlog.get_logger()

code_switcher = CodeSwitcher()
cultural_mapper = CulturalMapper()


async def intake_node(
    state: CareFlowState,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> dict:
    """Intake Agent LangGraph node function.

    Reads messages from state, processes through NLP pipeline,
    calls LLM via gateway, returns updated state fields.
    """
    messages = state.get("messages", [])
    case_id = state.get("case_id", "unknown")

    if not messages:
        return _initial_greeting(state)

    # Get latest patient message
    last_message = messages[-1]
    patient_text = (
        last_message.content if hasattr(last_message, "content") else str(last_message)
    )

    # === Step 1: Emergency Detection (mỗi message) ===
    is_emergency = detect_emergency(patient_text)
    if is_emergency:
        emergency_keywords = get_emergency_keywords_found(patient_text)
        logger.warning(
            "emergency.detected",
            case_id=case_id,
            keywords=emergency_keywords,
        )
        return {
            "is_emergency": True,
            "messages": [
                AIMessage(
                    content="⚠️ CẢNH BÁO KHẨN CẤP: Triệu chứng bạn mô tả cần được xử lý ngay lập tức. "
                    "Vui lòng gọi 911 hoặc đến phòng cấp cứu gần nhất ngay. "
                    "Đừng chờ đợi — sức khỏe của bạn là ưu tiên hàng đầu."
                )
            ],
        }

    # === Step 2: NLP Pipeline ===
    detected_language = code_switcher.detect_language(patient_text)
    cultural_expressions = cultural_mapper.map_expressions(patient_text)
    normalized_text = code_switcher.normalize(patient_text)

    # === Step 3: PHI De-identification ===
    deidentified_text, phi_mapping = phi_deidentifier.deidentify(normalized_text)

    # === Step 4: Build LLM messages ===
    # Build context with cultural expressions if found
    cultural_context = ""
    if cultural_expressions:
        expr_info = "; ".join(
            f"'{e['original']}' → {e['medical_meaning']}" for e in cultural_expressions
        )
        cultural_context = f"\n\nCULTURAL CONTEXT DETECTED: {expr_info}"

    llm_messages = [
        {"role": "system", "content": INTAKE_SYSTEM_PROMPT + cultural_context},
    ]

    # Add conversation history (de-identified)
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else str(msg)
        deidentified_content, _ = phi_deidentifier.deidentify(content)
        if isinstance(msg, HumanMessage):
            llm_messages.append({"role": "user", "content": deidentified_content})
        elif isinstance(msg, AIMessage):
            llm_messages.append({"role": "assistant", "content": deidentified_content})

    # === Step 5: Call LLM via Gateway ===
    response = await llm_gateway.generate(
        messages=llm_messages,
        agent_type="intake",
        case_id=case_id,
        temperature=0.3,
    )

    # === Step 6: Re-identify response if needed ===
    ai_response_text = response.content
    if phi_mapping:
        ai_response_text = phi_deidentifier.reidentify(ai_response_text, phi_mapping)

    # === Step 7: Return updated state ===
    return {
        "messages": [AIMessage(content=ai_response_text)],
        "detected_language": detected_language,
        "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
        "is_emergency": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _initial_greeting(state: CareFlowState) -> dict:
    """Return initial greeting when no messages yet."""
    return {
        "messages": [
            AIMessage(
                content="Xin chào! Tôi là trợ lý y tế AI của Compass Vitals. "
                "Tôi sẽ giúp thu thập thông tin về triệu chứng của bạn. "
                "Bạn có thể cho tôi biết bạn đang gặp vấn đề sức khỏe gì không?"
            )
        ],
        "detected_language": "vi",
        "is_emergency": False,
    }
