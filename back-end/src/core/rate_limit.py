from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import get_settings

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Sliding-window In-Memory Rate Limiter theo Client IP."""

    def __init__(self) -> None:
        self._history: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str, max_requests: int, window_seconds: float) -> tuple[bool, int]:
        """Kiểm tra request có được phép hay không và trả về số giây cần chờ nếu bị block."""
        now = time.monotonic()
        cutoff = now - window_seconds

        async with self._lock:
            timestamps = self._history[key]
            # Loại bỏ các timestamp cũ hơn window
            valid_timestamps = [t for t in timestamps if t > cutoff]
            self._history[key] = valid_timestamps

            if len(valid_timestamps) >= max_requests:
                earliest = valid_timestamps[0]
                retry_after = max(1, int(earliest + window_seconds - now) + 1)
                return False, retry_after

            valid_timestamps.append(now)
            return True, 0

    async def cleanup(self) -> None:
        """Dọn dẹp các key đã hết hạn để giải phóng bộ nhớ."""
        now = time.monotonic()
        async with self._lock:
            expired_keys = [
                key for key, timestamps in self._history.items()
                if not timestamps or timestamps[-1] < (now - 120)
            ]
            for key in expired_keys:
                del self._history[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware áp dụng giới hạn tần suất request để phòng chống DoS và cạn kiệt chi phí API."""

    def __init__(self, app, limiter: InMemoryRateLimiter | None = None) -> None:
        super().__init__(app)
        self.limiter = limiter or InMemoryRateLimiter()

    def _get_client_ip(self, request: Request) -> str:
        """Lấy IP thực của client, ưu tiên CF-Connecting-IP và X-Forwarded-For."""
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()

        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()

        # Bỏ qua rate limit trong môi trường test
        if settings.app_env == "test":
            return await call_next(request)

        path = request.url.path

        # Chỉ áp dụng rate limit cho các API endpoint
        if not path.startswith("/api/v1"):
            return await call_next(request)

        # Endpoint healthcheck không bị rate limit
        if path.endswith("/health"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # Phân loại giới hạn: AI endpoint nghiêm ngặt hơn vì tốn chi phí và CPU
        if "/ai/" in path:
            max_requests = 10
            window_seconds = 60.0
            key = f"ai:{client_ip}"
        else:
            max_requests = 60
            window_seconds = 60.0
            key = f"general:{client_ip}"

        allowed, retry_after = await self.limiter.is_allowed(key, max_requests, window_seconds)

        if not allowed:
            logger.warning(
                "Rate limit exceeded cho IP %s tại đường dẫn %s. Cần chờ %d giây.",
                client_ip,
                path,
                retry_after,
            )
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau {retry_after} giây.",
                    "details": {"retry_after_seconds": retry_after},
                },
            )

        return await call_next(request)
