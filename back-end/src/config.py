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
            str(_ROOT_DIR / ".env.local"),
            str(_BACKEND_DIR / ".env"),
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
    mistral_model: str = "ministral-14b-latest"
    mistral_temperature: float = 0.3

    # Gemini AI (Quiz Generation & OCR Engine)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_ocr_models: str = ""  # Danh sách nhiều model từ biến môi trường GEMINI_OCR_MODELS (ngăn cách bởi dấu phẩy)
    gemini_ocr_model: str = ""   # Fallback tương thích ngược: GEMINI_OCR_MODEL
    gemini_temperature: float = 0.3
    gemini_ocr_system_prompt: str = (
        "Perform OCR on this image. Ignore perspective distortion and page curvature. "
        "Transcribe all readable text verbatim."
    )

    @property
    def ocr_model_list(self) -> list[str]:
        """Danh sách các model Gemini OCR theo thứ tự ưu tiên, nạp linh hoạt từ .env mà không hardcode."""
        raw = (self.gemini_ocr_models or "").strip() or (self.gemini_ocr_model or "").strip()
        if not raw:
            return ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        models = [m.strip() for m in raw.split(",") if m.strip()]
        return models or ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

    # Upload
    max_upload_size_mb: int = 10

    # Local OCR (RapidOCR Det + VietOCR Seq2Seq Rec)
    local_ocr_enabled: bool = True
    local_ocr_batch_size: int = 16
    local_ocr_timeout_seconds: int = 30
    vietocr_model_path: str = ""
    vietocr_device: str = "cpu"
    vietocr_beamsearch: bool = False

    # RapidOCR Detector Tuning (chống gộp nhầm dòng & chống bỏ sót chữ)
    rapidocr_unclip_ratio: float = 1.70
    rapidocr_box_thresh: float = 0.50
    rapidocr_thresh: float = 0.20
    rapidocr_limit_side_len: int = 1536
    rapidocr_limit_type: str = "max"
    rapidocr_use_dilation: bool = False
    rapidocr_split_tall_boxes: bool = False
    rapidocr_enable_clahe: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
