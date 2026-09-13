from __future__ import annotations

import uuid

from src.core.exceptions import AppError, EntityNotFoundError
from src.models.schemas import (
    BankQuestionBatchCreate,
    BankQuestionCreate,
    BankQuestionSchema,
    BankQuestionUpdate,
)
from src.repositories.bank import SqlBankRepository


class BankServiceError(AppError):
    """Lỗi nghiệp vụ Ngân hàng câu hỏi."""

    error_code = "BANK_SERVICE_ERROR"
    status_code = 400


class BankQuestionNotFoundError(BankServiceError, EntityNotFoundError):
    error_code = "NOT_FOUND"
    status_code = 404


MAX_BATCH_SIZE = 100


class BankService:
    """Nghiệp vụ Ngân hàng câu hỏi.

    Validate dữ liệu đầu vào trước khi đẩy xuống repository.
    """

    def __init__(self, bank_repo: SqlBankRepository) -> None:
        self.repo = bank_repo

    async def batch_create(self, data: BankQuestionBatchCreate) -> list[BankQuestionSchema]:
        if not data.questions:
            raise BankServiceError("Danh sách câu hỏi không được để trống.")
        if len(data.questions) > MAX_BATCH_SIZE:
            raise BankServiceError(
                f"Số lượng câu hỏi mỗi lần lưu không được vượt quá {MAX_BATCH_SIZE}."
            )

        for q in data.questions:
            self._validate_question(q)

        return await self.repo.batch_create_questions(data.questions)

    async def list_questions(
        self,
        *,
        category: str | None = None,
        difficulty: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[BankQuestionSchema], int]:
        page = max(1, page)
        limit = min(100, max(1, limit))
        return await self.repo.list_questions(
            category=category,
            difficulty=difficulty,
            search=search,
            page=page,
            limit=limit,
        )

    async def get_categories(self) -> list[str]:
        return await self.repo.get_categories()

    async def get_question(self, question_id: uuid.UUID) -> BankQuestionSchema:
        q = await self.repo.get_question(question_id)
        if q is None:
            raise BankQuestionNotFoundError(f"Không tìm thấy câu hỏi với mã: {question_id}")
        return q

    async def update_question(
        self, question_id: uuid.UUID, data: BankQuestionUpdate
    ) -> BankQuestionSchema:
        updated = await self.repo.update_question(question_id, data)
        if updated is None:
            raise BankQuestionNotFoundError(f"Không tìm thấy câu hỏi với mã: {question_id}")
        return updated

    async def delete_question(self, question_id: uuid.UUID) -> bool:
        deleted = await self.repo.delete_question(question_id)
        if not deleted:
            raise BankQuestionNotFoundError(f"Không tìm thấy câu hỏi với mã: {question_id}")
        return True

    # ─── Private helpers ─────────────────────────────────────────────────────

    def _validate_question(self, q: BankQuestionCreate) -> None:
        """Đảm bảo mỗi câu hỏi có ít nhất 2 đáp án và 1 đáp án đúng."""
        if len(q.options) < 2:
            raise BankServiceError(
                f"Câu hỏi '{q.question_text[:40]}' phải có ít nhất 2 lựa chọn đáp án."
            )
        correct_count = sum(1 for o in q.options if o.is_correct)
        if correct_count == 0:
            raise BankServiceError(
                f"Câu hỏi '{q.question_text[:40]}' phải có ít nhất 1 đáp án đúng."
            )
