from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import get_attempt_service
from src.models.schemas import (
    AttemptResult,
    StartAttemptRequest,
    SubmitAttemptRequest,
)
from src.services.attempt_service import AttemptService, AttemptServiceError

router = APIRouter(tags=["Attempts"])


@router.post(
    "/attempts/start",
    response_model=AttemptResult,
    status_code=status.HTTP_201_CREATED,
)
async def start_attempt(
    data: StartAttemptRequest,
    service: Annotated[AttemptService, Depends(get_attempt_service)],
) -> AttemptResult:
    try:
        return await service.start_attempt(data.quiz_id, data.participant_name)
    except AttemptServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResult)
async def submit_attempt(
    attempt_id: uuid.UUID,
    data: SubmitAttemptRequest,
    service: Annotated[AttemptService, Depends(get_attempt_service)],
) -> AttemptResult:
    try:
        return await service.submit_attempt(attempt_id, data)
    except AttemptServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/attempts/{attempt_id}", response_model=AttemptResult)
async def get_attempt(
    attempt_id: uuid.UUID,
    service: Annotated[AttemptService, Depends(get_attempt_service)],
) -> AttemptResult:
    try:
        return await service.get_attempt(attempt_id)
    except AttemptServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
