"""FastAPI app — AI Agent Service entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import CompassBaseException, ClinicalSafetyError

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("startup", service=settings.service_name, env=settings.environment)
    yield
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


# Import and register routers after app creation to avoid circular imports
from app.api.v1.routes import chat  # noqa: E402

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
