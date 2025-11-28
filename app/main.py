from fastapi import FastAPI

from app.api.routers import chat as chat_router
from app.infrastructure.config.settings import get_settings


def create_app() -> FastAPI:
    # # Application factory
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    # # Register routers
    app.include_router(chat_router.router)

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        # # Simple health endpoint for uptime and Datadog checks
        return {"status": "ok", "app": settings.app_name, "environment": settings.environment}

    return app


app = create_app()
