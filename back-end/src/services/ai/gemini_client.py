from __future__ import annotations

import logging
from typing import Any

import numpy as np
from google import genai
from google.genai import types

from src.config import get_settings
from src.services.ai.prompts import build_ocr_prompt

logger = logging.getLogger(__name__)

# Global singleton client
_gemini_client: genai.Client | None = None


def _import_cv2() -> Any | None:
    """Trả về module cv2 hoặc None nếu package chưa cài."""
    try:
        import cv2  # type: ignore[import-untyped]

        return cv2
    except ImportError:
        return None


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

    Thử lần lượt danh sách model được cấu hình linh hoạt qua biến môi trường
    (GEMINI_OCR_MODELS / GEMINI_OCR_MODEL). Nếu model đầu tiên gặp lỗi (429/quota/không khả dụng),
    tự động thử các model tiếp theo trong danh sách trước khi báo lỗi hoặc fallback.
    """
    client = get_gemini_client()
    if not client:
        raise ValueError("GEMINI_API_KEY chưa được cấu hình.")

    settings = get_settings()

    # Xác định danh sách candidate models từ Settings hoặc env
    candidate_models: list[str] = []
    if isinstance(getattr(settings, "gemini_ocr_models", None), str) and settings.gemini_ocr_models.strip():
        candidate_models = [m.strip() for m in settings.gemini_ocr_models.split(",") if m.strip()]
    elif isinstance(getattr(settings, "gemini_ocr_model", None), str) and settings.gemini_ocr_model.strip():
        candidate_models = [settings.gemini_ocr_model.strip()]
    elif hasattr(settings, "ocr_model_list") and isinstance(settings.ocr_model_list, (list, tuple)):
        candidate_models = list(settings.ocr_model_list)
    else:
        candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

    prompt = build_ocr_prompt(custom_instruction)
    normalized_mime = _normalize_mime_type(mime_type)

    cv2 = _import_cv2()
    if cv2 is not None:
        try:
            from src.services.ai.page_normalization import normalize_page

            nparr = np.frombuffer(image_bytes, np.uint8)
            cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if cv_img is not None and cv_img.size > 0:
                norm_img = normalize_page(cv_img)
                success, encoded = cv2.imencode(".jpg", norm_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
                if success:
                    image_bytes = encoded.tobytes()
                    normalized_mime = "image/jpeg"
        except Exception as e:
            logger.debug("Page normalization cho Gemini bỏ qua (%s)", e)

    system_prompt = (
        getattr(settings, "gemini_ocr_system_prompt", None)
        or "Perform OCR on this image. Ignore perspective distortion and page curvature. Transcribe all readable text verbatim."
    )

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=normalized_mime)
    last_error: Exception | None = None

    for model_name in candidate_models:
        logger.info(
            "Gửi yêu cầu OCR tới Gemini API (model: %s, mime: %s, size: %d bytes)",
            model_name,
            normalized_mime,
            len(image_bytes),
        )
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=[image_part, prompt],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    system_instruction=system_prompt,
                ),
            )
            extracted_text = (response.text or "").strip()
            if extracted_text:
                logger.info(
                    "Gemini OCR thành công với model '%s': trích xuất được %d ký tự",
                    model_name,
                    len(extracted_text),
                )
                return extracted_text
            logger.info("Gemini OCR (model '%s') không tìm thấy chữ trong ảnh.", model_name)
        except Exception as e:
            last_error = e
            logger.warning(
                "Gemini OCR với model '%s' thất bại (%s). Đang thử model tiếp theo trong danh sách...",
                model_name,
                e,
            )

    if last_error:
        raise last_error

    return ""


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

