from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Core app settings
    app_name: str = Field(default="OmniGuard LLM Service")
    environment: str = Field(default="local")  # local, dev, prod

    # Vertex AI / GCP
    gcp_project_id: str = Field(alias="OMNIGUARD_GCP_PROJECT_ID")
    gcp_location: str = Field(default="europe-west4", alias="OMNIGUARD_GCP_LOCATION")
    vertex_model_name: str = Field(
        default="gemini-2.0-flash-001",
        alias="OMNIGUARD_VERTEX_MODEL_NAME",
    )

    # Telemetry base switches
    telemetry_enabled: bool = Field(default=True, alias="OMNIGUARD_TELEMETRY_ENABLED")

    class Config:
        # # Use env variables only, no .env by default
        env_file = None
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    # # Cached settings instance for reuse
    return Settings()  # type: ignore[arg-type]
