from __future__ import annotations

from src.core.exceptions import (
    AppError,
    EntityNotFoundError,
    ExternalServiceError,
    GenerationFailedError,
    InvalidImageError,
    InvalidInputError,
    NoTextFoundError,
    OCRFailedError,
    RateLimitExceededError,
    register_exception_handlers,
)

__all__ = [
    "AppError",
    "EntityNotFoundError",
    "ExternalServiceError",
    "GenerationFailedError",
    "InvalidImageError",
    "InvalidInputError",
    "NoTextFoundError",
    "OCRFailedError",
    "RateLimitExceededError",
    "register_exception_handlers",
]
