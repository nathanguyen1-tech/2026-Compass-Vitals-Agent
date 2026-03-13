"""FastAPI app — AI Agent Service entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

import sqlalchemy as sa
import structlog
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.exceptions import CompassBaseException, ClinicalSafetyError, VoiceError
from app.database.engine import async_engine

STATIC_DIR = Path(__file__).parent / "static"

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("startup", service=settings.service_name, env=settings.environment)
    # Verify DB connection on startup
    async with async_engine.connect() as conn:
        await conn.execute(sa.text("SELECT 1"))
    logger.info("database_connected", url=settings.database_url.split("@")[-1])
    yield
    await async_engine.dispose()
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


@app.get("/patient-register", response_class=HTMLResponse)
async def patient_register_ui():
    """Serve the patient registration form."""
    return (STATIC_DIR / "patient-register.html").read_text(encoding="utf-8")


@app.get("/login", response_class=HTMLResponse)
async def login_ui():
    """Serve the login page."""
    return (STATIC_DIR / "login.html").read_text(encoding="utf-8")


@app.get("/patient-dashboard", response_class=HTMLResponse)
async def patient_dashboard_ui():
    """Serve the patient dashboard (profile + chat)."""
    return (STATIC_DIR / "patient-dashboard.html").read_text(encoding="utf-8")


# Import and register routers after app creation to avoid circular imports
from app.api.v1.routes import chat, flow, logs, patients, voice_ws  # noqa: E402

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(flow.router, prefix="/api/v1", tags=["flow"])
app.include_router(voice_ws.router, prefix="/api/v1", tags=["voice"])
app.include_router(logs.router, prefix="/api/v1", tags=["logs"])
app.include_router(patients.router, prefix="/api/v1", tags=["patients"])
