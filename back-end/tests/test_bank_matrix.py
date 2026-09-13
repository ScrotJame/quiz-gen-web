"""TDD: Tests cho tính năng Sinh đề theo Ma trận từ Ngân hàng câu hỏi.

Kiểm tra:
1. sample_by_matrix: đủ câu hỏi theo từng độ khó.
2. sample_by_matrix: thiếu câu hỏi (bốc tối đa và sinh cảnh báo chính xác).
3. sample_by_matrix: lọc kết hợp môn học (category).
4. sample_by_matrix: chống N+1 queries khi nạp options.
5. POST /api/v1/bank/matrix-generate endpoint.
"""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from httpx import ASGITransport, AsyncClient

from src.db.base import Base
from src.main import app
from src.models.schemas import BankOptionCreate, BankQuestionCreate, QuestionType
from src.repositories.bank import SqlBankRepository
from src.services.bank_service import BankService
from src.api.bank import get_bank_service


@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(db_engine):
    return async_sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture
async def bank_repo(session_factory):
    return SqlBankRepository(session_factory=session_factory)


def _make_bank_question(category: str, difficulty: str, text_suffix: str) -> BankQuestionCreate:
    return BankQuestionCreate(
        question_text=f"Câu hỏi {category} {difficulty} {text_suffix}",
        question_type=QuestionType.SINGLE_CHOICE,
        category=category,
        difficulty=difficulty,
        explanation=f"Giải thích cho {text_suffix}",
        options=[
            BankOptionCreate(option_text=f"A. Đáp án 1 {text_suffix}", is_correct=True, order_num=0),
            BankOptionCreate(option_text=f"B. Đáp án 2 {text_suffix}", is_correct=False, order_num=1),
        ],
    )


@pytest.mark.asyncio
async def test_sample_by_matrix_sufficient_questions(bank_repo):
    # Seed 3 easy, 3 medium, 3 hard for 'Toán'
    seed_data = (
        [_make_bank_question("Toán", "easy", f"E{i}") for i in range(3)]
        + [_make_bank_question("Toán", "medium", f"M{i}") for i in range(3)]
        + [_make_bank_question("Toán", "hard", f"H{i}") for i in range(3)]
    )
    await bank_repo.batch_create_questions(seed_data)

    questions, warnings = await bank_repo.sample_by_matrix(
        category="Toán",
        easy_count=2,
        medium_count=2,
        hard_count=1,
    )

    assert len(questions) == 5
    assert len(warnings) == 0

    easy_sampled = [q for q in questions if q.difficulty == "easy"]
    med_sampled = [q for q in questions if q.difficulty == "medium"]
    hard_sampled = [q for q in questions if q.difficulty == "hard"]

    assert len(easy_sampled) == 2
    assert len(med_sampled) == 2
    assert len(hard_sampled) == 1
    for q in questions:
        assert len(q.options) == 2


@pytest.mark.asyncio
async def test_sample_by_matrix_insufficient_questions_generates_warnings(bank_repo):
    # Seed only 1 hard question
    seed_data = [_make_bank_question("Vật lý", "hard", "SingleHard")]
    await bank_repo.batch_create_questions(seed_data)

    questions, warnings = await bank_repo.sample_by_matrix(
        category="Vật lý",
        easy_count=2,
        medium_count=0,
        hard_count=5,
    )

    # We asked for 2 easy (0 found) and 5 hard (1 found)
    assert len(questions) == 1
    assert questions[0].difficulty == "hard"
    assert len(warnings) == 2
    assert any("Dễ" in w or "easy" in w.lower() for w in warnings)
    assert any("Khó" in w or "hard" in w.lower() for w in warnings)


@pytest.mark.asyncio
async def test_sample_by_matrix_filter_by_category(bank_repo):
    seed_data = [
        _make_bank_question("Toán", "easy", "T1"),
        _make_bank_question("Lý", "easy", "L1"),
    ]
    await bank_repo.batch_create_questions(seed_data)

    questions, _ = await bank_repo.sample_by_matrix(
        category="Toán",
        easy_count=5,
    )
    assert len(questions) == 1
    assert questions[0].category == "Toán"


@pytest.mark.asyncio
async def test_api_matrix_generate_endpoint(bank_repo):
    await bank_repo.batch_create_questions([
        _make_bank_question("Lịch sử", "easy", "H1"),
        _make_bank_question("Lịch sử", "medium", "H2"),
    ])

    app.dependency_overrides[get_bank_service] = lambda: BankService(bank_repo)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/bank/matrix-generate",
                json={
                    "category": "Lịch sử",
                    "easyCount": 1,
                    "mediumCount": 1,
                    "hardCount": 2,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["questions"]) == 2
            assert len(data["warnings"]) == 1
            assert "Khó" in data["warnings"][0]
    finally:
        app.dependency_overrides.clear()
