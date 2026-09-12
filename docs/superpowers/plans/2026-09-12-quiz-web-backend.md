# Quiz Web Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng hệ thống backend cho Quiz Web tại thư mục `back-end/` theo chuẩn Clean Architecture 3 lớp kế thừa từ `P-131`, tích hợp OCR hình ảnh (`rapidocr-onnxruntime`) và sinh câu hỏi trắc nghiệm thông minh bằng Mistral AI (`mistral-large-2512` / `mistral-small-2603`).

**Architecture:** Áp dụng mô hình 3 lớp một chiều nghiêm ngặt `api/` -> `services/` -> `repositories/`. Dùng Pydantic `CamelModel` cho frontend Next.js 16; `RapidOCR` xử lý ảnh local 0đ; LLM Mistral xử lý theo `temperature = 0` (nguyên văn 100%) và `temperature > 0` (biên tập chuẩn xác). Cung cấp cả async SQLAlchemy và In-Memory test double.

**Tech Stack:** FastAPI, Uvicorn, Pydantic v2, Pydantic-settings, SQLAlchemy 2.0 (async), aiosqlite / asyncpg, rapidocr-onnxruntime, mistralai, pytest, httpx.

**Spec:** `docs/superpowers/specs/2026-09-12-quiz-web-backend-design.md`

## Global Constraints
- Không dùng cơ chế đăng nhập/JWT bắt buộc (môi trường nội bộ).
- Repository là nơi duy nhất chạm database; Service là thuần Python không import FastAPI; API không chạm Repository.
- Dữ liệu trả về JSON cho frontend theo chuẩn camelCase thông qua `CamelModel`.
- Hỗ trợ chạy local tức thời bằng SQLite Async (`aiosqlite`) và có mock fallback khi chưa nạp `MISTRAL_API_KEY`.

---

### Task 1: Khởi tạo Scaffolding, Dependencies, Config & Database Base

**Files:**
- Create: `back-end/requirements.txt`
- Create: `back-end/.env.example`
- Create: `back-end/src/config.py`
- Create: `back-end/src/db/base.py`
- Create: `back-end/src/db/session.py`
- Test: `back-end/tests/test_config_and_db.py`

**Interfaces:**
- Produces: `get_settings()` -> `Settings`
- Produces: `Base` (DeclarativeBase), `TimestampMixin`, `UUIDMixin`
- Produces: `get_engine()`, `get_sessionmaker()`, `dispose_engine()`

- [ ] **Step 1: Viết test cho cấu hình và DB session**
- [ ] **Step 2: Chạy test để xác nhận FAIL (chưa có code)**
- [ ] **Step 3: Tạo `requirements.txt` và `.env.example`**
- [ ] **Step 4: Viết `src/config.py` (BaseSettings với pydantic-settings)**
- [ ] **Step 5: Viết `src/db/base.py` và `src/db/session.py`**
- [ ] **Step 6: Chạy test để xác nhận PASS**
- [ ] **Step 7: Commit git**

---

### Task 2: Xây dựng Models & Schemas (ORM Tables & CamelModel DTOs)

**Files:**
- Create: `back-end/src/models/schemas.py`
- Create: `back-end/src/models/tables/quiz.py`
- Create: `back-end/src/models/tables/question.py`
- Create: `back-end/src/models/tables/attempt.py`
- Create: `back-end/src/models/tables/__init__.py`
- Test: `back-end/tests/test_models_schemas.py`

**Interfaces:**
- Consumes: `Base`, `TimestampMixin` từ `src/db/base.py`
- Produces: `CamelModel`, `QuizSchema`, `QuestionSchema`, `OptionSchema`, `AttemptSchema`
- Produces: `QuizTable`, `QuestionTable`, `OptionTable`, `AttemptTable`, `AttemptAnswerTable`

- [ ] **Step 1: Viết test kiểm tra serialization CamelModel và quan hệ ORM**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Viết `src/models/schemas.py` với `CamelModel`**
- [ ] **Step 4: Viết các bảng ORM trong `src/models/tables/`**
- [ ] **Step 5: Chạy test xác nhận PASS**
- [ ] **Step 6: Commit git**

---

### Task 3: Xây dựng Repositories Layer (Abstract Base, In-Memory & Async SQL)

**Files:**
- Create: `back-end/src/repositories/base.py`
- Create: `back-end/src/repositories/memory.py`
- Create: `back-end/src/repositories/sql.py`
- Create: `back-end/src/repositories/__init__.py`
- Test: `back-end/tests/test_repositories.py`

**Interfaces:**
- Consumes: `QuizSchema`, `AttemptSchema` từ `src/models/schemas.py`
- Produces: `QuizRepository(ABC)`, `AttemptRepository(ABC)`
- Produces: `InMemoryQuizRepository`, `InMemoryAttemptRepository`
- Produces: `SqlQuizRepository`, `SqlAttemptRepository`
- Produces: `get_quiz_repo()`, `get_attempt_repo()` (provider switch)

- [ ] **Step 1: Viết test cho cả 2 bản cài đặt In-Memory và SQL Repository**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Định nghĩa contracts trong `src/repositories/base.py`**
- [ ] **Step 4: Triển khai `src/repositories/memory.py`**
- [ ] **Step 5: Triển khai `src/repositories/sql.py`**
- [ ] **Step 6: Cài đặt factory providers trong `src/repositories/__init__.py`**
- [ ] **Step 7: Chạy test xác nhận PASS**
- [ ] **Step 8: Commit git**

---

### Task 4: Xây dựng Services Layer (Quiz & Attempt Logic)

**Files:**
- Create: `back-end/src/services/quiz_service.py`
- Create: `back-end/src/services/attempt_service.py`
- Test: `back-end/tests/test_services.py`

**Interfaces:**
- Consumes: `QuizRepository`, `AttemptRepository` qua constructor injection
- Produces: `QuizService.list_quizzes()`, `create_quiz()`, `get_quiz_detail()`
- Produces: `AttemptService.start_attempt()`, `submit_attempt()`, `calculate_score()`, `get_leaderboard()`

- [ ] **Step 1: Viết test nghiệp vụ chấm điểm tự động, tính % đúng, bảng xếp hạng**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Viết `src/services/quiz_service.py`**
- [ ] **Step 4: Viết `src/services/attempt_service.py`**
- [ ] **Step 5: Chạy test xác nhận PASS**
- [ ] **Step 6: Commit git**

---

### Task 5: Xây dựng Module AI (RapidOCR & Mistral AI Quiz Generator)

**Files:**
- Create: `back-end/src/services/ai/ocr.py`
- Create: `back-end/src/services/ai/mistral_client.py`
- Create: `back-end/src/services/ai/prompts.py`
- Create: `back-end/src/services/ai/generator.py`
- Test: `back-end/tests/test_ai_generator.py`

**Interfaces:**
- Consumes: `get_settings()` từ `src/config.py`
- Produces: `extract_text_from_image(image_bytes: bytes) -> str`
- Produces: `QuizGeneratorService.generate_from_text(...)`, `generate_from_image(...)`
- Behavior: `temperature = 0.0` (nguyên văn 100%), `temperature > 0.0` (biên tập chuẩn xác)
- Fallback: Mock Generator tự động sinh đề mẫu khi chưa có `MISTRAL_API_KEY`

- [ ] **Step 1: Viết test cho OCR module, Prompt builder và Generator Mock fallback**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Viết `src/services/ai/ocr.py`**
- [ ] **Step 4: Viết `src/services/ai/mistral_client.py` & `src/services/ai/prompts.py`**
- [ ] **Step 5: Viết `src/services/ai/generator.py`**
- [ ] **Step 6: Chạy test xác nhận PASS**
- [ ] **Step 7: Commit git**

---

### Task 6: Xây dựng API Layer & FastAPI Main Application

**Files:**
- Create: `back-end/src/api/deps.py`
- Create: `back-end/src/api/health.py`
- Create: `back-end/src/api/quizzes.py`
- Create: `back-end/src/api/attempts.py`
- Create: `back-end/src/api/ai.py`
- Create: `back-end/src/api/routes.py`
- Create: `back-end/src/main.py`
- Test: `back-end/tests/test_api_endpoints.py`

**Interfaces:**
- Consumes: `QuizService`, `AttemptService`, `QuizGeneratorService`
- Produces: FastAPI router mounted at `/api/v1`
- Produces: Lifespan lifecycle with DB pre-ping and engine disposal
- Produces: Next.js CORS configuration

- [ ] **Step 1: Viết test integration cho các endpoints bằng `httpx.AsyncClient`**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Viết `src/api/deps.py` và `src/api/routes.py`**
- [ ] **Step 4: Viết các controllers `health.py`, `quizzes.py`, `attempts.py`, `ai.py`**
- [ ] **Step 5: Viết `src/main.py`**
- [ ] **Step 6: Chạy test xác nhận PASS**
- [ ] **Step 7: Commit git**

---

### Task 7: Tài liệu hướng dẫn & Xác thực Toàn diện (End-to-End Verification)

**Files:**
- Create: `back-end/README.md`
- Create: `back-end/src/db/init_db.py` (Script seed quiz mẫu để test UI ngay)
- Test: Toàn bộ test suite `pytest back-end/tests`

- [ ] **Step 1: Viết `src/db/init_db.py` tạo bảng và nạp 1 đề trắc nghiệm mẫu**
- [ ] **Step 2: Viết `back-end/README.md` hướng dẫn chạy server, test và tích hợp với `front-end`**
- [ ] **Step 3: Chạy toàn bộ test suite để đảm bảo 100% tests PASS**
- [ ] **Step 4: Chạy thử uvicorn server và gọi test `/api/v1/health`**
- [ ] **Step 5: Commit git hoàn tất**
