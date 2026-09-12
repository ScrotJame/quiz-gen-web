from __future__ import annotations

from src.repositories import get_attempt_repo, get_quiz_repo
from src.services.ai.generator import QuizGeneratorService
from src.services.attempt_service import AttemptService
from src.services.quiz_service import QuizService


def get_quiz_service() -> QuizService:
    return QuizService(get_quiz_repo())


def get_attempt_service() -> AttemptService:
    return AttemptService(get_attempt_repo(), get_quiz_repo())


def get_quiz_generator_service() -> QuizGeneratorService:
    return QuizGeneratorService(get_quiz_repo())
