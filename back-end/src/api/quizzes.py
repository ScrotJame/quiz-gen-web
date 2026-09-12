from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from src.api.deps import get_attempt_service, get_quiz_service
from src.models.schemas import (
    CamelModel,
    LeaderboardEntry,
    QuestionCreate,
    QuestionSchema,
    QuizCreate,
    QuizDetail,
    QuizSummary,
    QuizUpdate,
)
from src.services.attempt_service import AttemptService, AttemptServiceError
from src.services.quiz_service import QuizService, QuizServiceError

router = APIRouter(tags=["Quizzes"])


class PaginatedQuizListResponse(CamelModel):
    items: list[QuizSummary]
    total: int
    limit: int
    offset: int


@router.get("/quizzes", response_model=PaginatedQuizListResponse)
async def list_quizzes(
    service: Annotated[QuizService, Depends(get_quiz_service)],
    category: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaginatedQuizListResponse:
    items, total = await service.list_quizzes(
        category=category,
        search=search,
        limit=limit,
        offset=offset,
    )
    return PaginatedQuizListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/quizzes", response_model=QuizDetail, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    data: QuizCreate,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizDetail:
    try:
        return await service.create_quiz(data)
    except QuizServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/quizzes/{quiz_id}", response_model=QuizDetail)
async def get_quiz(
    quiz_id: uuid.UUID,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizDetail:
    try:
        return await service.get_quiz(quiz_id)
    except QuizServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/quizzes/{quiz_id}", response_model=QuizDetail)
async def update_quiz(
    quiz_id: uuid.UUID,
    data: QuizUpdate,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizDetail:
    try:
        return await service.update_quiz(quiz_id, data)
    except QuizServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/quizzes/{quiz_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_quiz(
    quiz_id: uuid.UUID,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> Response:
    try:
        await service.delete_quiz(quiz_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except QuizServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/quizzes/{quiz_id}/questions",
    response_model=QuestionSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_question_to_quiz(
    quiz_id: uuid.UUID,
    data: QuestionCreate,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuestionSchema:
    try:
        return await service.add_question(quiz_id, data)
    except QuizServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_question(
    question_id: uuid.UUID,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> Response:
    try:
        await service.delete_question(question_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except QuizServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/quizzes/{quiz_id}/leaderboard", response_model=list[LeaderboardEntry])
async def get_quiz_leaderboard(
    quiz_id: uuid.UUID,
    attempt_service: Annotated[AttemptService, Depends(get_attempt_service)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[LeaderboardEntry]:
    try:
        return await attempt_service.get_leaderboard(quiz_id, limit=limit)
    except AttemptServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
