from __future__ import annotations

from fastapi import APIRouter

from src.api.ai import router as ai_router
from src.api.attempts import router as attempts_router
from src.api.health import router as health_router
from src.api.quizzes import router as quizzes_router

router = APIRouter(prefix="/api/v1")

# Đăng ký các controller domain
router.include_router(health_router)
router.include_router(quizzes_router)
router.include_router(attempts_router)
router.include_router(ai_router)
