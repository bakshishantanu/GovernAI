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
    ADMIN_EMAILS: str = ""

    # --- Role assignment ---
    # Comma-separated email addresses. Role is decided by which list a signed-in
    # user's email appears on, not by anything client-supplied - an email not on
    # either list gets the least-privileged role, "user".
    ADMIN_EMAILS: str = "admin@governai.com"

    # --- LLM Providers ---
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_PRIMARY_MODEL: str = "openai/gpt-oss-20b"
    LLM_FALLBACK_MODEL: str = "gemini-2.5-flash"

    # --- Ticketing skill: Jira ---
    # Left blank, the Ticketing skill falls back to its in-memory mock
    # adapter (see SkillRegistry) so local dev/tests never need real
    # Jira credentials.
    JIRA_BASE_URL: str = ""
    JIRA_EMAIL: str = ""
    JIRA_API_TOKEN: str = ""
    JIRA_PROJECT_KEY: str = ""
    # Shared secret Jira Automation sends back as a header, checked by the
    # webhook receiver below so the endpoint can't be triggered by anyone
    # who happens to find its URL.
    JIRA_WEBHOOK_SECRET: str = ""

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
