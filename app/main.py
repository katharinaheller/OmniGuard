from fastapi import FastAPI
from app.api.routers import chat as chat_router
from app.infrastructure.config.settings import get_settings

# Load .env early (works with ddtrace-run because python loads file before instrumentation)
from dotenv import load_dotenv
load_dotenv()

import os

# Datadog LLMObs
from ddtrace.llmobs import LLMObs

# Observability logger for JSON logs and Datadog ingestion
from app.observability.ingestion import configure_observability_logger


def create_app() -> FastAPI:
    # Create config instance
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    # ---------------------------------------------------------------------
    # Datadog Observability
    # ---------------------------------------------------------------------
    @app.on_event("startup")
    async def enable_llmobs() -> None:
        # Initialize JSON log formatter + DD trace correlation
        configure_observability_logger()

        # Ensure DD_LLMOBS_ML_APP is set, otherwise Datadog crashes
        ml_app = os.getenv("DD_LLMOBS_ML_APP")
        if not ml_app:
            ml_app = settings.app_name.replace(" ", "_").lower()
            os.environ["DD_LLMOBS_ML_APP"] = ml_app  # Safe fallback

        # Enable LLM Observability with autodetected ml_app
        LLMObs.enable(ml_app=ml_app)

    # ---------------------------------------------------------------------
    # Routers
    # ---------------------------------------------------------------------
    app.include_router(chat_router.router)

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
        }

    return app


app = create_app()
