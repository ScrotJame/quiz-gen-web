from __future__ import annotations

import logging
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
from src.core.exceptions import (
    GenerationFailedError,
    NoTextFoundError,
    RateLimitExceededError,
)
from src.models.schemas import (
    AIGenerateRequest,
    CleanTextRequest,
    CleanTextResponse,
    Difficulty,
    GeneratedQuizResponse,
    OcrPageResponse,
)
from src.services.ai.generator import QuizGeneratorService
from src.services.ai.ocr import extract_text_with_metadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Quiz Generator"])

_ALLOWED_IMAGE_TYPES = frozenset(
    ["image/jpeg", "image/png", "image/webp", "image/jpg", "application/octet-stream"]
)


def validate_image_file(file: UploadFile, image_bytes: bytes, max_size_mb: int = 10) -> None:
    """Kiểm tra định dạng và kích thước của file ảnh tải lên."""
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng file không hỗ trợ: {file.content_type}. Chỉ chấp nhận PNG/JPG/WEBP.",
        )

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File ảnh tải lên bị rỗng.",
        )

    max_bytes = max_size_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File vượt quá kích thước cho phép ({max_size_mb} MB).",
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
        raise GenerationFailedError(f"Lỗi khi sinh đề bằng AI: {e}")


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
    author_name: str = Form(default="AI Quiz Generator", alias="authorName"),
    engine: str = Form(default="auto", description="Engine OCR: 'auto' | 'gemini' | 'local_vietocr'"),
) -> GeneratedQuizResponse:
    """OCR ảnh đề thi và sinh câu hỏi trắc nghiệm bằng AI theo mức nhiệt độ temperature."""
    settings = get_settings()
    image_bytes = await file.read()
    validate_image_file(file, image_bytes, settings.max_upload_size_mb)

    try:
        return await service.generate_from_image(
            image_bytes,
            num_questions=num_questions,
            difficulty=difficulty,
            temperature=temperature,
            save_immediately=save_immediately,
            author_name=author_name,
            preferred_engine=engine,
        )
    except Exception as e:
        raise GenerationFailedError(f"Lỗi khi xử lý OCR và sinh đề từ ảnh: {e}")


@router.post("/ocr-page", response_model=OcrPageResponse)
async def ocr_single_page(
    file: UploadFile = File(..., description="File ảnh trang sách (PNG, JPG, JPEG, WEBP)"),
    engine: str = Form(default="auto", description="Engine OCR: 'auto' | 'gemini' | 'local_vietocr'"),
    unclip_ratio: float | None = Form(default=None, description="Tùy chỉnh unclip_ratio của RapidOCR"),
    box_thresh: float | None = Form(default=None, description="Tùy chỉnh box_thresh của RapidOCR"),
    limit_side_len: int | None = Form(default=None, description="Độ phân giải tối đa quét ảnh"),
    enable_clahe: bool | None = Form(default=None, description="Bật/tắt tăng tương phản cục bộ CLAHE"),
    split_tall_boxes: bool | None = Form(default=None, description="Tách box cao bị gộp nhầm nhiều dòng"),
) -> OcrPageResponse:
    """Trích xuất văn bản từ một trang ảnh, trả về text + lineCount + averageConfidence."""
    settings = get_settings()
    image_bytes = await file.read()
    validate_image_file(file, image_bytes, settings.max_upload_size_mb)

    # Đóng gói det_params nếu có điều chỉnh từ frontend
    det_params: dict[str, float | int | bool] = {}
    if unclip_ratio is not None:
        det_params["unclip_ratio"] = unclip_ratio
    if box_thresh is not None:
        det_params["box_thresh"] = box_thresh
    if limit_side_len is not None:
        det_params["limit_side_len"] = limit_side_len
    if enable_clahe is not None:
        det_params["enable_clahe"] = enable_clahe
    if split_tall_boxes is not None:
        det_params["split_tall_boxes"] = split_tall_boxes

    try:
        result: OcrPageResponse = await extract_text_with_metadata(
            image_bytes,
            mime_type=file.content_type or "image/jpeg",
            preferred_engine=engine,
            det_params=det_params or None,
        )
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            raise RateLimitExceededError(
                "Gemini API đang bị giới hạn tần suất và OCR offline cũng không khả dụng. Vui lòng đợi 15-20 giây rồi thử lại."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý OCR: {e}",
        )

    if not result.text.strip():
        raise NoTextFoundError(
            "Không phát hiện văn bản trong ảnh. Vui lòng thử ảnh khác hoặc kiểm tra chất lượng ảnh."
        )

    return result


@router.post("/clean-text", response_model=CleanTextResponse)
async def clean_text(
    data: CleanTextRequest,
    service: Annotated[QuizGeneratorService, Depends(get_quiz_generator_service)],
) -> CleanTextResponse:
    """Làm sạch văn bản OCR thô bằng AI (sửa dấu tiếng Việt, nối câu liên trang)."""
    cleaned_text = await service.clean_text(
        raw_text=data.raw_text,
        target_language=data.target_language,
    )
    return CleanTextResponse(cleaned_text=cleaned_text)
