from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.models.schemas import (
    AttemptAnswerDetail,
    AttemptResult,
    LeaderboardEntry,
    QuestionCreate,
    QuestionSchema,
    QuizCreate,
    QuizDetail,
    QuizSummary,
    QuizUpdate,
)


class QuizRepository(ABC):
    """Hợp đồng truy cập dữ liệu Quiz và Question.

    Là ranh giới duy nhất chạm tới storage (SQL hoặc Memory).
    """

    @abstractmethod
    async def list_quizzes(
        self,
        *,
        category: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[QuizSummary], int]:
        """Lấy danh sách đề thi kèm tổng số câu hỏi."""
        ...

    @abstractmethod
    async def get_quiz(self, quiz_id: uuid.UUID) -> QuizDetail | None:
        """Lấy chi tiết đề thi kèm câu hỏi và đáp án."""
        ...

    @abstractmethod
    async def create_quiz(self, data: QuizCreate) -> QuizDetail:
        """Tạo mới đề thi."""
        ...

    @abstractmethod
    async def update_quiz(
        self, quiz_id: uuid.UUID, data: QuizUpdate
    ) -> QuizDetail | None:
        """Cập nhật thông tin đề thi."""
        ...

    @abstractmethod
    async def delete_quiz(self, quiz_id: uuid.UUID) -> bool:
        """Xóa đề thi."""
        ...

    @abstractmethod
    async def add_question(
        self, quiz_id: uuid.UUID, data: QuestionCreate
    ) -> QuestionSchema | None:
        """Thêm câu hỏi vào đề thi."""
        ...

    @abstractmethod
    async def delete_question(self, question_id: uuid.UUID) -> bool:
        """Xóa câu hỏi khỏi đề thi."""
        ...


class AttemptRepository(ABC):
    """Hợp đồng truy cập dữ liệu lượt làm bài và chấm điểm."""

    @abstractmethod
    async def create_attempt(
        self, quiz_id: uuid.UUID, participant_name: str
    ) -> AttemptResult:
        """Khởi tạo lượt làm bài mới."""
        ...

    @abstractmethod
    async def get_attempt(self, attempt_id: uuid.UUID) -> AttemptResult | None:
        """Lấy thông tin lượt làm bài."""
        ...

    @abstractmethod
    async def submit_attempt(
        self,
        attempt_id: uuid.UUID,
        answers: list[AttemptAnswerDetail],
        score: int,
        max_score: int,
        percentage: float,
    ) -> AttemptResult | None:
        """Lưu kết quả nộp bài và trạng thái hoàn thành."""
        ...

    @abstractmethod
    async def get_leaderboard(
        self, quiz_id: uuid.UUID, limit: int = 20
    ) -> list[LeaderboardEntry]:
        """Lấy bảng xếp hạng điểm của đề thi."""
        ...
