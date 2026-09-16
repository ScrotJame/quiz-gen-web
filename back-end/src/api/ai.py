from __future__ import annotations

import io
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
from PIL import Image

from src.api.deps import get_quiz_generator_service
from src.config import get_settings
from src.core.exceptions import (
    AppError,
    GenerationFailedError,
    NoTextFoundError,
    RateLimitExceededError,
)
from src.models.schemas import (
    AIGenerateRequest,
    CleanTextRequest,
    CleanTextResponse,
    Difficulty,
    ExtractQuestionsRequest,
    ExtractQuestionsResponse,
    GeneratedQuizResponse,
    OcrPageResponse,
)
from src.services.ai.generator import QuizGeneratorService
from src.services.ai.ocr import extract_text_with_metadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Quiz Generator"])

_ALLOWED_IMAGE_TYPES = frozenset(
    ["image/jpeg", "image/png", "image/webp", "image/jpg"]
)
_MAX_PIXELS = 50_000_000  # Giới hạn 50 Megapixels chống Decompression Bomb


def _check_magic_bytes(data: bytes) -> bool:
    """Xác thực định dạng file qua magic bytes (PNG, JPEG, WebP)."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if data.startswith(b"\xff\xd8\xff"):
        return True
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return True
    return False


def validate_image_file(file: UploadFile, image_bytes: bytes, max_size_mb: int = 10) -> None:
    """Kiểm tra định dạng, magic bytes và kích thước/độ phân giải của file ảnh tải lên."""
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

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng file không hỗ trợ: {file.content_type}. Chỉ chấp nhận PNG/JPG/WEBP.",
        )

    if not _check_magic_bytes(image_bytes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tệp tải lên không phải là ảnh hợp lệ (chữ ký tệp không khớp PNG/JPEG/WEBP).",
        )

    # Chống Image Decompression Bomb / Pixel Flood DoS
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
            if width * height > _MAX_PIXELS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Độ phân giải ảnh quá lớn ({width}x{height} pixels). Giới hạn tối đa là 50 Megapixels.",
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Không thể giải mã header ảnh: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể đọc dữ liệu ảnh. Tệp có thể đã bị hỏng.",
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
        logger.error("Lỗi khi sinh đề bằng AI: %s", e, exc_info=True)
        raise GenerationFailedError("Không thể sinh đề thi bằng AI. Vui lòng kiểm tra lại yêu cầu hoặc thử lại sau.")


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
        logger.error("Lỗi khi xử lý OCR và sinh đề từ ảnh: %s", e, exc_info=True)
        raise GenerationFailedError("Không thể xử lý OCR và sinh đề từ ảnh. Vui lòng kiểm tra lại chất lượng ảnh.")


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
        logger.error("Lỗi khi xử lý OCR: %s", e, exc_info=True)
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            raise RateLimitExceededError(
                "Gemini API đang bị giới hạn tần suất và OCR offline cũng không khả dụng. Vui lòng đợi 15-20 giây rồi thử lại."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi khi xử lý OCR. Vui lòng thử lại sau hoặc đổi sang engine khác.",
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
    try:
        cleaned_text = await service.clean_text(
            raw_text=data.raw_text,
            target_language=data.target_language,
        )
        return CleanTextResponse(cleaned_text=cleaned_text)
    except AppError:
        raise
    except Exception as e:
        logger.error("Lỗi khi làm sạch văn bản bằng AI: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể làm sạch văn bản bằng AI. Vui lòng thử lại sau.",
        )


@router.post("/extract-questions", response_model=ExtractQuestionsResponse)
async def extract_questions_from_text(
    data: ExtractQuestionsRequest,
    service: Annotated[QuizGeneratorService, Depends(get_quiz_generator_service)],
) -> ExtractQuestionsResponse:
    """Bóc tách toàn bộ câu hỏi trắc nghiệm có sẵn trong văn bản đã OCR và chuẩn hóa."""
    try:
        return await service.extract_questions(
            raw_text=data.text,
            default_category=data.default_category,
            default_difficulty=data.default_difficulty,
        )
    except AppError:
        raise
    except Exception as e:
        logger.error("Lỗi khi bóc tách câu hỏi từ văn bản: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể bóc tách câu hỏi từ văn bản. Vui lòng kiểm tra lại nội dung.",
        )



