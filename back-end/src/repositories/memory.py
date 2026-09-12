from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone

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
from src.repositories.base import AttemptRepository, QuizRepository


class InMemoryQuizRepository(QuizRepository):
    """In-memory test double cho QuizRepository."""

    def __init__(self) -> None:
        self.quizzes: dict[uuid.UUID, QuizDetail] = {}

    async def list_quizzes(
        self,
        *,
        category: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[QuizSummary], int]:
        items = list(self.quizzes.values())
        if category:
            items = [q for q in items if q.category == category]
        if search:
            s = search.lower()
            items = [q for q in items if s in q.title.lower() or (q.description and s in q.description.lower())]

        total = len(items)
        sliced = items[offset : offset + limit]
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
            for q in sliced
        ]
        return summaries, total

    async def get_quiz(self, quiz_id: uuid.UUID) -> QuizDetail | None:
        quiz = self.quizzes.get(quiz_id)
        return copy.deepcopy(quiz) if quiz else None

    async def create_quiz(self, data: QuizCreate) -> QuizDetail:
        now = datetime.now(timezone.utc)
        quiz_id = uuid.uuid4()
        questions_schema: list[QuestionSchema] = []

        for q_idx, q in enumerate(data.questions):
            q_id = uuid.uuid4()
            options_schema: list[OptionSchema] = []
            for o_idx, opt in enumerate(q.options):
                opt_id = uuid.uuid4()
                options_schema.append(
                    OptionSchema(
                        id=opt_id,
                        question_id=q_id,
                        option_text=opt.option_text,
                        is_correct=opt.is_correct,
                        order_num=opt.order_num or o_idx,
                    )
                )
            questions_schema.append(
                QuestionSchema(
                    id=q_id,
                    quiz_id=quiz_id,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    points=q.points,
                    order_num=q.order_num or q_idx,
                    explanation=q.explanation,
                    options=options_schema,
                )
            )

        quiz = QuizDetail(
            id=quiz_id,
            title=data.title,
            description=data.description,
            category=data.category,
            difficulty=data.difficulty,
            time_limit_minutes=data.time_limit_minutes,
            author_name=data.author_name,
            is_published=data.is_published,
            created_at=now,
            updated_at=now,
            questions=questions_schema,
        )
        self.quizzes[quiz_id] = quiz
        return copy.deepcopy(quiz)

    async def update_quiz(
        self, quiz_id: uuid.UUID, data: QuizUpdate
    ) -> QuizDetail | None:
        quiz = self.quizzes.get(quiz_id)
        if not quiz:
            return None
        dump = data.model_dump(exclude_unset=True)
        for k, v in dump.items():
            setattr(quiz, k, v)
        quiz.updated_at = datetime.now(timezone.utc)
        return copy.deepcopy(quiz)

    async def delete_quiz(self, quiz_id: uuid.UUID) -> bool:
        if quiz_id in self.quizzes:
            del self.quizzes[quiz_id]
            return True
        return False

    async def add_question(
        self, quiz_id: uuid.UUID, data: QuestionCreate
    ) -> QuestionSchema | None:
        quiz = self.quizzes.get(quiz_id)
        if not quiz:
            return None
        q_id = uuid.uuid4()
        opts: list[OptionSchema] = []
        for idx, opt in enumerate(data.options):
            opts.append(
                OptionSchema(
                    id=uuid.uuid4(),
                    question_id=q_id,
                    option_text=opt.option_text,
                    is_correct=opt.is_correct,
                    order_num=opt.order_num or idx,
                )
            )
        q_schema = QuestionSchema(
            id=q_id,
            quiz_id=quiz_id,
            question_text=data.question_text,
            question_type=data.question_type,
            points=data.points,
            order_num=data.order_num or len(quiz.questions),
            explanation=data.explanation,
            options=opts,
        )
        quiz.questions.append(q_schema)
        quiz.updated_at = datetime.now(timezone.utc)
        return copy.deepcopy(q_schema)

    async def delete_question(self, question_id: uuid.UUID) -> bool:
        for quiz in self.quizzes.values():
            for idx, q in enumerate(quiz.questions):
                if q.id == question_id:
                    quiz.questions.pop(idx)
                    quiz.updated_at = datetime.now(timezone.utc)
                    return True
        return False


class InMemoryAttemptRepository(AttemptRepository):
    """In-memory test double cho AttemptRepository."""

    def __init__(self) -> None:
        self.attempts: dict[uuid.UUID, AttemptResult] = {}

    async def create_attempt(
        self, quiz_id: uuid.UUID, participant_name: str
    ) -> AttemptResult:
        attempt_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        attempt = AttemptResult(
            id=attempt_id,
            quiz_id=quiz_id,
            participant_name=participant_name,
            score=0,
            max_score=0,
            percentage=0.0,
            status=AttemptStatus.IN_PROGRESS,
            started_at=now,
            completed_at=None,
            answers=[],
        )
        self.attempts[attempt_id] = attempt
        return copy.deepcopy(attempt)

    async def get_attempt(self, attempt_id: uuid.UUID) -> AttemptResult | None:
        attempt = self.attempts.get(attempt_id)
        return copy.deepcopy(attempt) if attempt else None

    async def submit_attempt(
        self,
        attempt_id: uuid.UUID,
        answers: list[AttemptAnswerDetail],
        score: int,
        max_score: int,
        percentage: float,
    ) -> AttemptResult | None:
        attempt = self.attempts.get(attempt_id)
        if not attempt:
            return None
        attempt.answers = copy.deepcopy(answers)
        attempt.score = score
        attempt.max_score = max_score
        attempt.percentage = percentage
        attempt.status = AttemptStatus.COMPLETED
        attempt.completed_at = datetime.now(timezone.utc)
        return copy.deepcopy(attempt)

    async def get_leaderboard(
        self, quiz_id: uuid.UUID, limit: int = 20
    ) -> list[LeaderboardEntry]:
        completed = [
            att
            for att in self.attempts.values()
            if att.quiz_id == quiz_id
            and att.status == AttemptStatus.COMPLETED
            and att.completed_at is not None
        ]
        completed.sort(key=lambda a: (-a.score, a.completed_at))
        entries: list[LeaderboardEntry] = []
        for att in completed[:limit]:
            duration = int((att.completed_at - att.started_at).total_seconds())
            entries.append(
                LeaderboardEntry(
                    id=att.id,
                    participant_name=att.participant_name,
                    score=att.score,
                    max_score=att.max_score,
                    percentage=att.percentage,
                    completed_at=att.completed_at,
                    duration_seconds=duration,
                )
            )
        return entries
