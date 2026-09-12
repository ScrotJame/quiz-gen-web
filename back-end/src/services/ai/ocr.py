from __future__ import annotations

import asyncio
import logging
from typing import Any

from rapidocr_onnxruntime import RapidOCR

from src.models.schemas import OcrPageResponse
from src.services.ai.gemini_client import extract_text_via_gemini, has_gemini_key

logger = logging.getLogger(__name__)

# Khởi tạo singleton RapidOCR để làm offline fallback
_ocr_engine: RapidOCR | None = None


def get_ocr_engine() -> RapidOCR:
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = RapidOCR()
    return _ocr_engine


def _extract_rapidocr(image_bytes: bytes) -> str:
    """Hàm trích xuất RapidOCR đồng bộ dùng làm fallback."""
    try:
        engine = get_ocr_engine()
        result, _ = engine(image_bytes)

        if not result:
            return ""

        extracted_lines: list[str] = []
        for item in result:
            if len(item) >= 2 and item[1]:
                text = str(item[1]).strip()
                if text:
                    extracted_lines.append(text)

        return "\n".join(extracted_lines)
    except Exception as e:
        logger.error("Lỗi khi trích xuất RapidOCR fallback: %s", e, exc_info=True)
        return ""


def _extract_rapidocr_with_metadata(image_bytes: bytes) -> OcrPageResponse:
    """Hàm trích xuất RapidOCR kèm metadata đồng bộ dùng làm fallback."""
    try:
        engine = get_ocr_engine()
        result, _ = engine(image_bytes)

        if not result:
            return OcrPageResponse(text="", line_count=0, average_confidence=0.0)

        lines: list[str] = []
        confidences: list[float] = []
        for item in result:
            if len(item) >= 3 and item[1]:
                text = str(item[1]).strip()
                if text:
                    lines.append(text)
                    confidences.append(float(item[2]))

        return OcrPageResponse(
            text="\n".join(lines),
            line_count=len(lines),
            average_confidence=round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
        )
    except Exception as e:
        logger.error("Lỗi khi trích xuất RapidOCR với metadata: %s", e, exc_info=True)
        return OcrPageResponse(text="", line_count=0, average_confidence=0.0)


async def extract_text_from_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> str:
    """Trích xuất toàn bộ văn bản từ ảnh tải lên.

    Ưu tiên sử dụng Gemini Vision (gemini-2.0-flash-lite) cho tiếng Việt chính xác.
    Nếu chưa cấu hình GEMINI_API_KEY hoặc gặp lỗi API, tự động fallback sang RapidOCR.
    """
    if has_gemini_key():
        try:
            text = await extract_text_via_gemini(image_bytes, mime_type=mime_type)
            if text.strip():
                return text
        except Exception as e:
            logger.warning(
                "Gemini OCR thất bại (%s), tự động chuyển sang RapidOCR fallback.", e
            )

    return await asyncio.to_thread(_extract_rapidocr, image_bytes)


async def extract_text_with_metadata(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> OcrPageResponse:
    """Trích xuất văn bản từ ảnh và trả về kèm metadata (lineCount, averageConfidence).

    Ưu tiên sử dụng Gemini Vision Multimodal cho OCR tài liệu tiếng Việt.
    Nếu không có key hoặc lỗi, tự động fallback sang RapidOCR.
    """
    if has_gemini_key():
        try:
            text = await extract_text_via_gemini(image_bytes, mime_type=mime_type)
            if text.strip():
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                return OcrPageResponse(
                    text=text,
                    line_count=len(lines),
                    average_confidence=1.0,
                )
            return OcrPageResponse(text="", line_count=0, average_confidence=0.0)
        except Exception as e:
            logger.warning(
                "Gemini OCR thất bại (%s), tự động chuyển sang RapidOCR fallback.", e
            )

    return await asyncio.to_thread(_extract_rapidocr_with_metadata, image_bytes)
