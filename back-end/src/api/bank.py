from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from src.models.schemas import (
    BankCategoriesResponse,
    BankMatrixGenerateRequest,
    BankMatrixGenerateResponse,
    BankQuestionBatchCreate,
    BankQuestionListResponse,
    BankQuestionSchema,
    BankQuestionUpdate,
)
from src.repositories.bank import SqlBankRepository
from src.services.bank_service import BankService

router = APIRouter(prefix="/bank", tags=["Question Bank"])


def get_bank_service() -> BankService:
    return BankService(SqlBankRepository())


BankServiceDep = Annotated[BankService, Depends(get_bank_service)]


@router.post(
    "/matrix-generate",
    response_model=BankMatrixGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Sinh danh sách câu hỏi theo ma trận tiêu chí",
)
async def matrix_generate_questions(
    data: BankMatrixGenerateRequest,
    service: BankServiceDep,
) -> BankMatrixGenerateResponse:
    """Bốc ngẫu nhiên câu hỏi từ ngân hàng theo độ khó và danh mục."""
    return await service.sample_by_matrix(data)


@router.post(
    "/questions/batch",
    response_model=list[BankQuestionSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Lưu hàng loạt câu hỏi vào Ngân hàng câu hỏi",
)
async def batch_create_bank_questions(
    data: BankQuestionBatchCreate,
    service: BankServiceDep,
) -> list[BankQuestionSchema]:
    """Batch insert tối đa 100 câu hỏi trong 1 transaction duy nhất (chống N+1)."""
    return await service.batch_create(data)


@router.get(
    "/questions",
    response_model=BankQuestionListResponse,
    summary="Danh sách câu hỏi trong Ngân hàng",
)
async def list_bank_questions(
    service: BankServiceDep,
    category: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> BankQuestionListResponse:
    items, total = await service.list_questions(
        category=category,
        difficulty=difficulty,
        search=search,
        page=page,
        limit=limit,
    )
    return BankQuestionListResponse(items=items, total=total, page=page, limit=limit)


@router.get(
    "/categories",
    response_model=BankCategoriesResponse,
    summary="Danh sách danh mục có trong Ngân hàng",
)
async def get_bank_categories(service: BankServiceDep) -> BankCategoriesResponse:
    cats = await service.get_categories()
    return BankCategoriesResponse(categories=cats)


@router.get(
    "/questions/{question_id}",
    response_model=BankQuestionSchema,
    summary="Chi tiết 1 câu hỏi trong Ngân hàng",
)
async def get_bank_question(
    question_id: uuid.UUID,
    service: BankServiceDep,
) -> BankQuestionSchema:
    return await service.get_question(question_id)


@router.put(
    "/questions/{question_id}",
    response_model=BankQuestionSchema,
    summary="Cập nhật câu hỏi trong Ngân hàng",
)
async def update_bank_question(
    question_id: uuid.UUID,
    data: BankQuestionUpdate,
    service: BankServiceDep,
) -> BankQuestionSchema:
    return await service.update_question(question_id, data)


@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Xóa câu hỏi khỏi Ngân hàng",
)
async def delete_bank_question(
    question_id: uuid.UUID,
    service: BankServiceDep,
) -> Response:
    await service.delete_question(question_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
