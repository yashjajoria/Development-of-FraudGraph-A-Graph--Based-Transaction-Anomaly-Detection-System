from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # root .env.local (written by `neon deploy`) first, backend/.env overrides
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env.local", ROOT / "backend" / ".env"), extra="ignore"
    )
    database_url: str = "sqlite:///./dev.db"
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    llm_timeout: float = 30.0
    jwt_secret: str = "dev-secret-change-me"  # MUST be overridden outside dev
    jwt_hours: int = 12
    demo_password: str = "fraudgraph"  # demo auth only: users analyst / admin / viewer
    rate_limit_per_min: int = 20
    max_input_chars: int = 2000
    cors_origins: str = "http://localhost:5173"


settings = Settings()
