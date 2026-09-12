from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, GUID, TimestampMixin, enum_column
from src.models.schemas import QuestionType

if TYPE_CHECKING:
    from src.models.tables.quiz import QuizTable


class QuestionTable(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        enum_column(QuestionType),
        default=QuestionType.SINGLE_CHOICE,
        nullable=False,
    )
    points: Mapped[int] = mapped_column(Integer, default=10)
    order_num: Mapped[int] = mapped_column(Integer, default=0)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    quiz: Mapped[QuizTable] = relationship(
        "QuizTable",
        back_populates="questions",
    )
    options: Mapped[list[OptionTable]] = relationship(
        "OptionTable",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="OptionTable.order_num",
        lazy="selectin",
    )


class OptionTable(Base, TimestampMixin):
    __tablename__ = "options"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    order_num: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    question: Mapped[QuestionTable] = relationship(
        "QuestionTable",
        back_populates="options",
    )
