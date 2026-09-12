import os
import pytest
import pytest_asyncio
from sqlalchemy import text

# Đặt biến môi trường test
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_quiz.db"
os.environ["USE_IN_MEMORY_REPOS"] = "false"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://127.0.0.1:3000"
os.environ["MISTRAL_API_KEY"] = ""  # Rule 6: Mock/fallback trong test tự động, không gọi API thật
os.environ["GEMINI_API_KEY"] = ""  # Rule 6: Mock/fallback trong test tự động, không gọi API thật

from src.config import get_settings
get_settings.cache_clear()

from src.db.base import Base
from src.db.session import dispose_engine, get_engine
import src.models.tables  # noqa: F401


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await dispose_engine()

    # Dọn dẹp file test db
    if os.path.exists("./test_quiz.db"):
        try:
            os.remove("./test_quiz.db")
        except Exception:
            pass
