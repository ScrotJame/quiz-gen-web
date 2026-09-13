from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, GUID, TimestampMixin, enum_column
from src.models.schemas import QuestionType

if TYPE_CHECKING:
    pass


class BankQuestionTable(Base, TimestampMixin):
    """Câu hỏi trong Ngân hàng câu hỏi — độc lập với đề thi."""

    __tablename__ = "bank_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        enum_column(QuestionType),
        default=QuestionType.SINGLE_CHOICE,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(128), nullable=False, default="Chung", index=True)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", index=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Ghi chú nguồn quét (tên đợt, tên file ảnh...)
    source_note: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Lazy="selectin" — load toàn bộ options cùng 1 truy vấn IN, chống N+1
    options: Mapped[list[BankOptionTable]] = relationship(
        "BankOptionTable",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="BankOptionTable.order_num",
        lazy="selectin",
    )

    __table_args__ = (
        # Compound index để filter category + difficulty cùng lúc hiệu quả
        Index("ix_bank_questions_category_difficulty", "category", "difficulty"),
    )


class BankOptionTable(Base, TimestampMixin):
    """Đáp án của câu hỏi trong Ngân hàng câu hỏi."""

    __tablename__ = "bank_options"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("bank_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order_num: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    question: Mapped[BankQuestionTable] = relationship(
        "BankQuestionTable",
        back_populates="options",
    )
