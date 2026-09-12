import uuid
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.db.base import Base
from src.models.schemas import (
    AttemptAnswerDetail,
    Difficulty,
    OptionCreate,
    QuestionCreate,
    QuestionType,
    QuizCreate,
)
from src.repositories.memory import InMemoryAttemptRepository, InMemoryQuizRepository
from src.repositories.sql import SqlAttemptRepository, SqlQuizRepository


@pytest.fixture
def sample_quiz_create() -> QuizCreate:
    return QuizCreate(
        title="Sample Repo Quiz",
        description="Testing repo layer",
        category="General",
        difficulty=Difficulty.MEDIUM,
        time_limit_minutes=10,
        questions=[
            QuestionCreate(
                question_text="2 + 2 = ?",
                question_type=QuestionType.SINGLE_CHOICE,
                points=10,
                options=[
                    OptionCreate(option_text="3", is_correct=False),
                    OptionCreate(option_text="4", is_correct=True),
                ],
            )
        ],
    )


@pytest.mark.asyncio
async def test_in_memory_quiz_repo(sample_quiz_create: QuizCreate):
    repo = InMemoryQuizRepository()
    created = await repo.create_quiz(sample_quiz_create)
    assert created.id is not None
    assert len(created.questions) == 1
    assert len(created.questions[0].options) == 2

    # List
    quizzes, total = await repo.list_quizzes()
    assert total == 1
    assert quizzes[0].title == "Sample Repo Quiz"

    # Get
    detail = await repo.get_quiz(created.id)
    assert detail is not None
    assert detail.title == "Sample Repo Quiz"


@pytest.mark.asyncio
async def test_in_memory_attempt_repo():
    quiz_id = uuid.uuid4()
    q_id = uuid.uuid4()
    opt_id = uuid.uuid4()
    repo = InMemoryAttemptRepository()

    att = await repo.create_attempt(quiz_id, "Bob")
    assert att.participant_name == "Bob"
    assert att.score == 0

    submitted = await repo.submit_attempt(
        att.id,
        answers=[
            AttemptAnswerDetail(
                id=uuid.uuid4(),
                question_id=q_id,
                selected_option_ids=[opt_id],
                is_correct=True,
                earned_points=10,
            )
        ],
        score=10,
        max_score=10,
        percentage=100.0,
    )
    assert submitted is not None
    assert submitted.score == 10
    assert submitted.percentage == 100.0

    lb = await repo.get_leaderboard(quiz_id)
    assert len(lb) == 1
    assert lb[0].participant_name == "Bob"
    assert lb[0].score == 10


@pytest.mark.asyncio
async def test_sql_repositories(sample_quiz_create: QuizCreate):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sm = async_sessionmaker(bind=engine, expire_on_commit=False)
    quiz_repo = SqlQuizRepository(session_factory=sm)
    attempt_repo = SqlAttemptRepository(session_factory=sm)

    # 1. Create Quiz
    created_quiz = await quiz_repo.create_quiz(sample_quiz_create)
    assert created_quiz.id is not None
    assert len(created_quiz.questions) == 1
    q = created_quiz.questions[0]
    assert len(q.options) == 2

    # 2. List Quizzes
    quizzes, total = await quiz_repo.list_quizzes()
    assert total == 1
    assert quizzes[0].title == "Sample Repo Quiz"

    # 3. Create Attempt
    attempt = await attempt_repo.create_attempt(created_quiz.id, "Alice")
    assert attempt.participant_name == "Alice"

    # 4. Submit Attempt
    correct_opt = [o for o in q.options if o.is_correct][0]
    submitted = await attempt_repo.submit_attempt(
        attempt.id,
        answers=[
            AttemptAnswerDetail(
                id=uuid.uuid4(),
                question_id=q.id,
                selected_option_ids=[correct_opt.id],
                is_correct=True,
                earned_points=10,
            )
        ],
        score=10,
        max_score=10,
        percentage=100.0,
    )
    assert submitted is not None
    assert submitted.score == 10

    # 5. Leaderboard
    lb = await attempt_repo.get_leaderboard(created_quiz.id)
    assert len(lb) == 1
    assert lb[0].participant_name == "Alice"
    assert lb[0].score == 10

    await engine.dispose()
