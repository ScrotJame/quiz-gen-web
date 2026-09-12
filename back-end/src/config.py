from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(_ROOT_DIR / ".env"),
            str(_ROOT_DIR / ".env.production"),
            str(_ROOT_DIR / ".env.local"),
            str(_BACKEND_DIR / ".env"),
            str(_BACKEND_DIR / ".env.production"),
            str(_BACKEND_DIR / ".env.local"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Quiz Web Backend"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Database
    database_url: str = "sqlite+aiosqlite:///./quiz.db"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    use_in_memory_repos: bool = False

    # Mistral AI (Quiz Generation & Text Cleaning)
    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-2512"
    mistral_temperature: float = 0.3

    # Gemini AI (Quiz Generation & OCR Engine)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_ocr_model: str = "gemini-3.1-flash-lite"
    gemini_temperature: float = 0.3

    # Upload
    max_upload_size_mb: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
