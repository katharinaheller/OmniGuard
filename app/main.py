from fastapi import FastAPI
from app.api.routers import chat as chat_router
from app.infrastructure.config.settings import get_settings

# Load .env early (works only for Python, not ddtrace-run)
from dotenv import load_dotenv
load_dotenv()

# ddtrace LLMObs – enable inside startup event
from ddtrace.llmobs import LLMObs


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    # ---------------------
    # Datadog Observability
    # ---------------------
    @app.on_event("startup")
    async def enable_llmobs():
        # This is executed AFTER ddtrace-run injects env vars
        LLMObs.enable()

    # ---------------------
    # Routers
    # ---------------------
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
