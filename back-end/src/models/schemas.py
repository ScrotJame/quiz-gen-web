from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model tự động serialize camelCase cho frontend Next.js."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------------------------------------------------------------- enums


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionType(StrEnum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"


class AttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# ---------------------------------------------------------------- options


class OptionBase(CamelModel):
    option_text: str
    is_correct: bool = False
    order_num: int = 0


class OptionCreate(OptionBase):
    pass


class OptionSchema(OptionBase):
    id: uuid.UUID
    question_id: uuid.UUID


# ---------------------------------------------------------------- questions


class QuestionBase(CamelModel):
    question_text: str
    question_type: QuestionType = QuestionType.SINGLE_CHOICE
    points: int = 10
    order_num: int = 0
    explanation: str | None = None


class QuestionCreate(QuestionBase):
    options: list[OptionCreate] = Field(default_factory=list)


class QuestionSchema(QuestionBase):
    id: uuid.UUID
    quiz_id: uuid.UUID
    options: list[OptionSchema] = Field(default_factory=list)


# ---------------------------------------------------------------- quizzes


class QuizBase(CamelModel):
    title: str
    description: str | None = None
    category: str = "Chung"
    difficulty: Difficulty = Difficulty.MEDIUM
    time_limit_minutes: int = 15
    author_name: str = "Nội bộ"
    is_published: bool = True


class QuizCreate(QuizBase):
    questions: list[QuestionCreate] = Field(default_factory=list)


class QuizUpdate(CamelModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    difficulty: Difficulty | None = None
    time_limit_minutes: int | None = None
    author_name: str | None = None
    is_published: bool | None = None


class QuizSummary(QuizBase):
    id: uuid.UUID
    total_questions: int = 0
    created_at: datetime
    updated_at: datetime


class QuizDetail(QuizBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    questions: list[QuestionSchema] = Field(default_factory=list)


class DashboardStats(CamelModel):
    total_quizzes: int = 0
    average_score: float = 0.0
    total_questions_completed: int = 0
    total_attempts: int = 0


# ---------------------------------------------------------------- attempts


class StartAttemptRequest(CamelModel):
    quiz_id: uuid.UUID
    participant_name: str = "Thí sinh"


class AnswerSubmission(CamelModel):
    question_id: uuid.UUID
    selected_option_ids: list[uuid.UUID] = Field(default_factory=list)


class SubmitAttemptRequest(CamelModel):
    answers: list[AnswerSubmission] = Field(default_factory=list)


class AttemptAnswerDetail(CamelModel):
    id: uuid.UUID
    question_id: uuid.UUID
    selected_option_ids: list[uuid.UUID]
    is_correct: bool
    earned_points: int


class AttemptResult(CamelModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    participant_name: str
    score: int
    max_score: int
    percentage: float
    status: AttemptStatus
    started_at: datetime
    completed_at: datetime | None = None
    answers: list[AttemptAnswerDetail] = Field(default_factory=list)


class LeaderboardEntry(CamelModel):
    id: uuid.UUID
    participant_name: str
    score: int
    max_score: int
    percentage: float
    completed_at: datetime
    duration_seconds: int = 0


# ---------------------------------------------------------------- AI generator


class AIGenerateRequest(CamelModel):
    topic: str | None = None
    content: str | None = None
    num_questions: int = Field(default=5, ge=1, le=30)
    difficulty: Difficulty = Difficulty.MEDIUM
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    save_immediately: bool = False
    author_name: str = "Mistral AI"


class GeneratedQuizResponse(CamelModel):
    title: str
    description: str
    category: str = "AI Generated"
    difficulty: Difficulty
    questions: list[QuestionCreate]
    saved_quiz_id: uuid.UUID | None = None


# --- OCR Studio


class OcrPageResponse(CamelModel):
    text: str
    line_count: int = 0
    average_confidence: float = 0.0


class CleanTextRequest(CamelModel):
    raw_text: str
    target_language: str = "vi"


class CleanTextResponse(CamelModel):
    cleaned_text: str
