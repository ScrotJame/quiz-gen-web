from __future__ import annotations

import uuid

from src.core.exceptions import AppError, EntityNotFoundError
from src.models.schemas import (
    DashboardStats,
    OptionSchema,
    QuestionCreate,
    QuestionSchema,
    QuestionType,
    QuizCreate,
    QuizDetail,
    QuizSummary,
    QuizUpdate,
)
from src.repositories.base import QuizRepository


class QuizServiceError(AppError):
    """Lỗi nghiệp vụ Quiz."""

    error_code = "QUIZ_SERVICE_ERROR"
    status_code = 400


class QuizNotFoundError(QuizServiceError, EntityNotFoundError):
    """Không tìm thấy đề thi hoặc câu hỏi."""

    error_code = "NOT_FOUND"
    status_code = 404


class QuizService:
    """Nghiệp vụ quản lý đề thi và câu hỏi.

    Thuần Python, nhận QuizRepository qua constructor injection theo chuẩn P-131.
    """

    def __init__(self, quiz_repo: QuizRepository) -> None:
        self.repo = quiz_repo

    async def list_quizzes(
        self,
        category: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[QuizSummary], int]:
        return await self.repo.list_quizzes(
            category=category,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def get_dashboard_stats(self) -> DashboardStats:
        return await self.repo.get_dashboard_stats()

    async def get_quiz(self, quiz_id: uuid.UUID, *, mask_answers: bool = True) -> QuizDetail:
        quiz = await self.repo.get_quiz(quiz_id)
        if not quiz:
            raise QuizNotFoundError(f"Không tìm thấy đề thi với mã: {quiz_id}")

        if not mask_answers:
            return quiz

        # Bảo mật: Ẩn is_correct và explanation khi lấy đề thi để chống gian lận qua F12 Network tab
        sanitized_questions = []
        for q in quiz.questions:
            sanitized_options = [
                OptionSchema(
                    id=opt.id,
                    question_id=opt.question_id,
                    option_text=opt.option_text,
                    order_num=opt.order_num,
                    is_correct=None,
                )
                for opt in q.options
            ]
            sanitized_q = q.model_copy(
                update={
                    "options": sanitized_options,
                    "explanation": None,
                }
            )
            sanitized_questions.append(sanitized_q)

        return quiz.model_copy(update={"questions": sanitized_questions})

    async def create_quiz(self, data: QuizCreate) -> QuizDetail:
        # Validate business rules
        if not data.title.strip():
            raise QuizServiceError("Tiêu đề đề thi không được để trống.")

        for q in data.questions:
            self._validate_question(q)

        return await self.repo.create_quiz(data)

    async def update_quiz(
        self, quiz_id: uuid.UUID, data: QuizUpdate
    ) -> QuizDetail:
        updated = await self.repo.update_quiz(quiz_id, data)
        if not updated:
            raise QuizNotFoundError(f"Không tìm thấy đề thi với mã: {quiz_id}")
        return updated

    async def delete_quiz(self, quiz_id: uuid.UUID) -> bool:
        deleted = await self.repo.delete_quiz(quiz_id)
        if not deleted:
            raise QuizNotFoundError(f"Không tìm thấy đề thi với mã: {quiz_id}")
        return True

    async def add_question(
        self, quiz_id: uuid.UUID, data: QuestionCreate
    ) -> QuestionSchema:
        # Kiểm tra quiz tồn tại
        await self.get_quiz(quiz_id)
        self._validate_question(data)
        q = await self.repo.add_question(quiz_id, data)
        if not q:
            raise QuizServiceError("Không thể thêm câu hỏi vào đề thi.")
        return q

    async def delete_question(self, question_id: uuid.UUID) -> bool:
        deleted = await self.repo.delete_question(question_id)
        if not deleted:
            raise QuizNotFoundError(f"Không tìm thấy câu hỏi với mã: {question_id}")
        return True

    def _validate_question(self, q: QuestionCreate) -> None:
        if len(q.options) < 2:
            raise QuizServiceError(
                f"Câu hỏi '{q.question_text[:30]}...' phải có ít nhất 2 lựa chọn đáp án."
            )
        correct_count = sum(1 for o in q.options if o.is_correct)
        if correct_count == 0:
            raise QuizServiceError(
                f"Câu hỏi '{q.question_text[:30]}...' phải có ít nhất 1 đáp án đúng."
            )
        if q.question_type == QuestionType.SINGLE_CHOICE and correct_count > 1:
            raise QuizServiceError(
                f"Câu hỏi chọn 1 đáp án '{q.question_text[:30]}...' chỉ được phép có 1 đáp án đúng."
            )
