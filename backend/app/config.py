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

    # LLM interpretation layer (see app.llm). Defaults to the offline mock
    # provider so the app runs with no API key; set LLM_PROVIDER=gemini and
    # GEMINI_API_KEY to use the real provider.
    llm_provider: str = "mock"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    # 2048 leaves headroom beyond a realistic structured response even with
    # thinking disabled (see app.llm.gemini_provider); 1024 was observed
    # truncating real responses.
    llm_max_output_tokens: int = 2048

    # UIClip evaluation layer (see app.uiclip). Defaults to the offline mock
    # evaluator. "huggingface" loads the official BIG Lab checkpoint via
    # transformers.CLIPModel/CLIPProcessor (app.uiclip.huggingface_provider)
    # — see docs/research/uiclip-integration.md for why this checkpoint was
    # chosen. Any other value gracefully degrades to
    # uiclip.status = "unavailable" rather than raising.
    uiclip_provider: str = "mock"
    uiclip_model_id: str = "biglab/uiclip_jitteredwebsites-2-224-paraphrased"
    uiclip_device: str = "auto"

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
