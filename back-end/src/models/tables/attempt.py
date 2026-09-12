from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, GUID, TimestampMixin, enum_column
from src.models.schemas import AttemptStatus

if TYPE_CHECKING:
    from src.models.tables.quiz import QuizTable


class AttemptTable(Base, TimestampMixin):
    __tablename__ = "attempts"

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
    participant_name: Mapped[str] = mapped_column(String(100), default="Thí sinh")
    score: Mapped[int] = mapped_column(Integer, default=0)
    max_score: Mapped[int] = mapped_column(Integer, default=0)
    percentage: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[AttemptStatus] = mapped_column(
        enum_column(AttemptStatus),
        default=AttemptStatus.IN_PROGRESS,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    quiz: Mapped[QuizTable] = relationship(
        "QuizTable",
        back_populates="attempts",
    )
    answers: Mapped[list[AttemptAnswerTable]] = relationship(
        "AttemptAnswerTable",
        back_populates="attempt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AttemptAnswerTable(Base, TimestampMixin):
    __tablename__ = "attempt_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Lưu danh sách UUID dạng JSON string để tương thích mọi database
    selected_option_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    earned_points: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    attempt: Mapped[AttemptTable] = relationship(
        "AttemptTable",
        back_populates="answers",
    )

    @property
    def selected_option_ids(self) -> list[uuid.UUID]:
        try:
            raw = json.loads(self.selected_option_ids_json)
            return [uuid.UUID(x) for x in raw]
        except Exception:
            return []

    @selected_option_ids.setter
    def selected_option_ids(self, ids: list[uuid.UUID]) -> None:
        self.selected_option_ids_json = json.dumps([str(x) for x in ids])
