"""Patient Simulator — Đóng vai bệnh nhân trong Auto Test."""

import json

import structlog

from app.agents.auto_test.prompts import PATIENT_SIMULATOR_PROMPT, PERSONALITY_INSTRUCTIONS
from app.api.v1.schemas.auto_test import PatientRespondResponse, Scenario
from app.domain.services.llm_gateway import LLMGateway

logger = structlog.get_logger()


async def get_patient_response(
    gateway: LLMGateway,
    scenario: Scenario,
    conversation_history: list[dict],
    agent_message: str,
    reference_content: str = "",
) -> PatientRespondResponse:
    """Sinh câu trả lời của bệnh nhân ảo."""
    personality_instructions = PERSONALITY_INSTRUCTIONS.get(
        scenario.personality,
        PERSONALITY_INSTRUCTIONS["cooperative"],
    )

    system_prompt = PATIENT_SIMULATOR_PROMPT.format(
        primary_symptom=scenario.primary_symptom,
        secondary_symptoms=", ".join(scenario.secondary_symptoms) if scenario.secondary_symptoms else "không có",
        context=scenario.context or "không có thông tin thêm",
        patient_history=scenario.patient_history or "không có tiền sử đặc biệt",
        severity=scenario.severity,
        language_mix=scenario.language_mix,
        personality=scenario.personality,
        personality_instructions=personality_instructions,
    )

    # Nếu có file tham khảo → thêm hướng dẫn chi tiết về Red Flags, cách tiết lộ thông tin
    if reference_content:
        system_prompt += (
            "\n\n════════════════════════════════════════════════════\n"
            "TÀI LIỆU THAM KHẢO TỪ BÁC SĨ\n"
            "════════════════════════════════════════════════════\n\n"
            "Đọc tài liệu dưới đây để biết:\n"
            "- Red Flags nào CHỈ tiết lộ khi Agent hỏi đúng câu\n"
            "- Triệu chứng đi kèm nào nên nói, nào nên chờ được hỏi\n"
            "- Cách mô tả triệu chứng theo OLD CARTS\n\n"
            "LƯU Ý: Chỉ tham khảo kịch bản LIÊN QUAN đến triệu chứng của bạn.\n"
            "Vẫn phải tuân thủ QUY TẮC SỐ 1: HỎI GÌ TRẢ ĐÓ.\n\n"
            f"{reference_content}"
        )

    # Build messages: patient = assistant, agent = user
    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history:
        role = "assistant" if msg.get("role") == "patient" else "user"
        messages.append({"role": role, "content": msg["content"]})
    # Latest agent message
    messages.append({"role": "user", "content": agent_message})

    response = await gateway.generate(
        messages=messages,
        agent_type="auto_test_simulator",
        case_id=scenario.case_id,
    )

    result = _parse_patient_response(response.content)
    logger.info(
        "patient_response",
        case_id=scenario.case_id,
        should_end=result.should_end,
        message_len=len(result.patient_message),
    )
    return result


def _parse_patient_response(content: str) -> PatientRespondResponse:
    """Parse JSON response từ Patient Simulator."""
    text = content.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            data = json.loads(text[start : end + 1])
            return PatientRespondResponse(
                patient_message=data.get("message", text),
                should_end=data.get("should_end", False),
                end_reason=data.get("end_reason"),
            )
        except json.JSONDecodeError:
            pass
    # Fallback: treat entire content as the message
    return PatientRespondResponse(patient_message=text, should_end=False)
