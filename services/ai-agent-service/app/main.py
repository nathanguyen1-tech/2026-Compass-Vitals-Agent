"""FastAPI app — AI Agent Service entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.exceptions import CompassBaseException, ClinicalSafetyError, VoiceError

STATIC_DIR = Path(__file__).parent / "static"

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("startup", service=settings.service_name, env=settings.environment)

    # Create DB tables (idempotent — safe to run on every startup)
    try:
        from app.db.engine import engine
        from app.domain.models.base import Base
        from app.domain.models import agent_session  # noqa: F401 — register model

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("db.tables_ready")
    except Exception as e:
        logger.warning("db.create_tables_failed", error=str(e))

    yield

    # Dispose engine on shutdown
    try:
        from app.db.engine import engine as _engine
        await _engine.dispose()
    except Exception:
        pass

    logger.info("shutdown", service=settings.service_name)


app = FastAPI(
    title="AI Agent Service",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(CompassBaseException)
async def compass_exception_handler(request, exc: CompassBaseException):
    status_map = {
        "ValidationError": 400,
        "AuthorizationError": 403,
        "PHIAccessError": 403,
        "ClinicalSafetyError": 500,
        "LLMError": 503,
        "LLMTimeoutError": 503,
        "LLMRateLimitError": 429,
        "VoiceError": 502,
    }
    status_code = status_map.get(type(exc).__name__, 500)

    if isinstance(exc, ClinicalSafetyError):
        logger.critical("clinical_safety_error", message=exc.message, code=exc.code)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    """Catch-all handler to surface hidden 500 errors."""
    import traceback
    tb = traceback.format_exc()
    logger.error("unhandled_exception", error=str(exc), traceback=tb)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": str(exc)}},
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.service_name}


@app.get("/", response_class=HTMLResponse)
async def chat_ui():
    """Serve the chat UI."""
    return (STATIC_DIR / "chat.html").read_text(encoding="utf-8")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_ui():
    """Serve the care flow dashboard."""
    return (STATIC_DIR / "dashboard.html").read_text(encoding="utf-8")


@app.get("/care-plan", response_class=HTMLResponse)
async def care_plan_ui():
    """Serve the care plan view."""
    return (STATIC_DIR / "care-plan.html").read_text(encoding="utf-8")


@app.get("/clinical-summary", response_class=HTMLResponse)
async def clinical_summary_ui():
    """Serve the clinical summary view for MD."""
    return (STATIC_DIR / "clinical-summary.html").read_text(encoding="utf-8")


@app.get("/clinical-summary-v2", response_class=HTMLResponse)
async def clinical_summary_v2_ui():
    """Serve the Clinical Summary v2 (LLM-generated narrative) view for MD."""
    return (STATIC_DIR / "clinical-summary-v2.html").read_text(encoding="utf-8")


@app.get("/soap-note", response_class=HTMLResponse)
async def soap_note_ui():
    """Serve the SOAP note view for MD."""
    return (STATIC_DIR / "soap-note.html").read_text(encoding="utf-8")


@app.get("/logs", response_class=HTMLResponse)
async def logs_ui():
    """Serve the LLM Logs Dashboard."""
    return (STATIC_DIR / "logs.html").read_text(encoding="utf-8")


@app.get("/history", response_class=HTMLResponse)
async def history_ui():
    """Serve the session history page."""
    return (STATIC_DIR / "history.html").read_text(encoding="utf-8")


@app.get("/chat-v2", response_class=HTMLResponse)
async def chat_v2_ui():
    """Serve the Intake Agent V2 Chat UI."""
    return (STATIC_DIR / "chat-v2.html").read_text(encoding="utf-8")


@app.get("/chat-v3", response_class=HTMLResponse)
async def chat_v3_ui():
    """Serve the Intake Agent V3 Chat UI (Two-LLM Per Turn)."""
    html = (STATIC_DIR / "chat-v2.html").read_text(encoding="utf-8")
    html = html.replace("/api/v1/chat-v2", "/api/v1/chat-v3")
    html = html.replace("Intake Agent V2", "Intake Agent V3")
    return html


@app.get("/chat-v4", response_class=HTMLResponse)
async def chat_v4_ui():
    """Serve the Intake Agent V4 Chat UI (Single LLM Senior Doctor)."""
    html = (STATIC_DIR / "chat-v2.html").read_text(encoding="utf-8")
    html = html.replace("/api/v1/chat-v2", "/api/v1/chat-v4")
    html = html.replace("Intake Agent V2", "Intake Agent V4 — Senior Doctor")
    return html


# Import and register routers after app creation to avoid circular imports
from app.api.v1.routes import chat, chat_v2, chat_v3, chat_v4, flow, logs, sessions, voice_ws  # noqa: E402

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(chat_v2.router, prefix="/api/v1", tags=["chat-v2"])
app.include_router(chat_v3.router, prefix="/api/v1", tags=["chat-v3"])
app.include_router(chat_v4.router, prefix="/api/v1", tags=["chat-v4"])
app.include_router(flow.router, prefix="/api/v1", tags=["flow"])
app.include_router(voice_ws.router, prefix="/api/v1", tags=["voice"])
app.include_router(logs.router, prefix="/api/v1", tags=["logs"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
