import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.db.base import Base
from src.models.schemas import (
    QuizBase,
    QuizCreate,
    QuestionCreate,
    OptionCreate,
    Difficulty,
    QuestionType,
    StartAttemptRequest,
)
from src.models.tables import (
    QuizTable,
    QuestionTable,
    OptionTable,
    AttemptTable,
    AttemptAnswerTable,
)


def test_camel_model_serialization():
    req = StartAttemptRequest(quiz_id=uuid.uuid4(), participant_name="Alice")
    data = req.model_dump(by_alias=True)
    assert "quizId" in data
    assert "participantName" in data
    assert data["participantName"] == "Alice"


def test_quiz_create_camel_dump():
    quiz = QuizCreate(
        title="Python Quiz",
        time_limit_minutes=20,
        difficulty=Difficulty.EASY,
        questions=[
            QuestionCreate(
                question_text="What is Python?",
                question_type=QuestionType.SINGLE_CHOICE,
                options=[
                    OptionCreate(option_text="A language", is_correct=True),
                    OptionCreate(option_text="A snake only", is_correct=False),
                ],
            )
        ],
    )
    dumped = quiz.model_dump(by_alias=True)
    assert "timeLimitMinutes" in dumped
    assert dumped["timeLimitMinutes"] == 20
    assert dumped["questions"][0]["questionText"] == "What is Python?"


@pytest.mark.asyncio
async def test_orm_tables_creation():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        quiz = QuizTable(
            title="Async Quiz",
            difficulty=Difficulty.MEDIUM,
            time_limit_minutes=15,
        )
        session.add(quiz)
        await session.flush()

        question = QuestionTable(
            quiz_id=quiz.id,
            question_text="Sample Question",
            points=10,
        )
        session.add(question)
        await session.flush()

        option = OptionTable(
            question_id=question.id,
            option_text="Option 1",
            is_correct=True,
        )
        session.add(option)
        await session.commit()

        # Query back with selectinload
        stmt = (
            select(QuizTable)
            .where(QuizTable.id == quiz.id)
            .options(
                selectinload(QuizTable.questions).selectinload(QuestionTable.options)
            )
        )
        result = await session.execute(stmt)
        q_loaded = result.scalar_one_or_none()

        assert q_loaded is not None
        assert len(q_loaded.questions) == 1
        assert len(q_loaded.questions[0].options) == 1
        assert q_loaded.questions[0].options[0].option_text == "Option 1"

    await engine.dispose()
