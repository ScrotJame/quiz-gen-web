from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.api.routes import router as api_router
from src.config import get_settings
from src.db.base import Base
from src.db.session import dispose_engine, get_engine

logging.basicConfig(
    level=get_settings().log_level,
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
)
logger = logging.getLogger("quiz_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Khởi động {settings.app_name} tại môi trường {settings.app_env}")

    if not settings.use_in_memory_repos and settings.app_env != "test":
        try:
            async with get_engine().begin() as conn:
                import src.models.tables  # noqa: F401
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Khởi tạo Database tables thành công.")

            # Kiểm tra kết nối DB ngay khi boot
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Kết nối Database: OK")
        except Exception as e:
            logger.error(f"Lỗi kết nối cơ sở dữ liệu khi khởi động: {e}", exc_info=True)

    yield

    logger.info("Đang tắt server và giải phóng database engine...")
    await dispose_engine()
    logger.info("Shutdown hoàn tất.")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Quiz Web Backend với Clean Architecture 3 lớp và Mistral AI Generator",
    version="1.0.0",
    lifespan=lifespan,
)

# Cấu hình CORS cho Next.js frontend
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký routes
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "message": f"Chào mừng tới {settings.app_name}",
        "docs": "/docs",
        "api": "/api/v1",
    }
