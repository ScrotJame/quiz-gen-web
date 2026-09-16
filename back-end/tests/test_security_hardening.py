import io
import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from src.main import app
from src.core.rate_limit import InMemoryRateLimiter, RateLimitMiddleware
from src.models.schemas import OptionSchema, QuestionSchema, QuizDetail, Difficulty, QuestionType
from src.services.quiz_service import QuizService
from src.repositories.memory import InMemoryQuizRepository, InMemoryAttemptRepository
from src.services.attempt_service import AttemptService
from src.models.schemas import QuizCreate, QuestionCreate, OptionCreate, SubmitAttemptRequest, AnswerSubmission


@pytest.fixture
def client():
    return TestClient(app)


def test_magic_bytes_validation_rejects_fake_png(client):
    """File có content-type image/png nhưng nội dung là text thường phải bị từ chối 400."""
    fake_png_data = b"This is not a valid PNG image file at all."
    files = {
        "file": ("fake.png", fake_png_data, "image/png"),
    }
    response = client.post("/api/v1/ai/ocr-page", files=files)
    assert response.status_code == 400
    assert "chữ ký tệp không khớp" in response.text or "không phải là ảnh hợp lệ" in response.text


def test_magic_bytes_validation_accepts_real_png(client):
    """File ảnh PNG hợp lệ được tạo bằng PIL phải vượt qua bước validate magic bytes."""
    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    valid_png_data = buf.getvalue()

    files = {
        "file": ("test.png", valid_png_data, "image/png"),
    }
    response = client.post("/api/v1/ai/ocr-page", files=files)
    # Không bị lỗi 400 của validate_image_file (có thể trả về 422 NO_TEXT_FOUND vì ảnh trắng)
    assert response.status_code in (200, 422, 500, 502)
    if response.status_code == 400:
        assert "chữ ký tệp không khớp" not in response.text


@pytest.mark.asyncio
async def test_quiz_service_masks_answers_and_explanation():
    """Kiểm tra quiz_service.get_quiz ẩn is_correct và explanation khi lấy đề thi."""
    quiz_repo = InMemoryQuizRepository()
    quiz_service = QuizService(quiz_repo)

    # Tạo đề thi mẫu
    quiz = await quiz_repo.create_quiz(
        QuizCreate(
            title="Đề thi bảo mật",
            category="Security",
            difficulty=Difficulty.MEDIUM,
            questions=[
                QuestionCreate(
                    question_text="Câu hỏi 1?",
                    question_type=QuestionType.SINGLE_CHOICE,
                    points=10,
                    explanation="Giải thích bí mật cho câu 1",
                    options=[
                        OptionCreate(option_text="A", is_correct=True, order_num=0),
                        OptionCreate(option_text="B", is_correct=False, order_num=1),
                    ],
                )
            ],
        )
    )

    # Lấy đề thi qua get_quiz (mặc định mask_answers=True)
    masked_quiz = await quiz_service.get_quiz(quiz.id)
    assert len(masked_quiz.questions) == 1
    q = masked_quiz.questions[0]

    # Đáp án và giải thích phải bị ẩn
    assert q.explanation is None
    for opt in q.options:
        assert opt.is_correct is None

    # Khi truyền mask_answers=False thì vẫn xem được nguyên bản (dùng cho backend grading)
    raw_quiz = await quiz_service.get_quiz(quiz.id, mask_answers=False)
    assert raw_quiz.questions[0].explanation == "Giải thích bí mật cho câu 1"
    assert raw_quiz.questions[0].options[0].is_correct is True


@pytest.mark.asyncio
async def test_attempt_submission_reveals_correct_answers_and_explanation():
    """Sau khi thí sinh nộp bài, AttemptResult phải chứa correct_option_ids và explanation."""
    quiz_repo = InMemoryQuizRepository()
    attempt_repo = InMemoryAttemptRepository()
    attempt_service = AttemptService(attempt_repo, quiz_repo)

    quiz = await quiz_repo.create_quiz(
        QuizCreate(
            title="Đề thi trắc nghiệm",
            category="Chung",
            difficulty=Difficulty.EASY,
            questions=[
                QuestionCreate(
                    question_text="2 + 2 = ?",
                    points=10,
                    explanation="2 cộng 2 bằng 4 theo toán học cơ bản.",
                    options=[
                        OptionCreate(option_text="3", is_correct=False, order_num=0),
                        OptionCreate(option_text="4", is_correct=True, order_num=1),
                    ],
                )
            ],
        )
    )

    # Thí sinh bắt đầu làm bài
    attempt = await attempt_service.start_attempt(quiz.id, "Nguyen Van A")
    q = quiz.questions[0]
    opt_correct = [o for o in q.options if o.is_correct][0]

    # Thí sinh nộp bài chọn phương án đúng
    result = await attempt_service.submit_attempt(
        attempt.id,
        SubmitAttemptRequest(
            answers=[
                AnswerSubmission(
                    question_id=q.id,
                    selected_option_ids=[opt_correct.id],
                )
            ]
        ),
    )

    assert result.score == 10
    assert len(result.answers) == 1
    ans = result.answers[0]
    assert ans.is_correct is True
    assert ans.correct_option_ids == [opt_correct.id]
    assert ans.explanation == "2 cộng 2 bằng 4 theo toán học cơ bản."


@pytest.mark.asyncio
async def test_in_memory_rate_limiter():
    """Kiểm tra InMemoryRateLimiter chặn request khi vượt quá ngưỡng."""
    limiter = InMemoryRateLimiter()
    key = "test_client_ip"

    # Cho phép tối đa 3 requests trong 10 giây
    for _ in range(3):
        allowed, retry_after = await limiter.is_allowed(key, max_requests=3, window_seconds=10.0)
        assert allowed is True
        assert retry_after == 0

    # Request thứ 4 phải bị block
    allowed, retry_after = await limiter.is_allowed(key, max_requests=3, window_seconds=10.0)
    assert allowed is False
    assert retry_after > 0
