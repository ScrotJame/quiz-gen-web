"""Repository layer — nơi duy nhất chạm tới storage.

Kế thừa mô hình provider từ P-131: tự động chuyển đổi giữa SQL và In-Memory dựa trên config.
"""

from __future__ import annotations

from functools import lru_cache

from src.config import get_settings
from src.repositories.base import AttemptRepository, QuizRepository
from src.repositories.memory import InMemoryAttemptRepository, InMemoryQuizRepository
from src.repositories.sql import SqlAttemptRepository, SqlQuizRepository

__all__ = [
    "QuizRepository",
    "AttemptRepository",
    "InMemoryQuizRepository",
    "InMemoryAttemptRepository",
    "SqlQuizRepository",
    "SqlAttemptRepository",
    "get_quiz_repo",
    "get_attempt_repo",
]


@lru_cache
def get_quiz_repo() -> QuizRepository:
    settings = get_settings()
    if settings.use_in_memory_repos:
        attempt_repo = get_attempt_repo()
        if isinstance(attempt_repo, InMemoryAttemptRepository):
            return InMemoryQuizRepository(attempt_repo=attempt_repo)
        return InMemoryQuizRepository()
    return SqlQuizRepository()


@lru_cache
def get_attempt_repo() -> AttemptRepository:
    settings = get_settings()
    if settings.use_in_memory_repos:
        return InMemoryAttemptRepository()
    return SqlAttemptRepository()
