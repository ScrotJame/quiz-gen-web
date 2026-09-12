"""Script khởi tạo database và nạp dữ liệu câu hỏi trắc nghiệm mẫu."""

import asyncio
import logging

from src.db.base import Base
from src.db.session import dispose_engine, get_engine
from src.models.schemas import Difficulty, OptionCreate, QuestionCreate, QuestionType, QuizCreate
from src.repositories import get_quiz_repo
import src.models.tables  # noqa: F401

logging.basicConfig(level="INFO")
logger = logging.getLogger("init_db")


async def init_and_seed() -> None:
    logger.info("1. Tạo các bảng trong cơ sở dữ liệu...")
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tạo bảng thành công.")

    logger.info("2. Kiểm tra và nạp đề trắc nghiệm mẫu...")
    quiz_repo = get_quiz_repo()
    quizzes, total = await quiz_repo.list_quizzes()
    if total > 0:
        logger.info(f"Database đã có sẵn {total} đề thi. Bỏ qua bước seed.")
        await dispose_engine()
        return

    sample_quiz = QuizCreate(
        title="Kiến thức Lập trình Python & Clean Architecture",
        description="Bộ đề thi trắc nghiệm mẫu kiểm tra kiến thức về FastAPI, Python 3 và mô hình 3 lớp Clean Architecture.",
        category="Công nghệ thông tin",
        difficulty=Difficulty.MEDIUM,
        time_limit_minutes=15,
        author_name="Ban Đào Tạo",
        questions=[
            QuestionCreate(
                question_text="Trong kiến trúc 3 lớp (3-tier) của FastAPI, tầng nào chịu trách nhiệm lưu trữ và truy vấn database?",
                question_type=QuestionType.SINGLE_CHOICE,
                points=10,
                order_num=0,
                explanation="Repository Layer là nơi duy nhất chạm tới storage (SQL/In-Memory), cách ly hoàn toàn với tầng Controller và Service.",
                options=[
                    OptionCreate(option_text="API / Controller Layer", is_correct=False, order_num=0),
                    OptionCreate(option_text="Service Layer", is_correct=False, order_num=1),
                    OptionCreate(option_text="Repository Layer", is_correct=True, order_num=2),
                    OptionCreate(option_text="Presentation Layer", is_correct=False, order_num=3),
                ],
            ),
            QuestionCreate(
                question_text="Khi sử dụng AI Vision/OCR để tạo trắc nghiệm từ ảnh, thiết lập temperature = 0 có ý nghĩa gì?",
                question_type=QuestionType.SINGLE_CHOICE,
                points=10,
                order_num=1,
                explanation="Temperature = 0 kích hoạt chế độ trích xuất nguyên văn 100% câu chữ từ ảnh, không tự ý viết lại hoặc thêm bớt từ ngữ.",
                options=[
                    OptionCreate(option_text="AI tự do sáng tạo thêm câu hỏi mới", is_correct=False, order_num=0),
                    OptionCreate(option_text="Trích xuất nguyên văn 100% từng câu chữ từ ảnh", is_correct=True, order_num=1),
                    OptionCreate(option_text="Dịch câu hỏi sang tiếng Anh tự động", is_correct=False, order_num=2),
                    OptionCreate(option_text="Bỏ qua các câu hỏi khó trong ảnh", is_correct=False, order_num=3),
                ],
            ),
            QuestionCreate(
                question_text="Tại sao Pydantic CamelModel được sử dụng trong hệ thống backend này?",
                question_type=QuestionType.SINGLE_CHOICE,
                points=10,
                order_num=2,
                explanation="CamelModel giúp Python code viết chuẩn snake_case nhưng khi trả về JSON cho Next.js thì tự động thành camelCase.",
                options=[
                    OptionCreate(option_text="Để Next.js frontend nhận JSON chuẩn camelCase tự nhiên mà không cần map đổi tay", is_correct=True, order_num=0),
                    OptionCreate(option_text="Để tăng tốc độ truy vấn SQLite", is_correct=False, order_num=1),
                    OptionCreate(option_text="Để bảo mật mật khẩu người dùng", is_correct=False, order_num=2),
                    OptionCreate(option_text="Để nén dung lượng ảnh OCR", is_correct=False, order_num=3),
                ],
            ),
        ],
    )

    created = await quiz_repo.create_quiz(sample_quiz)
    logger.info(f"Đã tạo thành công đề thi mẫu ID: {created.id} ({created.title})")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(init_and_seed())
