"""TDD - Test cho tính năng Bóc tách toàn bộ câu hỏi (Question Extraction).

Chạy: pytest back-end/tests/test_extract_questions.py -v
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from src.models.schemas import (
    BankOptionCreate,
    BankQuestionCreate,
    ExtractQuestionsRequest,
    ExtractQuestionsResponse,
)
from src.repositories.memory import InMemoryQuizRepository
from src.services.ai.generator import QuizGeneratorService
from src.services.ai.prompts import build_extract_questions_prompt


# ─── 1. Test Prompt Generation ───────────────────────────────────────────────


def test_build_extract_questions_prompt():
    raw_text = "Câu 1: Thủ đô nước Pháp là gì?\nA. London\nB. Paris\nC. Rome\nD. Berlin"
    sys_p, user_p = build_extract_questions_prompt(raw_text, default_category="Địa lý")

    assert "BÓC TÁCH TOÀN BỘ" in sys_p
    assert "KHÔNG TỰ SINH CÂU HỎI MỚI" in sys_p
    assert "Địa lý" in sys_p
    assert "Thủ đô nước Pháp" in user_p


# ─── 2. Test QuizGeneratorService.extract_questions ─────────────────────────


@pytest.mark.asyncio
async def test_extract_questions_fallback_regex():
    """Khi không có API key AI, service dùng regex parser bóc tách câu hỏi từ text."""
    sample_text = """
    Câu 1: 1 + 1 bằng bao nhiêu?
    A. 1
    B. 2
    C. 3
    D. 4

    Câu 2: Đơn vị đo cường độ dòng điện là gì?
    A. Vôn
    B. Ampe
    C. Ôm
    D. Oát
    """
    repo = InMemoryQuizRepository()
    service = QuizGeneratorService(repo)

    result = await service.extract_questions(sample_text, default_category="Khoa học")
    assert isinstance(result, ExtractQuestionsResponse)
    assert len(result.questions) == 2
    assert result.total_extracted == 2

    q1 = result.questions[0]
    assert "1 + 1" in q1.question_text
    assert q1.category == "Khoa học"
    assert len(q1.options) == 4

    q2 = result.questions[1]
    assert "cường độ dòng điện" in q2.question_text
    assert len(q2.options) == 4


@pytest.mark.asyncio
async def test_extract_questions_empty_text():
    """Khi text không có câu hỏi trắc nghiệm nào, trả về danh sách rỗng."""
    sample_text = "Đây chỉ là đoạn văn bản thuyết minh chung chung, không có câu hỏi trắc nghiệm nào cả."
    repo = InMemoryQuizRepository()
    service = QuizGeneratorService(repo)

    result = await service.extract_questions(sample_text)
    assert isinstance(result, ExtractQuestionsResponse)
    assert len(result.questions) == 0
    assert result.total_extracted == 0


@pytest.mark.asyncio
async def test_extract_questions_with_llm_json():
    """Khi LLM trả về JSON hợp lệ, service parse chính xác danh sách câu hỏi."""
    mock_llm_output = """
    {
      "questions": [
        {
          "questionText": "Ngôn ngữ lập trình nào phổ biến cho AI?",
          "questionType": "single_choice",
          "category": "Tin học",
          "difficulty": "medium",
          "explanation": "Python có hệ sinh thái thư viện AI phong phú.",
          "sourceNote": "Trích xuất từ đề thi",
          "options": [
            {"optionText": "Python", "isCorrect": true, "orderNum": 0},
            {"optionText": "PHP", "isCorrect": false, "orderNum": 1},
            {"optionText": "Pascal", "isCorrect": false, "orderNum": 2}
          ]
        }
      ]
    }
    """
    repo = InMemoryQuizRepository()
    service = QuizGeneratorService(repo)

    with patch("src.services.ai.generator.has_gemini_key", return_value=True), \
         patch("src.services.ai.generator.call_gemini_chat", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_llm_output

        result = await service.extract_questions("Đề thi tin học...", default_category="Tin học")
        assert len(result.questions) == 1
        assert result.total_extracted == 1
        assert result.questions[0].question_text == "Ngôn ngữ lập trình nào phổ biến cho AI?"
        assert result.questions[0].options[0].is_correct is True


# ─── 3. Test API Endpoint POST /api/v1/ai/extract-questions ─────────────────


@pytest.fixture
async def client():
    from src.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_extract_questions_endpoint(client):
    payload = {
        "text": "Câu 1: Mặt trời mọc hướng nào?\nA. Đông\nB. Tây\nC. Nam\nD. Bắc",
        "defaultCategory": "Khoa học tự nhiên",
    }
    response = await client.post("/api/v1/ai/extract-questions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert "totalExtracted" in data
    assert data["totalExtracted"] >= 1
    assert data["questions"][0]["category"] == "Khoa học tự nhiên"
