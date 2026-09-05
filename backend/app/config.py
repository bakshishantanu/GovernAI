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

    #: Local development only. When true, the literal token "dummy-token" is
    #: accepted as an admin user so the console works without a Supabase
    #: project. Must be declared here, not read from os.environ — a value in
    #: `.env` is loaded by pydantic-settings and never reaches os.environ.
    AUTH_ALLOW_DEV_TOKEN: bool = False

    # --- LLM Providers ---
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_PRIMARY_MODEL: str = "openai/gpt-oss-20b"
    LLM_FALLBACK_MODEL: str = "gemini-2.5-flash"

    # --- Cost Tracking ---
    MODEL_PRICING_JSON: str = "{}"

    #: Live budget cap enforced before every tool call (FRD-11). Org-wide until
    #: a per-agent cap column exists. Declared here for the same reason as
    #: AUTH_ALLOW_DEV_TOKEN above.
    AGENT_BUDGET_USD_24H: float = 5.00

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
