from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types

from src.config import get_settings
from src.services.ai.prompts import build_ocr_prompt

logger = logging.getLogger(__name__)

# Global singleton client
_gemini_client: genai.Client | None = None


def has_gemini_key() -> bool:
    """Kiểm tra xem API key của Gemini đã được cấu hình hợp lệ hay chưa."""
    settings = get_settings()
    key = (settings.gemini_api_key or "").strip()
    return bool(key) and "your-key" not in key.lower() and not key.lower().startswith("your-")


def get_gemini_client() -> genai.Client | None:
    """Lấy hoặc khởi tạo singleton genai.Client."""
    global _gemini_client
    if not has_gemini_key():
        return None
    if _gemini_client is None:
        settings = get_settings()
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


def _normalize_mime_type(mime_type: str) -> str:
    """Chuẩn hóa MIME type hợp lệ cho Gemini API."""
    mime = (mime_type or "").lower().strip()
    if "png" in mime:
        return "image/png"
    if "webp" in mime:
        return "image/webp"
    if "gif" in mime:
        return "image/gif"
    return "image/jpeg"


async def extract_text_via_gemini(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    custom_instruction: str | None = None,
) -> str:
    """Trích xuất toàn bộ văn bản từ ảnh qua Gemini Multimodal Vision.

    Sử dụng model cấu hình trong settings (mặc định: gemini-2.0-flash-lite).
    """
    client = get_gemini_client()
    if not client:
        raise ValueError("GEMINI_API_KEY chưa được cấu hình.")

    settings = get_settings()
    model_name = settings.gemini_ocr_model or "gemini-2.0-flash-lite"
    prompt = build_ocr_prompt(custom_instruction)
    normalized_mime = _normalize_mime_type(mime_type)

    logger.info(
        "Gửi yêu cầu OCR tới Gemini API (model: %s, mime: %s, size: %d bytes)",
        model_name,
        normalized_mime,
        len(image_bytes),
    )

    try:
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=normalized_mime)
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,
            ),
        )

        extracted_text = (response.text or "").strip()
        logger.info(
            "Gemini OCR thành công: trích xuất được %d ký tự",
            len(extracted_text),
        )
        return extracted_text
    except Exception as e:
        logger.error("Lỗi khi gọi Gemini OCR API: %s", e, exc_info=True)
        raise


async def call_gemini_chat(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    model: str | None = None,
    response_format_json: bool = True,
) -> str:
    """Gửi yêu cầu chat completion / sinh đề thi tới Google Gemini AI."""
    client = get_gemini_client()
    if not client:
        raise ValueError("GEMINI_API_KEY chưa được cấu hình.")

    settings = get_settings()
    chosen_model = model or settings.gemini_model or "gemini-3.1-flash-lite"

    logger.info(
        "Gửi yêu cầu Gemini chat completion (model: %s, temperature: %.2f)",
        chosen_model,
        temperature,
    )

    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_prompt if system_prompt else None,
        response_mime_type="application/json" if response_format_json else None,
    )

    try:
        response = await client.aio.models.generate_content(
            model=chosen_model,
            contents=[user_prompt],
            config=config,
        )
        content = (response.text or "").strip()
        return content
    except Exception as e:
        logger.error("Lỗi khi gọi Gemini chat: %s", e, exc_info=True)
        raise

