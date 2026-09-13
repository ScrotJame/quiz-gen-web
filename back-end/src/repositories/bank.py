"""SqlBankRepository — Ngân hàng câu hỏi với batch insert chống N+1.

Chiến lược:
- Ghi: session.add_all() gom toàn bộ questions và options vào 1 transaction duy nhất.
- Đọc: selectinload(BankQuestionTable.options) chỉ sinh ra 2 SQL queries (IN-loading).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from src.db.session import get_sessionmaker
from src.models.schemas import (
    BankOptionSchema,
    BankQuestionCreate,
    BankQuestionSchema,
    BankQuestionUpdate,
)
from src.models.tables.bank import BankOptionTable, BankQuestionTable


def _to_schema(row: BankQuestionTable) -> BankQuestionSchema:
    """Chuyển đổi ORM row -> Pydantic schema (không gọi thêm query)."""
    return BankQuestionSchema(
        id=row.id,
        question_text=row.question_text,
        question_type=row.question_type,
        category=row.category,
        difficulty=row.difficulty,
        explanation=row.explanation,
        source_note=row.source_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
        options=[
            BankOptionSchema(
                id=opt.id,
                question_id=opt.question_id,
                option_text=opt.option_text,
                is_correct=opt.is_correct,
                order_num=opt.order_num,
            )
            for opt in row.options
        ],
    )


class SqlBankRepository:
    """Truy cập dữ liệu Ngân hàng câu hỏi qua SQLAlchemy Async."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.session_factory = session_factory or get_sessionmaker()

    async def batch_create_questions(
        self, questions: list[BankQuestionCreate]
    ) -> list[BankQuestionSchema]:
        """Lưu hàng loạt câu hỏi vào ngân hàng trong 1 transaction duy nhất.

        Sinh UUID trước, gom toàn bộ rows, gọi add_all 2 lần (questions, options)
        rồi commit — không có N+1 query khi ghi.
        """
        question_rows: list[BankQuestionTable] = []
        option_rows: list[BankOptionTable] = []

        for q_in in questions:
            q_id = uuid.uuid4()
            q_row = BankQuestionTable(
                id=q_id,
                question_text=q_in.question_text,
                question_type=q_in.question_type,
                category=q_in.category,
                difficulty=q_in.difficulty,
                explanation=q_in.explanation,
                source_note=q_in.source_note,
            )
            question_rows.append(q_row)

            for idx, opt_in in enumerate(q_in.options):
                option_rows.append(
                    BankOptionTable(
                        id=uuid.uuid4(),
                        question_id=q_id,
                        option_text=opt_in.option_text,
                        is_correct=opt_in.is_correct,
                        order_num=opt_in.order_num if opt_in.order_num is not None else idx,
                    )
                )

        async with self.session_factory() as session:
            async with session.begin():
                session.add_all(question_rows)
                session.add_all(option_rows)
            # Sau commit, load lại để có options qua selectinload (2 queries tổng)
            ids = [q.id for q in question_rows]
            stmt = (
                select(BankQuestionTable)
                .where(BankQuestionTable.id.in_(ids))
                .options(selectinload(BankQuestionTable.options))
                .order_by(BankQuestionTable.created_at)
            )
            rows = (await session.execute(stmt)).scalars().all()

        return [_to_schema(r) for r in rows]

    async def list_questions(
        self,
        *,
        category: str | None = None,
        difficulty: str | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
        page: int | None = None,
    ) -> tuple[list[BankQuestionSchema], int]:
        """Tra cứu câu hỏi có lọc, tìm kiếm và phân trang.

        Luôn chỉ sinh ra 2 SQL queries:
        1. COUNT(*) cho total
        2. SELECT ... LIMIT/OFFSET với selectinload options
        """
        if page is not None and page >= 1:
            offset = (page - 1) * limit

        async with self.session_factory() as session:
            base_query = select(BankQuestionTable)
            if category:
                base_query = base_query.where(BankQuestionTable.category == category)
            if difficulty:
                base_query = base_query.where(BankQuestionTable.difficulty == difficulty)
            if search:
                term = f"%{search}%"
                base_query = base_query.where(BankQuestionTable.question_text.ilike(term))

            # Query 1: đếm tổng số
            count_stmt = select(func.count()).select_from(base_query.subquery())
            total = (await session.execute(count_stmt)).scalar() or 0

            # Query 2: lấy trang + selectinload options (=> 2 total SQL queries)
            stmt = (
                base_query
                .options(selectinload(BankQuestionTable.options))
                .order_by(BankQuestionTable.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            rows = (await session.execute(stmt)).scalars().all()

        return [_to_schema(r) for r in rows], total

    async def get_categories(self) -> list[str]:
        """Lấy danh sách categories duy nhất, sắp xếp theo alphabet."""
        async with self.session_factory() as session:
            stmt = (
                select(distinct(BankQuestionTable.category))
                .order_by(BankQuestionTable.category)
            )
            result = (await session.execute(stmt)).scalars().all()
        return list(result)

    async def get_question(self, question_id: uuid.UUID) -> BankQuestionSchema | None:
        """Lấy chi tiết 1 câu hỏi kèm options."""
        async with self.session_factory() as session:
            stmt = (
                select(BankQuestionTable)
                .where(BankQuestionTable.id == question_id)
                .options(selectinload(BankQuestionTable.options))
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return _to_schema(row)

    async def update_question(
        self, question_id: uuid.UUID, data: BankQuestionUpdate
    ) -> BankQuestionSchema | None:
        """Cập nhật một phần thông tin câu hỏi (không sửa options)."""
        async with self.session_factory() as session:
            stmt = (
                select(BankQuestionTable)
                .where(BankQuestionTable.id == question_id)
                .options(selectinload(BankQuestionTable.options))
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                return None

            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(row, field, value)
            row.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(row)

        return _to_schema(row)

    async def delete_question(self, question_id: uuid.UUID) -> bool:
        """Xóa câu hỏi (cascade xóa options theo FK)."""
        async with self.session_factory() as session:
            stmt = select(BankQuestionTable).where(BankQuestionTable.id == question_id)
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
        return True

    async def sample_by_matrix(
        self,
        *,
        category: str | None = None,
        easy_count: int = 0,
        medium_count: int = 0,
        hard_count: int = 0,
    ) -> tuple[list[BankQuestionSchema], list[str]]:
        """Bốc ngẫu nhiên câu hỏi theo ma trận độ khó và danh mục (chống N+1)."""
        sampled_questions: list[BankQuestionSchema] = []
        warnings: list[str] = []

        difficulty_requests = [
            ("easy", "Dễ", easy_count),
            ("medium", "Trung bình", medium_count),
            ("hard", "Khó", hard_count),
        ]

        async with self.session_factory() as session:
            for diff_val, diff_label, count in difficulty_requests:
                if count <= 0:
                    continue

                stmt = (
                    select(BankQuestionTable)
                    .options(selectinload(BankQuestionTable.options))
                    .where(BankQuestionTable.difficulty == diff_val)
                )
                if category:
                    stmt = stmt.where(BankQuestionTable.category == category)

                stmt = stmt.order_by(func.random()).limit(count)
                rows = (await session.execute(stmt)).scalars().all()
                found_count = len(rows)

                if found_count < count:
                    warnings.append(
                        f"Mức độ '{diff_label}': Kho chỉ có {found_count} câu (yêu cầu {count} câu), đã lấy {found_count} câu."
                    )

                for r in rows:
                    sampled_questions.append(_to_schema(r))

        return sampled_questions, warnings
