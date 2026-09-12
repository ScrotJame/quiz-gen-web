from __future__ import annotations

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
from src.models.schemas import (
    AIGenerateRequest,
    Difficulty,
    GeneratedQuizResponse,
)
from src.services.ai.generator import QuizGeneratorService

router = APIRouter(prefix="/ai", tags=["AI Quiz Generator"])


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
    author_name: str = Form(default="OCR + Mistral AI", alias="authorName"),
) -> GeneratedQuizResponse:
    """OCR ảnh đề thi và sinh câu hỏi trắc nghiệm bằng Mistral AI theo mức nhiệt độ temperature."""
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
