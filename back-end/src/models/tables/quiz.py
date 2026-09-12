from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, GUID, TimestampMixin, enum_column
from src.models.schemas import Difficulty

if TYPE_CHECKING:
    from src.models.tables.attempt import AttemptTable
    from src.models.tables.question import QuestionTable


class QuizTable(Base, TimestampMixin):
    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), default="Chung", index=True)
    difficulty: Mapped[Difficulty] = mapped_column(
        enum_column(Difficulty),
        default=Difficulty.MEDIUM,
        nullable=False,
    )
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=15)
    author_name: Mapped[str] = mapped_column(String(100), default="Nội bộ")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    questions: Mapped[list[QuestionTable]] = relationship(
        "QuestionTable",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="QuestionTable.order_num",
        lazy="selectin",
    )
    attempts: Mapped[list[AttemptTable]] = relationship(
        "AttemptTable",
        back_populates="quiz",
        cascade="all, delete-orphan",
    )
