# Load environment variables before anything else
from dotenv import load_dotenv  # # Import dotenv loader
load_dotenv()  # # Ensure Datadog keys are present at import time

# Datadog auto-instrumentation for ddtrace v4.x (must be before any framework imports)
from ddtrace import patch_all  # # Auto-instrument all supported libraries
patch_all()  # # Enable all integrations in the current process

from fastapi import FastAPI
from app.api.routers import chat as chat_router
from app.infrastructure.config.settings import get_settings

import os

# Datadog LLM Observability (agentless mode)
from ddtrace.llmobs import LLMObs

# Structured JSON logger integration
from app.observability.ingestion import configure_observability_logger


def _validate_env() -> None:
    # # Ensure required Datadog keys for agentless ingestion
    required = ["DD_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables for Datadog LLMObs: {missing}. "
            "Check that .env is present and load_dotenv() executed."
        )


def _ensure_ml_app(settings) -> str:
    # # Ensure ML application name exists for Datadog correlation
    ml_app = os.getenv("DD_LLMOBS_ML_APP")
    if ml_app:
        return ml_app

    # # Fallback to safe normalized name
    fallback = settings.app_name.replace(" ", "_").lower()
    os.environ["DD_LLMOBS_ML_APP"] = fallback
    return fallback


def create_app() -> FastAPI:
    settings = get_settings()
    _validate_env()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    @app.on_event("startup")
    async def startup_observability() -> None:
        # # Configure JSON logging + Datadog trace correlation
        configure_observability_logger()

        # # Determine ML application identifier
        ml_app = _ensure_ml_app(settings)

        # # Enable Datadog LLM Observability (agentless)
        LLMObs.enable(ml_app=ml_app)

    # # Attach routers
    app.include_router(chat_router.router)

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
        }

    return app


# # ASGI application instance
app = create_app()
