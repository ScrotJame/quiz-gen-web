from __future__ import annotations

import io
import logging
from typing import Any

from PIL import Image
from rapidocr_onnxruntime import RapidOCR

logger = logging.getLogger(__name__)

# Khởi tạo singleton RapidOCR để không load model nhiều lần
_ocr_engine: RapidOCR | None = None


def get_ocr_engine() -> RapidOCR:
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = RapidOCR()
    return _ocr_engine


def extract_text_from_image(image_bytes: bytes) -> str:
    """Trích xuất toàn bộ văn bản từ ảnh tải lên.

    Sử dụng RapidOCR (ONNX runtime) hỗ trợ tiếng Việt và tiếng Anh có dấu.
    """
    try:
        # Load image qua PIL để chuẩn hóa format RGB
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        engine = get_ocr_engine()
        result, elapse_list = engine(image)

        if not result:
            return ""

        # result là list các tuple: [box, text, confidence]
        extracted_lines: list[str] = []
        for item in result:
            if len(item) >= 2 and item[1]:
                text = str(item[1]).strip()
                if text:
                    extracted_lines.append(text)

        full_text = "\n".join(extracted_lines)
        return full_text
    except Exception as e:
        logger.error(f"Lỗi khi trích xuất OCR từ ảnh: {e}", exc_info=True)
        return ""
