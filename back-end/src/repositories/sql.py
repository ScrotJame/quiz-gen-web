from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from src.db.session import get_sessionmaker
from src.models.schemas import (
    AttemptAnswerDetail,
    AttemptResult,
    AttemptStatus,
    LeaderboardEntry,
    OptionSchema,
    QuestionCreate,
    QuestionSchema,
    QuizCreate,
    QuizDetail,
    QuizSummary,
    QuizUpdate,
)
from src.models.tables import (
    AttemptAnswerTable,
    AttemptTable,
    OptionTable,
    QuestionTable,
    QuizTable,
)
from src.repositories.base import AttemptRepository, QuizRepository


class SqlQuizRepository(QuizRepository):
    """SQLAlchemy Async implementation cho QuizRepository."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.session_factory = session_factory or get_sessionmaker()

    async def list_quizzes(
        self,
        *,
        category: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[QuizSummary], int]:
        async with self.session_factory() as session:
            query = select(QuizTable).where(QuizTable.is_published.is_(True))
            if category:
                query = query.where(QuizTable.category == category)
            if search:
                term = f"%{search}%"
                query = query.where(
                    (QuizTable.title.ilike(term)) | (QuizTable.description.ilike(term))
                )

            # Count total
            count_stmt = select(func.count()).select_from(query.subquery())
            total = (await session.execute(count_stmt)).scalar() or 0

            # Fetch paginated with question count
            stmt = (
                query.options(selectinload(QuizTable.questions))
                .order_by(QuizTable.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            quizzes = result.scalars().all()

            summaries = [
                QuizSummary(
                    id=q.id,
                    title=q.title,
                    description=q.description,
                    category=q.category,
                    difficulty=q.difficulty,
                    time_limit_minutes=q.time_limit_minutes,
                    author_name=q.author_name,
                    is_published=q.is_published,
                    total_questions=len(q.questions),
                    created_at=q.created_at,
                    updated_at=q.updated_at,
                )
                for q in quizzes
            ]
            return summaries, total

    async def get_quiz(self, quiz_id: uuid.UUID) -> QuizDetail | None:
        async with self.session_factory() as session:
            stmt = (
                select(QuizTable)
                .where(QuizTable.id == quiz_id)
                .options(
                    selectinload(QuizTable.questions).selectinload(QuestionTable.options)
                )
            )
            result = await session.execute(stmt)
            quiz = result.scalar_one_or_none()
            if not quiz:
                return None

            questions_dto = [
                QuestionSchema(
                    id=q.id,
                    quiz_id=q.quiz_id,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    points=q.points,
                    order_num=q.order_num,
                    explanation=q.explanation,
                    options=[
                        OptionSchema(
                            id=opt.id,
                            question_id=opt.question_id,
                            option_text=opt.option_text,
                            is_correct=opt.is_correct,
                            order_num=opt.order_num,
                        )
                        for opt in q.options
                    ],
                )
                for q in quiz.questions
            ]

            return QuizDetail(
                id=quiz.id,
                title=quiz.title,
                description=quiz.description,
                category=quiz.category,
                difficulty=quiz.difficulty,
                time_limit_minutes=quiz.time_limit_minutes,
                author_name=quiz.author_name,
                is_published=quiz.is_published,
                created_at=quiz.created_at,
                updated_at=quiz.updated_at,
                questions=questions_dto,
            )

    async def create_quiz(self, data: QuizCreate) -> QuizDetail:
        async with self.session_factory() as session:
            quiz = QuizTable(
                title=data.title,
                description=data.description,
                category=data.category,
                difficulty=data.difficulty,
                time_limit_minutes=data.time_limit_minutes,
                author_name=data.author_name,
                is_published=data.is_published,
            )
            session.add(quiz)
            await session.flush()

            for q_idx, q_in in enumerate(data.questions):
                question = QuestionTable(
                    quiz_id=quiz.id,
                    question_text=q_in.question_text,
                    question_type=q_in.question_type,
                    points=q_in.points,
                    order_num=q_in.order_num or q_idx,
                    explanation=q_in.explanation,
                )
                session.add(question)
                await session.flush()

                for o_idx, opt_in in enumerate(q_in.options):
                    option = OptionTable(
                        question_id=question.id,
                        option_text=opt_in.option_text,
                        is_correct=opt_in.is_correct,
                        order_num=opt_in.order_num or o_idx,
                    )
                    session.add(option)

            await session.commit()
            return await self.get_quiz(quiz.id)  # type: ignore[return-value]

    async def update_quiz(
        self, quiz_id: uuid.UUID, data: QuizUpdate
    ) -> QuizDetail | None:
        async with self.session_factory() as session:
            stmt = select(QuizTable).where(QuizTable.id == quiz_id)
            quiz = (await session.execute(stmt)).scalar_one_or_none()
            if not quiz:
                return None

            dump = data.model_dump(exclude_unset=True)
            for k, v in dump.items():
                setattr(quiz, k, v)
            quiz.updated_at = datetime.now(timezone.utc)
            await session.commit()

            return await self.get_quiz(quiz_id)

    async def delete_quiz(self, quiz_id: uuid.UUID) -> bool:
        async with self.session_factory() as session:
            stmt = select(QuizTable).where(QuizTable.id == quiz_id)
            quiz = (await session.execute(stmt)).scalar_one_or_none()
            if not quiz:
                return False
            await session.delete(quiz)
            await session.commit()
            return True

    async def add_question(
        self, quiz_id: uuid.UUID, data: QuestionCreate
    ) -> QuestionSchema | None:
        async with self.session_factory() as session:
            quiz = (await session.execute(select(QuizTable).where(QuizTable.id == quiz_id))).scalar_one_or_none()
            if not quiz:
                return None

            question = QuestionTable(
                quiz_id=quiz_id,
                question_text=data.question_text,
                question_type=data.question_type,
                points=data.points,
                order_num=data.order_num,
                explanation=data.explanation,
            )
            session.add(question)
            await session.flush()

            opts_dto: list[OptionSchema] = []
            for idx, opt_in in enumerate(data.options):
                option = OptionTable(
                    question_id=question.id,
                    option_text=opt_in.option_text,
                    is_correct=opt_in.is_correct,
                    order_num=opt_in.order_num or idx,
                )
                session.add(option)
                await session.flush()
                opts_dto.append(
                    OptionSchema(
                        id=option.id,
                        question_id=question.id,
                        option_text=option.option_text,
                        is_correct=option.is_correct,
                        order_num=option.order_num,
                    )
                )

            await session.commit()
            return QuestionSchema(
                id=question.id,
                quiz_id=quiz_id,
                question_text=question.question_text,
                question_type=question.question_type,
                points=question.points,
                order_num=question.order_num,
                explanation=question.explanation,
                options=opts_dto,
            )

    async def delete_question(self, question_id: uuid.UUID) -> bool:
        async with self.session_factory() as session:
            stmt = select(QuestionTable).where(QuestionTable.id == question_id)
            q = (await session.execute(stmt)).scalar_one_or_none()
            if not q:
                return False
            await session.delete(q)
            await session.commit()
            return True


class SqlAttemptRepository(AttemptRepository):
    """SQLAlchemy Async implementation cho AttemptRepository."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.session_factory = session_factory or get_sessionmaker()

    async def create_attempt(
        self, quiz_id: uuid.UUID, participant_name: str
    ) -> AttemptResult:
        async with self.session_factory() as session:
            attempt = AttemptTable(
                quiz_id=quiz_id,
                participant_name=participant_name,
                score=0,
                max_score=0,
                percentage=0.0,
                status=AttemptStatus.IN_PROGRESS,
            )
            session.add(attempt)
            await session.commit()

            return AttemptResult(
                id=attempt.id,
                quiz_id=attempt.quiz_id,
                participant_name=attempt.participant_name,
                score=attempt.score,
                max_score=attempt.max_score,
                percentage=attempt.percentage,
                status=attempt.status,
                started_at=attempt.started_at,
                completed_at=attempt.completed_at,
                answers=[],
            )

    async def get_attempt(self, attempt_id: uuid.UUID) -> AttemptResult | None:
        async with self.session_factory() as session:
            stmt = (
                select(AttemptTable)
                .where(AttemptTable.id == attempt_id)
                .options(selectinload(AttemptTable.answers))
            )
            result = await session.execute(stmt)
            attempt = result.scalar_one_or_none()
            if not attempt:
                return None

            answers_dto = [
                AttemptAnswerDetail(
                    id=ans.id,
                    question_id=ans.question_id,
                    selected_option_ids=ans.selected_option_ids,
                    is_correct=ans.is_correct,
                    earned_points=ans.earned_points,
                )
                for ans in attempt.answers
            ]

            return AttemptResult(
                id=attempt.id,
                quiz_id=attempt.quiz_id,
                participant_name=attempt.participant_name,
                score=attempt.score,
                max_score=attempt.max_score,
                percentage=attempt.percentage,
                status=attempt.status,
                started_at=attempt.started_at,
                completed_at=attempt.completed_at,
                answers=answers_dto,
            )

    async def submit_attempt(
        self,
        attempt_id: uuid.UUID,
        answers: list[AttemptAnswerDetail],
        score: int,
        max_score: int,
        percentage: float,
    ) -> AttemptResult | None:
        async with self.session_factory() as session:
            stmt = select(AttemptTable).where(AttemptTable.id == attempt_id)
            attempt = (await session.execute(stmt)).scalar_one_or_none()
            if not attempt:
                return None

            attempt.score = score
            attempt.max_score = max_score
            attempt.percentage = percentage
            attempt.status = AttemptStatus.COMPLETED
            attempt.completed_at = datetime.now(timezone.utc)

            # Insert answers
            for ans in answers:
                ans_record = AttemptAnswerTable(
                    attempt_id=attempt.id,
                    question_id=ans.question_id,
                    is_correct=ans.is_correct,
                    earned_points=ans.earned_points,
                )
                ans_record.selected_option_ids = ans.selected_option_ids
                session.add(ans_record)

            await session.commit()
            return await self.get_attempt(attempt_id)

    async def get_leaderboard(
        self, quiz_id: uuid.UUID, limit: int = 20
    ) -> list[LeaderboardEntry]:
        async with self.session_factory() as session:
            stmt = (
                select(AttemptTable)
                .where(
                    AttemptTable.quiz_id == quiz_id,
                    AttemptTable.status == AttemptStatus.COMPLETED,
                    AttemptTable.completed_at.is_not(None),
                )
                .order_by(AttemptTable.score.desc(), AttemptTable.completed_at.asc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            attempts = result.scalars().all()

            entries: list[LeaderboardEntry] = []
            for att in attempts:
                duration = 0
                if att.completed_at and att.started_at:
                    duration = int((att.completed_at - att.started_at).total_seconds())
                entries.append(
                    LeaderboardEntry(
                        id=att.id,
                        participant_name=att.participant_name,
                        score=att.score,
                        max_score=att.max_score,
                        percentage=att.percentage,
                        completed_at=att.completed_at,  # type: ignore[arg-type]
                        duration_seconds=duration,
                    )
                )
            return entries
