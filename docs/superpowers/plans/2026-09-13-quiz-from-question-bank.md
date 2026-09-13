# Tạo Đề Thi Từ Thư Viện Câu Hỏi (Question Bank) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng tính năng tạo đề thi trực tiếp từ Ngân hàng câu hỏi thông qua hai phương thức: chọn thủ công bằng checkbox trên trang `/bank` và sinh đề tự động theo Ma trận tiêu chí (Matrix Generator), sau đó nạp vào màn hình biên tập toàn màn hình `/create/from-bank` để hoàn tất và xuất bản đề thi.

**Architecture:** Mở rộng backend với truy vấn SQL ngẫu nhiên chống N+1 (`selectinload(options)`) cho endpoint `POST /api/v1/bank/matrix-generate`. Ở frontend, tạo trang quản lý ngân hàng câu hỏi `/bank` với bộ lọc/tìm kiếm, floating action bar chọn câu hỏi hàng loạt, modal ma trận sinh đề và trang biên tập `/create/from-bank` tái sử dụng `QuizEditor`.

**Tech Stack:** FastAPI (Python 3.13), SQLAlchemy 2.0 Async, Pydantic v2, Next.js 15 (App Router), TypeScript (strict: true), TailwindCSS, Lucide Icons.

**Spec:** `docs/superpowers/specs/2026-09-13-quiz-from-question-bank-design.md`

## Global Constraints
- Tech stack đã chốt: Next.js + FastAPI + SQLAlchemy. Không thay đổi framework.
- Không import chéo code giữa frontend và backend; chỉ giao tiếp qua REST JSON.
- Chống N+1 query tuyệt đối trên SQLAlchemy khi bốc câu hỏi kèm options.
- Không để lỗi 500 trần trụi; trả về lỗi chuẩn và cảnh báo rõ ràng khi kho không đủ câu.
- Frontend tuân thủ TypeScript `strict: true`, không dùng `any`.
- Mọi logic backend phải tuân thủ TDD: viết test trước (Red) $\rightarrow$ code tối thiểu (Green) $\rightarrow$ Refactor.

---

### Task 1: Backend Schemas & Repository Matrix Sampling (TDD)

**Files:**
- Modify: `back-end/src/models/schemas.py:120-140`
- Modify: `back-end/src/repositories/bank.py:20-50`, `200-230`
- Test: `back-end/tests/test_bank_matrix.py`

**Interfaces:**
- Consumes: `BankQuestionTable`, `BankOptionTable`, `selectinload`, `func.random()`, `get_sessionmaker()`
- Produces: 
  - `BankMatrixGenerateRequest(category: str | None, easy_count: int, medium_count: int, hard_count: int)`
  - `BankMatrixGenerateResponse(questions: list[BankQuestionSchema], total: int, warnings: list[str])`
  - `SqlBankRepository.sample_by_matrix(category: str | None, easy_count: int, medium_count: int, hard_count: int) -> tuple[list[BankQuestionSchema], list[str]]`

- [ ] **Step 1: Write the failing tests for repository matrix sampling**

Create `back-end/tests/test_bank_matrix.py`:
```python
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.schemas import BankOptionCreate, BankQuestionCreate, QuestionType
from src.models.tables.bank import BankQuestionTable
from src.repositories.bank import SqlBankRepository


def _make_bank_question(category: str, difficulty: str, text_suffix: str) -> BankQuestionCreate:
    return BankQuestionCreate(
        question_text=f"Câu hỏi {category} {difficulty} {text_suffix}",
        question_type=QuestionType.SINGLE_CHOICE,
        category=category,
        difficulty=difficulty,
        explanation=f"Giải thích cho {text_suffix}",
        options=[
            BankOptionCreate(option_text=f"A. Đáp án 1 {text_suffix}", is_correct=True, order_num=0),
            BankOptionCreate(option_text=f"B. Đáp án 2 {text_suffix}", is_correct=False, order_num=1),
        ],
    )


@pytest.mark.asyncio
async def test_sample_by_matrix_sufficient_questions(db_sessionmaker):
    repo = SqlBankRepository(session_factory=db_sessionmaker)
    # Seed 3 easy, 3 medium, 3 hard for 'Math'
    seed_data = [
        _make_bank_question("Math", "easy", f"E{i}") for i in range(3)
    ] + [
        _make_bank_question("Math", "medium", f"M{i}") for i in range(3)
    ] + [
        _make_bank_question("Math", "hard", f"H{i}") for i in range(3)
    ]
    await repo.batch_create_questions(seed_data)

    questions, warnings = await repo.sample_by_matrix(
        category="Math",
        easy_count=2,
        medium_count=2,
        hard_count=1,
    )

    assert len(questions) == 5
    assert len(warnings) == 0

    easy_sampled = [q for q in questions if q.difficulty == "easy"]
    med_sampled = [q for q in questions if q.difficulty == "medium"]
    hard_sampled = [q for q in questions if q.difficulty == "hard"]

    assert len(easy_sampled) == 2
    assert len(med_sampled) == 2
    assert len(hard_sampled) == 1
    for q in questions:
        assert len(q.options) == 2


@pytest.mark.asyncio
async def test_sample_by_matrix_insufficient_questions_generates_warnings(db_sessionmaker):
    repo = SqlBankRepository(session_factory=db_sessionmaker)
    # Seed only 1 hard question
    seed_data = [
        _make_bank_question("Physics", "hard", "SingleHard")
    ]
    await repo.batch_create_questions(seed_data)

    questions, warnings = await repo.sample_by_matrix(
        category="Physics",
        easy_count=2,
        medium_count=0,
        hard_count=5,
    )

    # We asked for 2 easy (0 found) and 5 hard (1 found)
    assert len(questions) == 1
    assert questions[0].difficulty == "hard"
    assert len(warnings) == 2
    assert any("Dễ" in w or "easy" in w.lower() for w in warnings)
    assert any("Khó" in w or "hard" in w.lower() for w in warnings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bank_matrix.py -v`
Expected: FAIL with `AttributeError: 'SqlBankRepository' object has no attribute 'sample_by_matrix'`

- [ ] **Step 3: Implement schemas and repository method**

1. In `back-end/src/models/schemas.py`, add:
```python
class BankMatrixGenerateRequest(CamelModel):
    category: str | None = None
    easy_count: int = Field(default=0, ge=0, le=100)
    medium_count: int = Field(default=0, ge=0, le=100)
    hard_count: int = Field(default=0, ge=0, le=100)


class BankMatrixGenerateResponse(CamelModel):
    questions: list[BankQuestionSchema]
    total: int
    warnings: list[str]
```

2. In `back-end/src/repositories/bank.py`, add `sample_by_matrix`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_bank_matrix.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add back-end/src/models/schemas.py back-end/src/repositories/bank.py back-end/tests/test_bank_matrix.py
git commit -m "feat(backend): implement bank matrix sampling in repository with tests"
```

---

### Task 2: Backend Service & API Endpoint for Matrix Generate (TDD)

**Files:**
- Modify: `back-end/src/services/bank_service.py`
- Modify: `back-end/src/api/bank.py`
- Test: `back-end/tests/test_bank_matrix.py`

**Interfaces:**
- Consumes: `SqlBankRepository.sample_by_matrix`, `BankMatrixGenerateRequest`
- Produces: `POST /api/v1/bank/matrix-generate` endpoint returning `BankMatrixGenerateResponse`

- [ ] **Step 1: Add failing API endpoint test to `test_bank_matrix.py`**

Append to `back-end/tests/test_bank_matrix.py`:
```python
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_api_matrix_generate_endpoint(db_sessionmaker):
    repo = SqlBankRepository(session_factory=db_sessionmaker)
    await repo.batch_create_questions([
        _make_bank_question("History", "easy", "H1"),
        _make_bank_question("History", "medium", "H2"),
    ])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/bank/matrix-generate",
            json={
                "category": "History",
                "easyCount": 1,
                "mediumCount": 1,
                "hardCount": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["questions"]) == 2
        assert len(data["warnings"]) == 1
        assert "Khó" in data["warnings"][0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bank_matrix.py::test_api_matrix_generate_endpoint -v`
Expected: FAIL with status 404 Not Found (endpoint does not exist yet).

- [ ] **Step 3: Implement Service method and API Endpoint**

1. In `back-end/src/services/bank_service.py`:
```python
    async def sample_by_matrix(
        self, data: BankMatrixGenerateRequest
    ) -> BankMatrixGenerateResponse:
        questions, warnings = await self.repo.sample_by_matrix(
            category=data.category,
            easy_count=data.easy_count,
            medium_count=data.medium_count,
            hard_count=data.hard_count,
        )
        return BankMatrixGenerateResponse(
            questions=questions,
            total=len(questions),
            warnings=warnings,
        )
```

2. In `back-end/src/api/bank.py`:
```python
from src.models.schemas import (
    BankCategoriesResponse,
    BankMatrixGenerateRequest,
    BankMatrixGenerateResponse,
    BankQuestionBatchCreate,
    BankQuestionListResponse,
    BankQuestionSchema,
    BankQuestionUpdate,
)

@router.post(
    "/matrix-generate",
    response_model=BankMatrixGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Sinh danh sách câu hỏi theo ma trận tiêu chí",
)
async def matrix_generate_questions(
    data: BankMatrixGenerateRequest,
    service: BankServiceDep,
) -> BankMatrixGenerateResponse:
    """Bốc ngẫu nhiên câu hỏi từ ngân hàng theo độ khó và danh mục."""
    return await service.sample_by_matrix(data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_bank_matrix.py -v`
Expected: PASS (all 3 tests pass)

- [ ] **Step 5: Commit**

```bash
git add back-end/src/services/bank_service.py back-end/src/api/bank.py back-end/tests/test_bank_matrix.py
git commit -m "feat(backend): add POST /api/v1/bank/matrix-generate endpoint with tests"
```

---

### Task 3: Frontend API Client & Types

**Files:**
- Modify: `front-end/src/lib/types.ts`
- Modify: `front-end/src/lib/api-client.ts`

**Interfaces:**
- Consumes: `POST /api/v1/bank/matrix-generate`
- Produces: 
  - `BankMatrixGenerateRequest` interface
  - `BankMatrixGenerateResponse` interface
  - `generateBankMatrix(params: BankMatrixGenerateRequest): Promise<BankMatrixGenerateResponse>`

- [ ] **Step 1: Add types in `front-end/src/lib/types.ts`**

```typescript
export interface BankMatrixGenerateRequest {
  category?: string | null;
  easyCount: number;
  mediumCount: number;
  hardCount: number;
}

export interface BankMatrixGenerateResponse {
  questions: BankQuestionSchema[];
  total: number;
  warnings: string[];
}
```

- [ ] **Step 2: Add API call function in `front-end/src/lib/api-client.ts`**

```typescript
export async function generateBankMatrix(
  data: BankMatrixGenerateRequest
): Promise<BankMatrixGenerateResponse> {
  const response = await fetch(`${API_BASE}/api/v1/bank/matrix-generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Không thể sinh câu hỏi theo ma trận");
  }
  return response.json();
}
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `npx tsc --noEmit` in `front-end`
Expected: PASS with 0 errors.

- [ ] **Step 4: Commit**

```bash
git add front-end/src/lib/types.ts front-end/src/lib/api-client.ts
git commit -m "feat(frontend): add generateBankMatrix client function and types"
```

---

### Task 4: Frontend Matrix Generate Modal & Question Bank Page (`/bank`)

**Files:**
- Create: `front-end/src/components/bank/MatrixGenerateModal.tsx`
- Create: `front-end/src/components/bank/EditBankQuestionModal.tsx`
- Create: `front-end/src/app/bank/page.tsx`
- Modify: `front-end/src/components/layout/Navbar.tsx`

**Interfaces:**
- Consumes: `getBankQuestions`, `getBankCategories`, `updateBankQuestion`, `deleteBankQuestion`, `generateBankMatrix`
- Produces:
  - Responsive `/bank` page with table/cards, search, category & difficulty filters, pagination
  - Checkbox selection & bottom floating bar
  - Staging questions into `sessionStorage.setItem("quiz_bank_staging", JSON.stringify({ questions, category, source: "..." }))`
  - Modal matrix generator with live calculation and error/warning handling

- [ ] **Step 1: Create `MatrixGenerateModal.tsx`**
Includes:
- Category selection dropdown (loaded dynamically via `getBankCategories()`)
- Inputs for easyCount, mediumCount, hardCount with plus/minus buttons
- Real-time sum calculation
- Loading indicator while generating
- Stores response to `sessionStorage` and calls `router.push('/create/from-bank')`

- [ ] **Step 2: Create `EditBankQuestionModal.tsx`**
Allows updating `questionText`, `category`, `difficulty`, `explanation` for an existing bank question using `updateBankQuestion()`.

- [ ] **Step 3: Create `front-end/src/app/bank/page.tsx`**
- Page container with Navbar.
- Header: Title "Ngân hàng câu hỏi", count stats, button "Tạo đề theo Ma trận".
- Search input (debounced) & filters for category, difficulty.
- Question list cards with checkboxes, expandable options & explanations, edit & delete buttons.
- Server-side pagination controls (Previous/Next page).
- Fixed bottom Floating Action Bar when `selectedIds.size > 0`:
  - Shows "Đã chọn X câu hỏi"
  - Button "Bỏ chọn"
  - Button "Tạo đề thi từ X câu đã chọn" $\rightarrow$ saves to `sessionStorage` and navigates to `/create/from-bank`.

- [ ] **Step 4: Update `Navbar.tsx`**
Add link/button to `/bank` with icon `Database` or `BookOpen` so users can access the bank from any page.

- [ ] **Step 5: Verify build & lint**

Run: `npm run lint` in `front-end`
Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add front-end/src/components/bank/ front-end/src/app/bank/ front-end/src/components/layout/Navbar.tsx
git commit -m "feat(frontend): create Question Bank page /bank with matrix modal and floating selection bar"
```

---

### Task 5: Frontend Dedicated Quiz Creation from Bank (`/create/from-bank`)

**Files:**
- Create: `front-end/src/app/create/from-bank/page.tsx`

**Interfaces:**
- Consumes:
  - `sessionStorage.getItem("quiz_bank_staging")`
  - `QuizEditor` component
  - `createQuiz` API
- Produces:
  - `/create/from-bank` route that initializes `QuizEditor` with the staged questions, handles empty state if direct URL visited, and redirects to `/quiz/{quizId}` on success.

- [ ] **Step 1: Create `front-end/src/app/create/from-bank/page.tsx`**
- Reads staging payload from `sessionStorage` on mount.
- Translates `BankQuestionSchema[]` into `QuestionEdit[]` using UUIDs.
- Pre-fills suggested Title: `"Đề thi từ Ngân hàng câu hỏi - [Category]"` and Category.
- Displays warning banner if `staging.warnings` contains any alerts.
- Embeds `QuizEditor`:
  - `onSave`: calls `createQuiz()`, clears `sessionStorage`, and pushes to `/quiz/${quiz.id}`.
  - `onBack`: confirms and routes back to `/bank`.
- If no questions found in `sessionStorage`: renders friendly Empty State with a button "Quay lại Ngân hàng câu hỏi".

- [ ] **Step 2: Verify build & lint**

Run: `npm run lint` in `front-end`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add front-end/src/app/create/from-bank/page.tsx
git commit -m "feat(frontend): create /create/from-bank page preloaded with staged questions into QuizEditor"
```

---

### Task 6: End-to-End Verification

**Files:**
- Test: All backend tests and frontend production build

- [ ] **Step 1: Run complete backend pytest suite**
Run: `pytest tests/test_bank_matrix.py tests/test_bank_api.py tests/test_bank_repository.py -v`
Expected: 100% PASS.

- [ ] **Step 2: Run frontend production build**
Run: `npm run build` in `front-end`
Expected: Build successfully completes with static/dynamic route `/bank` and `/create/from-bank`.

- [ ] **Step 3: Commit all remaining changes**
```bash
git commit -m "chore: complete end-to-end verification for quiz creation from question bank"
```
