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


settings = Settings()
