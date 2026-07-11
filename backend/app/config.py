"""Application configuration, loaded from environment variables and `.env`."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the LucidUI backend.

    CORS is wide open (`*`) by default for Phase 1 development convenience.
    Production deployments must restrict `cors_allow_origins` explicitly —
    see ROADMAP.md Phase 11 ("Secure CORS").
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "LucidUI Backend"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = True
    cors_allow_origins: str = "*"
    max_upload_size_bytes: int = 20 * 1024 * 1024

    @property
    def cors_allow_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS origins setting into a list."""
        if self.cors_allow_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance shared across the application."""
    return Settings()
