import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings management."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App basics
    APP_NAME: str = "resume-studio"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # API settings
    API_PREFIX: str = "/api/v1"
    @property
    def CORS_ORIGINS(self) -> list[str]:
        raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000")
        return [o.strip() for o in raw.split(",") if o.strip()]

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./resume_intelligence.db")

    # LLM settings
    API_KEY: str = os.getenv("API_KEY", "")
    API_BASE: str = os.getenv("API_BASE", "https://api.deepseek.com")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-chat")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0"))

    # Upload settings
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))

    # RAG toggle
    RAG_ENABLED: bool = os.getenv("RAG_ENABLED", "False").lower() == "true"


settings = Settings()
