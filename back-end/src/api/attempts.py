from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.deps import get_attempt_service
from src.models.schemas import (
    AttemptResult,
    StartAttemptRequest,
    SubmitAttemptRequest,
)
from src.services.attempt_service import AttemptService

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
    return await service.start_attempt(data.quiz_id, data.participant_name)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResult)
async def submit_attempt(
    attempt_id: uuid.UUID,
    data: SubmitAttemptRequest,
    service: Annotated[AttemptService, Depends(get_attempt_service)],
) -> AttemptResult:
    return await service.submit_attempt(attempt_id, data)


@router.get("/attempts/{attempt_id}", response_model=AttemptResult)
async def get_attempt(
    attempt_id: uuid.UUID,
    service: Annotated[AttemptService, Depends(get_attempt_service)],
) -> AttemptResult:
    return await service.get_attempt(attempt_id)
