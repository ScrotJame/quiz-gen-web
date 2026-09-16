from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Lớp ngoại lệ cơ sở cho toàn bộ ứng dụng."""

    error_code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code
        self.details = details


class InvalidInputError(AppError):
    error_code = "INVALID_INPUT"
    status_code = 400


class InvalidImageError(AppError):
    error_code = "INVALID_IMAGE"
    status_code = 400


class EntityNotFoundError(AppError):
    error_code = "NOT_FOUND"
    status_code = 404


class NoTextFoundError(AppError):
    error_code = "NO_TEXT_FOUND"
    status_code = 422


class RateLimitExceededError(AppError):
    error_code = "RATE_LIMIT_EXCEEDED"
    status_code = 429


class ExternalServiceError(AppError):
    error_code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502


class OCRFailedError(AppError):
    error_code = "OCR_FAILED"
    status_code = 500


class GenerationFailedError(AppError):
    error_code = "GENERATION_FAILED"
    status_code = 500


def register_exception_handlers(app: FastAPI) -> None:
    """Đăng ký exception handler tập trung cho FastAPI app."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        error_body = {
            "error_code": exc.error_code,
            "message": exc.message,
        }
        if exc.details is not None:
            error_body["details"] = exc.details

        # Đảm bảo tương thích cả chuẩn contract {"error_code", "message"}
        # lẫn FastAPI convention {"detail": {"error_code", "message"}}
        content: dict[str, Any] = {
            "error_code": exc.error_code,
            "message": exc.message,
            "detail": error_body,
        }
        if exc.details is not None:
            content["details"] = exc.details

        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Lỗi máy chủ không xác định tại %s %s: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "Đã có lỗi xảy ra phía máy chủ. Vui lòng thử lại sau.",
                "detail": {
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": "Đã có lỗi xảy ra phía máy chủ. Vui lòng thử lại sau.",
                },
            },
        )
