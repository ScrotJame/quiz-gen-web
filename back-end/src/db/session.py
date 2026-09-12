"""Engine và session factory async cho SQLAlchemy.

Lazy instantiation theo chuẩn P-131 để không mở kết nối khi import module.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    engine_kwargs: dict = {
        "echo": settings.db_echo,
    }

    # SQLite không hỗ trợ pool_size / max_overflow chuẩn
    if "sqlite" in settings.database_url:
        pass
    else:
        engine_kwargs["pool_size"] = settings.db_pool_size
        engine_kwargs["max_overflow"] = settings.db_max_overflow
        engine_kwargs["pool_pre_ping"] = True

    return create_async_engine(settings.database_url, **engine_kwargs)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def dispose_engine() -> None:
    """Giải phóng engine lúc server shutdown."""
    engine = get_engine()
    await engine.dispose()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
