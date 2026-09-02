from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """GovernAI backend configuration. All values are read from environment
    variables (or a .env file) at startup."""

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/governai"

    # --- Supabase Auth ---
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # --- LLM Providers ---
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_PRIMARY_MODEL: str = "openai/gpt-oss-20b"
    LLM_FALLBACK_MODEL: str = "gemini-2.5-flash"

    # --- Cost Tracking ---
    MODEL_PRICING_JSON: str = "{}"

    # --- Application ---
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
