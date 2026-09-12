import io
import pytest
from PIL import Image, ImageDraw

from src.models.schemas import Difficulty
from src.repositories.memory import InMemoryQuizRepository
from src.services.ai.generator import QuizGeneratorService
from src.services.ai.ocr import extract_text_from_image
from src.services.ai.prompts import build_system_prompt, build_user_prompt


def create_test_image_bytes(text: str = "Cau 1: 1+1=2") -> bytes:
    """Tạo ảnh bộ nhớ có chứa text để test OCR."""
    img = Image.new("RGB", (300, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_prompts_temperature_distinction():
    p_zero = build_system_prompt(0.0)
    assert "TRÍCH XUẤT NGUYÊN VĂN" in p_zero
    assert "CHÍNH XÁC 100%" in p_zero

    p_creative = build_system_prompt(0.3)
    assert "BIÊN TẬP THÔNG MINH" in p_creative
    assert "sửa lỗi chính tả từ bản quét OCR" in p_creative


@pytest.mark.asyncio
async def test_ocr_extraction():
    img_bytes = create_test_image_bytes("Hello OCR Test")
    extracted = await extract_text_from_image(img_bytes)
    # OCR should run and return a string
    assert isinstance(extracted, str)


@pytest.mark.asyncio
async def test_quiz_generator_mock_fallback():
    repo = InMemoryQuizRepository()
    service = QuizGeneratorService(repo)

    # 1. Generate without saving
    result = await service.generate_quiz(
        topic="Lập trình Python",
        num_questions=3,
        difficulty=Difficulty.EASY,
        temperature=0.0,
        save_immediately=False,
    )
    assert len(result.questions) == 3
    assert result.difficulty == Difficulty.EASY
    assert result.saved_quiz_id is None
    assert "Trích xuất" in result.questions[0].question_text

    # 2. Generate with save_immediately=True
    saved_result = await service.generate_quiz(
        topic="SQL Database",
        num_questions=2,
        difficulty=Difficulty.MEDIUM,
        temperature=0.5,
        save_immediately=True,
    )
    assert saved_result.saved_quiz_id is not None

    # Check in repo
    db_quiz = await repo.get_quiz(saved_result.saved_quiz_id)
    assert db_quiz is not None
    assert len(db_quiz.questions) == 2


@pytest.mark.asyncio
async def test_generate_from_image():
    repo = InMemoryQuizRepository()
    service = QuizGeneratorService(repo)
    img_bytes = create_test_image_bytes("Cau hoi trac nghiem toan hoc")

    result = await service.generate_from_image(
        img_bytes,
        num_questions=4,
        temperature=0.0,
        save_immediately=True,
    )
    assert len(result.questions) == 4
    assert result.saved_quiz_id is not None
