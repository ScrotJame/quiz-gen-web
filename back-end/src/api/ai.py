from __future__ import annotations

import json
import logging
import re
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from src.api.deps import get_quiz_generator_service
from src.config import get_settings
from src.models.schemas import (
    AIGenerateRequest,
    CleanTextRequest,
    CleanTextResponse,
    Difficulty,
    GeneratedQuizResponse,
    OcrPageResponse,
)
from src.services.ai.generator import QuizGeneratorService
from src.services.ai.gemini_client import call_gemini_chat, has_gemini_key
from src.services.ai.ocr import extract_text_with_metadata
from src.services.ai.prompts import build_clean_text_prompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Quiz Generator"])

_ALLOWED_IMAGE_TYPES = frozenset(
    ["image/jpeg", "image/png", "image/webp", "image/jpg", "application/octet-stream"]
)


@router.post("/generate", response_model=GeneratedQuizResponse)
async def generate_quiz_from_text(
    data: AIGenerateRequest,
    service: Annotated[QuizGeneratorService, Depends(get_quiz_generator_service)],
) -> GeneratedQuizResponse:
    """Sinh câu hỏi trắc nghiệm từ chủ đề hoặc nội dung văn bản."""
    try:
        return await service.generate_quiz(
            topic=data.topic,
            content=data.content,
            num_questions=data.num_questions,
            difficulty=data.difficulty,
            temperature=data.temperature,
            save_immediately=data.save_immediately,
            author_name=data.author_name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi sinh đề bằng AI: {e}",
        )


@router.post("/generate-from-image", response_model=GeneratedQuizResponse)
async def generate_quiz_from_image(
    service: Annotated[QuizGeneratorService, Depends(get_quiz_generator_service)],
    file: UploadFile = File(..., description="File ảnh đề thi (PNG, JPG, JPEG, WEBP)"),
    num_questions: int = Form(default=5, alias="numQuestions"),
    difficulty: Difficulty = Form(default=Difficulty.MEDIUM),
    temperature: float = Form(
        default=0.0,
        description="0.0: Trích xuất nguyên văn 100%; > 0.0: Biên tập sửa lỗi OCR",
    ),
    save_immediately: bool = Form(default=False, alias="saveImmediately"),
    author_name: str = Form(default="Gemini OCR + AI", alias="authorName"),
) -> GeneratedQuizResponse:
    """OCR ảnh đề thi và sinh câu hỏi trắc nghiệm bằng Gemini AI theo mức nhiệt độ temperature."""
    # Kiểm tra content type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg", "application/octet-stream"]
    if file.content_type and file.content_type.lower() not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng file không hỗ trợ: {file.content_type}. Vui lòng tải file ảnh PNG/JPG/WEBP.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File ảnh tải lên bị rỗng.",
        )

    try:
        return await service.generate_from_image(
            image_bytes,
            num_questions=num_questions,
            difficulty=difficulty,
            temperature=temperature,
            save_immediately=save_immediately,
            author_name=author_name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý OCR và sinh đề từ ảnh: {e}",
        )


@router.post("/ocr-page", response_model=OcrPageResponse)
async def ocr_single_page(
    file: UploadFile = File(..., description="File ảnh trang sách (PNG, JPG, JPEG, WEBP)"),
) -> OcrPageResponse:
    """Trích xuất văn bản từ một trang ảnh, trả về text + lineCount + averageConfidence."""
    settings = get_settings()

    # Validate content type
    if file.content_type and file.content_type.lower() not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng file không hỗ trợ: {file.content_type}. Chỉ chấp nhận PNG/JPG/WEBP.",
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File ảnh tải lên bị rỗng.",
        )

    # Validate file size
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File vượt quá kích thước cho phép ({settings.max_upload_size_mb} MB).",
        )

    # Trích xuất văn bản (Gemini Vision OCR hoặc RapidOCR fallback)
    result: OcrPageResponse = await extract_text_with_metadata(
        image_bytes,
        mime_type=file.content_type or "image/jpeg",
    )

    if not result.text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "NO_TEXT_FOUND",
                "message": "Không phát hiện văn bản trong ảnh. Vui lòng thử ảnh khác hoặc kiểm tra chất lượng ảnh.",
            },
        )

    return result


@router.post("/clean-text", response_model=CleanTextResponse)
async def clean_text(
    data: CleanTextRequest,
    service: Annotated[QuizGeneratorService, Depends(get_quiz_generator_service)],
) -> CleanTextResponse:
    """Làm sạch văn bản OCR thô bằng Gemini AI (sửa dấu tiếng Việt, nối câu liên trang)."""
    # Fallback nếu không có API key
    if not has_gemini_key():
        logger.info("Không có GEMINI_API_KEY — trả nguyên raw_text làm fallback.")
        return CleanTextResponse(cleaned_text=data.raw_text)

    system_prompt, user_prompt = build_clean_text_prompt(data.raw_text, data.target_language)

    try:
        raw_response = await call_gemini_chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )
    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini để làm sạch text: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Không thể kết nối với dịch vụ AI. Vui lòng thử lại sau.",
        )

    # Parse JSON response
    try:
        cleaned = raw_response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        parsed = json.loads(cleaned)
        cleaned_text = parsed.get("cleanedText", data.raw_text)
    except Exception:
        # AI trả về format không đúng — fallback về raw text
        logger.warning("Không parse được JSON từ Gemini clean-text, dùng raw_text fallback.")
        cleaned_text = data.raw_text

    return CleanTextResponse(cleaned_text=cleaned_text)

