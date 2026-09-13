"""TDD - RED PHASE: Test cho Bank Repository (Ngân hàng câu hỏi).

Chạy: pytest back-end/tests/test_bank_repository.py -v
"""

import uuid
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.db.base import Base
from src.models.schemas import (
    BankOptionCreate,
    BankQuestionCreate,
    BankQuestionUpdate,
    Difficulty,
    QuestionType,
)
from src.repositories.bank import SqlBankRepository


@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def bank_repo(db_engine):
    sm = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    return SqlBankRepository(session_factory=sm)


def make_question(
    text: str = "Câu hỏi mẫu?",
    category: str = "Toán",
    difficulty: str = "medium",
    n_options: int = 4,
) -> BankQuestionCreate:
    options = [
        BankOptionCreate(
            option_text=f"Đáp án {chr(65 + i)}",
            is_correct=(i == 0),
            order_num=i,
        )
        for i in range(n_options)
    ]
    return BankQuestionCreate(
        question_text=text,
        question_type=QuestionType.SINGLE_CHOICE,
        category=category,
        difficulty=difficulty,
        explanation="Giải thích mẫu.",
        source_note="OCR batch test",
        options=options,
    )


# ─── Batch Insert Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_create_returns_all_questions(bank_repo):
    """Batch insert trả về đúng số lượng câu hỏi đã lưu."""
    questions = [make_question(text=f"Câu {i}?") for i in range(5)]
    created = await bank_repo.batch_create_questions(questions)

    assert len(created) == 5
    for q in created:
        assert q.id is not None
        assert len(q.options) == 4


@pytest.mark.asyncio
async def test_batch_create_options_are_loaded(bank_repo):
    """Sau batch insert, options được load đúng (không N+1)."""
    q = make_question()
    [result] = await bank_repo.batch_create_questions([q])

    assert len(result.options) == 4
    correct_opts = [o for o in result.options if o.is_correct]
    assert len(correct_opts) == 1
    assert correct_opts[0].option_text == "Đáp án A"


@pytest.mark.asyncio
async def test_batch_create_large_batch(bank_repo):
    """Batch insert 50 câu trong 1 transaction."""
    questions = [make_question(text=f"Câu số {i}?", n_options=4) for i in range(50)]
    created = await bank_repo.batch_create_questions(questions)

    assert len(created) == 50
    total_opts = sum(len(q.options) for q in created)
    assert total_opts == 200  # 50 câu * 4 đáp án


# ─── List & Filter Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_questions_pagination(bank_repo):
    """Phân trang hoạt động đúng với limit và offset."""
    qs = [make_question(text=f"Câu {i}?") for i in range(10)]
    await bank_repo.batch_create_questions(qs)

    items, total = await bank_repo.list_questions(limit=5, offset=0)
    assert total == 10
    assert len(items) == 5

    items_p2, total_p2 = await bank_repo.list_questions(limit=5, offset=5)
    assert total_p2 == 10
    assert len(items_p2) == 5


@pytest.mark.asyncio
async def test_list_questions_filter_by_category(bank_repo):
    """Lọc theo category trả về đúng kết quả."""
    await bank_repo.batch_create_questions([
        make_question(text="Câu Lý 1?", category="Vật lý"),
        make_question(text="Câu Lý 2?", category="Vật lý"),
        make_question(text="Câu Hóa 1?", category="Hóa học"),
    ])

    items, total = await bank_repo.list_questions(category="Vật lý")
    assert total == 2
    assert all(q.category == "Vật lý" for q in items)


@pytest.mark.asyncio
async def test_list_questions_filter_by_difficulty(bank_repo):
    """Lọc theo difficulty trả về đúng kết quả."""
    await bank_repo.batch_create_questions([
        make_question(text="Dễ 1?", difficulty="easy"),
        make_question(text="Dễ 2?", difficulty="easy"),
        make_question(text="Khó 1?", difficulty="hard"),
    ])

    items, total = await bank_repo.list_questions(difficulty="easy")
    assert total == 2


@pytest.mark.asyncio
async def test_list_questions_search(bank_repo):
    """Tìm kiếm toàn văn trong question_text."""
    await bank_repo.batch_create_questions([
        make_question(text="Thủ đô Việt Nam là gì?"),
        make_question(text="Diện tích Hà Nội bao nhiêu?"),
        make_question(text="Câu hỏi không liên quan"),
    ])

    items, total = await bank_repo.list_questions(search="Hà Nội")
    assert total == 1
    assert "Hà Nội" in items[0].question_text


@pytest.mark.asyncio
async def test_list_questions_options_loaded_without_n_plus_1(bank_repo):
    """Tất cả options trong kết quả phân trang phải được load bằng 2 queries (selectinload)."""
    qs = [make_question(text=f"Q {i}?", n_options=3) for i in range(5)]
    await bank_repo.batch_create_questions(qs)

    items, _ = await bank_repo.list_questions(limit=5)
    # Nếu N+1 xảy ra, sẽ có 5+1=6 queries. Ta chỉ có thể verify kết quả đúng.
    assert all(len(q.options) == 3 for q in items)


# ─── Get Categories Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_categories_returns_unique_sorted(bank_repo):
    """Danh sách categories trả về duy nhất và sắp xếp."""
    await bank_repo.batch_create_questions([
        make_question(category="Toán"),
        make_question(category="Lý"),
        make_question(category="Toán"),  # trùng
        make_question(category="Hóa"),
    ])

    cats = await bank_repo.get_categories()
    assert sorted(cats) == cats  # đã sắp xếp
    assert len(cats) == len(set(cats))  # duy nhất
    assert "Toán" in cats
    assert "Lý" in cats


# ─── Get / Update / Delete Single Question ───────────────────────────────────


@pytest.mark.asyncio
async def test_get_question_by_id(bank_repo):
    """Lấy đúng câu hỏi theo ID kèm options."""
    [created] = await bank_repo.batch_create_questions([make_question(text="Câu đặc biệt?")])

    found = await bank_repo.get_question(created.id)
    assert found is not None
    assert found.question_text == "Câu đặc biệt?"
    assert len(found.options) == 4


@pytest.mark.asyncio
async def test_get_question_not_found(bank_repo):
    """Trả về None khi không tìm thấy câu hỏi."""
    result = await bank_repo.get_question(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_update_question(bank_repo):
    """Cập nhật câu hỏi trong ngân hàng."""
    [created] = await bank_repo.batch_create_questions([make_question(text="Câu gốc?")])

    updated = await bank_repo.update_question(
        created.id,
        BankQuestionUpdate(question_text="Câu đã sửa?", category="Sinh học"),
    )

    assert updated is not None
    assert updated.question_text == "Câu đã sửa?"
    assert updated.category == "Sinh học"
    # Options không thay đổi
    assert len(updated.options) == 4


@pytest.mark.asyncio
async def test_delete_question(bank_repo):
    """Xóa câu hỏi và cascade xóa options."""
    [created] = await bank_repo.batch_create_questions([make_question()])

    result = await bank_repo.delete_question(created.id)
    assert result is True

    # Xác nhận đã xóa
    found = await bank_repo.get_question(created.id)
    assert found is None


@pytest.mark.asyncio
async def test_delete_nonexistent_question(bank_repo):
    """Xóa câu hỏi không tồn tại trả về False."""
    result = await bank_repo.delete_question(uuid.uuid4())
    assert result is False
