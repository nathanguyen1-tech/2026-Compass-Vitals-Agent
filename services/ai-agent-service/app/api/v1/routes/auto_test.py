"""Auto Test API endpoints — sinh kịch bản, mô phỏng bệnh nhân, đánh giá, lưu log."""

import structlog
from fastapi import APIRouter, HTTPException

from app.agents.auto_test.medical_judge import evaluate_conversation
from app.agents.auto_test.patient_simulator import get_patient_response
from app.agents.auto_test.scenario_generator import generate_scenarios
from app.api.v1.schemas.auto_test import (
    EvaluateRequest,
    EvaluateResponse,
    ExportRequest,
    PatientRespondRequest,
    PatientRespondResponse,
    ScenarioGenerateRequest,
    ScenarioGenerateResponse,
)
from app.domain.services import auto_test_store
from app.config import settings
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()
router = APIRouter()

# Reuse same services pattern as chat_v2.py
_phi = PHIDeidentifier(encryption_key=settings.phi_encryption_key) if settings.phi_encryption_key else None
_gateway = (
    LLMGateway(
        openai_api_key=settings.openai_api_key,
        phi_deidentifier=_phi,
        primary_model=settings.primary_llm_model,
        screening_model=settings.screening_llm_model,
    )
    if settings.openai_api_key and _phi
    else None
)


@router.post("/auto-test/generate-scenarios", response_model=ScenarioGenerateResponse)
async def generate_scenarios_endpoint(request: ScenarioGenerateRequest):
    """Sinh N kịch bản bệnh nhân cho auto test."""
    if not _gateway:
        raise _no_gateway_error()

    scenarios = await generate_scenarios(
        gateway=_gateway,
        count=request.count,
        severity_filter=request.severity_filter,
        topic=request.topic,
        reference_content=request.reference_content,
    )
    return ScenarioGenerateResponse(scenarios=scenarios)


@router.post("/auto-test/patient-respond", response_model=PatientRespondResponse)
async def patient_respond_endpoint(request: PatientRespondRequest):
    """Sinh câu trả lời của bệnh nhân ảo."""
    if not _gateway:
        raise _no_gateway_error()

    result = await get_patient_response(
        gateway=_gateway,
        scenario=request.scenario,
        conversation_history=request.conversation_history,
        agent_message=request.agent_message,
        reference_content=request.reference_content,
    )
    return result


@router.post("/auto-test/evaluate", response_model=EvaluateResponse)
async def evaluate_endpoint(request: EvaluateRequest):
    """Đánh giá cuộc hội thoại hoàn chỉnh."""
    if not _gateway:
        raise _no_gateway_error()

    result = await evaluate_conversation(
        gateway=_gateway,
        scenario=request.scenario,
        conversation_history=request.conversation_history,
        reference_content=request.reference_content,
    )
    return EvaluateResponse(result=result)


@router.post("/auto-test/save-run")
async def save_run_endpoint(request: ExportRequest):
    """Lưu kết quả test run vào PostgreSQL."""
    await auto_test_store.save_run(
        test_run_id=request.test_run_id,
        total_cases=request.summary.get("total_cases", len(request.results)),
        summary=request.summary,
        results=request.results,
    )
    return {"status": "saved", "test_run_id": request.test_run_id}


@router.get("/auto-test/runs")
async def list_runs_endpoint():
    """Danh sách tất cả test runs."""
    runs = await auto_test_store.list_runs()
    return {"runs": runs}


@router.get("/auto-test/runs/{run_id}")
async def get_run_endpoint(run_id: str):
    """Chi tiết 1 test run (kèm conversation)."""
    run = await auto_test_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Test run {run_id} không tồn tại")
    return run


@router.delete("/auto-test/runs/{run_id}")
async def delete_run_endpoint(run_id: str):
    """Xóa 1 test run."""
    deleted = await auto_test_store.delete_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Test run {run_id} không tồn tại")
    return {"status": "deleted", "test_run_id": run_id}


def _no_gateway_error():
    return HTTPException(
        status_code=503,
        detail="LLM Gateway chưa được cấu hình. Kiểm tra OPENAI_API_KEY và PHI_ENCRYPTION_KEY trong .env",
    )
