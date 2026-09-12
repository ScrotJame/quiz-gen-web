from __future__ import annotations

import logging

from src.models.schemas import OcrPageResponse
from src.services.ai.gemini_client import extract_text_via_gemini, has_gemini_key
from src.services.ai.local_ocr import get_local_ocr_engine

logger = logging.getLogger(__name__)


async def extract_text_from_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    preferred_engine: str = "auto",
    det_params: dict | None = None,
) -> str:
    """Trích xuất toàn bộ văn bản từ ảnh tải lên.

    Ưu tiên 1: Gemini Vision OCR (chất lượng tốt nhất, hỗ trợ công thức toán).
    Ưu tiên 2: Local OCR (RapidOCR Det + VietOCR ONNX) khi Gemini không khả dụng hoặc không có kết quả.
    """
    # Nếu yêu cầu dùng trực tiếp Local OCR / VietOCR
    if preferred_engine == "local_vietocr":
        engine = get_local_ocr_engine()
        if engine is not None:
            try:
                return await engine.extract_text(image_bytes, mime_type, det_params=det_params)
            except Exception as e:
                logger.error("Local OCR that bai: %s", e, exc_info=True)
        return ""

    # --- 1. Gemini Vision OCR (primary nếu không chỉ định local_vietocr) ---
    if preferred_engine != "local_vietocr" and has_gemini_key():
        try:
            text = await extract_text_via_gemini(image_bytes, mime_type=mime_type)
            if text.strip():
                return text
            logger.info("Gemini Vision OCR khong tim thay chu, tu dong chuyen sang Local OCR fallback...")
        except Exception as e:
            logger.warning(
                "Gemini Vision OCR that bai (%s), chuyen sang Local OCR fallback...", e
            )
            # Fall through to local OCR

    # Nếu chỉ định riêng gemini mà không muốn fallback
    if preferred_engine == "gemini":
        return ""

    # --- 2. Local OCR fallback (RapidOCR Det + VietOCR ONNX) ---
    engine = get_local_ocr_engine()
    if engine is not None:
        try:
            text = await engine.extract_text(image_bytes, mime_type, det_params=det_params)
            if text.strip():
                logger.info(
                    "Local OCR fallback thanh cong: %d ky tu duoc trich xuat.",
                    len(text),
                )
                return text
        except Exception as e:
            logger.error("Local OCR fallback cung that bai: %s", e, exc_info=True)

    logger.info("Khong co OCR engine nao kha dung hoac khong phat hien chu.")
    return ""


async def extract_text_with_metadata(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    preferred_engine: str = "auto",
    det_params: dict | None = None,
) -> OcrPageResponse:
    """Trích xuất văn bản từ ảnh và trả về kèm metadata.

    Ưu tiên 1: Gemini Vision OCR.
    Ưu tiên 2: Local OCR (RapidOCR Det + VietOCR ONNX) khi Gemini thất bại hoặc không nhận diện được chữ.
    """
    # Nếu yêu cầu dùng trực tiếp Local OCR / VietOCR
    if preferred_engine == "local_vietocr":
        engine = get_local_ocr_engine()
        if engine is not None:
            try:
                return await engine.extract_text_with_metadata(image_bytes, mime_type, det_params=det_params)
            except Exception as e:
                logger.error("Local OCR (metadata) that bai: %s", e, exc_info=True)
        return OcrPageResponse(text="", line_count=0, average_confidence=0.0, provider="local_vietocr")

    # --- 1. Gemini Vision OCR (primary nếu không chỉ định local_vietocr) ---
    if preferred_engine != "local_vietocr" and has_gemini_key():
        try:
            text = await extract_text_via_gemini(image_bytes, mime_type=mime_type)
            if text.strip():
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                return OcrPageResponse(
                    text=text,
                    line_count=len(lines),
                    average_confidence=1.0,
                    provider="gemini",
                )
            logger.info("Gemini OCR khong tim thay text trong anh, chuyen sang Local OCR fallback...")
        except Exception as e:
            logger.warning(
                "Gemini OCR that bai (metadata mode) (%s), thu Local OCR...", e
            )
            # Fall through to local OCR

    # Nếu chỉ định riêng gemini mà không muốn fallback
    if preferred_engine == "gemini":
        return OcrPageResponse(text="", line_count=0, average_confidence=0.0, provider="gemini")

    # --- 2. Local OCR fallback ---
    engine = get_local_ocr_engine()
    if engine is not None:
        try:
            result = await engine.extract_text_with_metadata(image_bytes, mime_type, det_params=det_params)
            if result.text.strip():
                logger.info(
                    "Local OCR fallback (metadata): %d dong, %d ky tu.",
                    result.line_count,
                    len(result.text),
                )
            return result
        except Exception as e:
            logger.error(
                "Local OCR fallback (metadata) cung that bai: %s", e, exc_info=True
            )

    return OcrPageResponse(text="", line_count=0, average_confidence=0.0, provider="unknown")

