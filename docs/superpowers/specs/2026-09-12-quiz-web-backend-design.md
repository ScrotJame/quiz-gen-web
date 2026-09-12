# Thiết kế Kiến trúc Backend cho Quiz Web (Kế thừa chuẩn P-131)

**Ngày:** 2026-09-12  
**Mục tiêu:** Xây dựng hệ thống backend cho Quiz Web tại thư mục `back-end/` áp dụng Clean Architecture 3 lớp kế thừa từ `D:\VIN.AI\VIN_team_131\P-131\src`, tích hợp module AI Quiz Generation sử dụng **Mistral AI**, lược bỏ cơ chế đăng nhập (phục vụ nội bộ).

---

## 1. Mục tiêu & Ràng buộc hệ thống

- **Môi trường sử dụng**: Nội bộ (Internal Tooling), không cần đăng nhập/mật khẩu phức tạp. Người dùng chỉ cần nhập tên hiển thị (`creator_name` khi tạo quiz hoặc `participant_name` khi làm bài).
- **AI Generator**: Tích hợp **Mistral AI** (`mistralai` SDK / Mistral API qua httpx hoặc langchain-mistralai). Hỗ trợ sinh câu hỏi trắc nghiệm từ chủ đề (topic), cấp độ khó (easy, medium, hard), số lượng câu hỏi và ngôn ngữ. Có sẵn cơ chế mock fallback khi chưa có API key.
- **Frontend Compatibility**: Kế thừa mẫu `CamelModel` từ P-131 để tự động serialize JSON sang `camelCase` cho frontend Next.js 16.
- **Data Persistence & Testing**:
  - Hỗ trợ cả **SQL Async** (PostgreSQL qua `asyncpg` hoặc SQLite async qua `aiosqlite` để chạy local tức thì) và **In-Memory Repository** (phục vụ unit test / dev mode không cần setup database).
  - Tự động chuyển đổi giữa SQL và In-Memory qua biến cấu hình `USE_IN_MEMORY_REPOS`.

---

## 2. Cấu trúc thư mục chi tiết

```
back-end/
├── src/
│   ├── api/                      # Tầng Controller (FastAPI Routing)
│   │   ├── deps.py               # Dependency Injection (Repository & Service Providers)
│   │   ├── routes.py             # Router tổng hợp gắn tiền tố /api/v1
│   │   ├── health.py             # Health check & database connection ping
│   │   ├── quizzes.py            # CRUD Quiz (danh sách, chi tiết, tạo, sửa, xóa)
│   │   ├── questions.py          # Quản lý câu hỏi và các lựa chọn đáp án
│   │   ├── attempts.py           # Bắt đầu làm bài, nộp bài, chấm điểm & xem kết quả
│   │   ├── ai.py                 # Endpoint sinh câu hỏi qua Mistral AI
│   │   └── leaderboard.py        # Thống kê kết quả & bảng xếp hạng các lượt thi
│   ├── config.py                 # Pydantic BaseSettings quản lý biến môi trường
│   ├── db/                       # Database Session & Base Declarative
│   │   ├── base.py               # Base class, UUID primary key, TimestampMixin, enum_column helper
│   │   ├── session.py            # Async engine, sessionmaker, lifespan DB hook
│   │   └── init_db.py            # Tạo bảng tự động & seed quiz mẫu
│   ├── models/                   # Schemas Pydantic & ORM Tables
│   │   ├── schemas.py            # CamelModel schemas (Quiz, Question, Option, Attempt, AI request/response)
│   │   └── tables/               # SQLAlchemy ORM Tables (quiz.py, question.py, attempt.py)
│   ├── repositories/             # Tầng Data Access
│   │   ├── base.py               # Interface trừu tượng (QuizRepository, AttemptRepository)
│   │   ├── sql.py                # Triển khai async SQLAlchemy
│   │   ├── memory.py             # Triển khai In-Memory cho test/dev
│   │   └── __init__.py           # Factory provider tráo đổi repository theo cấu hình
│   ├── services/                 # Tầng Business Logic (Thuần Python)
│   │   ├── ai/                   # Module Mistral AI Quiz Generation
│   │   │   ├── mistral_client.py # Khởi tạo Mistral client & mock fallback
│   │   │   ├── prompts.py        # Prompt sinh đề trắc nghiệm chuẩn cấu trúc JSON
│   │   │   └── generator.py      # AI Quiz Generator service
│   │   ├── quiz_service.py       # Nghiệp vụ quản lý quiz, câu hỏi, lựa chọn
│   │   └── attempt_service.py    # Nghiệp vụ chấm điểm tự động, tính tỷ lệ đúng và thời gian
│   ├── main.py                   # FastAPI app factory, lifespan, CORS, middleware
│   └── tests/                    # Async Pytest suite
├── .env.example                  # File mẫu cấu hình môi trường
├── requirements.txt              # Danh sách thư viện
└── README.md                     # Hướng dẫn chạy và tài liệu API
```

---

## 3. Mô hình Dữ liệu (Domain Entities & Schemas)

### 3.1. Bảng cơ sở dữ liệu (`models/tables/`)
- **Quiz**:
  - `id`: UUID (Primary Key)
  - `title`: String(255)
  - `description`: Text
  - `category`: String(100)
  - `difficulty`: String(50) — `easy`, `medium`, `hard`
  - `time_limit_minutes`: Integer (default: 15)
  - `author_name`: String(100) (default: "Nội bộ")
  - `is_published`: Boolean (default: True)
  - `created_at`, `updated_at`: DateTime(timezone=True)
- **Question**:
  - `id`: UUID (Primary Key)
  - `quiz_id`: UUID (Foreign Key -> Quiz)
  - `question_text`: Text
  - `question_type`: String(32) — `single_choice`, `multiple_choice`
  - `points`: Integer (default: 10)
  - `order_num`: Integer (thứ tự câu)
  - `explanation`: Text (giải thích đáp án)
- **Option**:
  - `id`: UUID (Primary Key)
  - `question_id`: UUID (Foreign Key -> Question)
  - `option_text`: Text
  - `is_correct`: Boolean
  - `order_num`: Integer
- **Attempt**:
  - `id`: UUID (Primary Key)
  - `quiz_id`: UUID (Foreign Key -> Quiz)
  - `participant_name`: String(100)
  - `score`: Integer (điểm đạt được)
  - `max_score`: Integer (tổng điểm tối đa của đề)
  - `percentage`: Float (phần trăm điểm, ví dụ 85.5%)
  - `status`: String(32) — `in_progress`, `completed`
  - `started_at`, `completed_at`: DateTime(timezone=True)
- **AttemptAnswer**:
  - `id`: UUID (Primary Key)
  - `attempt_id`: UUID (Foreign Key -> Attempt)
  - `question_id`: UUID (Foreign Key -> Question)
  - `selected_option_ids`: JSON (danh sách ID lựa chọn)
  - `is_correct`: Boolean
  - `earned_points`: Integer

---

## 4. Thiết kế Module AI Quiz Generator (`Mistral AI`)

### 4.1. Cấu hình (`config.py`)
- `mistral_api_key`: Chuỗi API key lấy từ Mistral Console.
- `mistral_model`: Mặc định `mistral-small-latest` (hoặc `open-mistral-7b`, `mistral-large-latest`).
- `mistral_temperature`: Mặc định `0.3` (giữ câu hỏi và đáp án chính xác, chuẩn mực).

### 4.2. Luồng sinh đề (`services/ai/generator.py`)
1. **Input**:
   - `topic`: Chủ đề bài thi (ví dụ: "Lập trình Python căn bản", "Quy trình DevOps nội bộ").
   - `num_questions`: Số lượng câu hỏi cần sinh (mặc định 5, từ 1 đến 20).
   - `difficulty`: `easy`, `medium`, `hard`.
   - `language`: `vi` hoặc `en`.
   - `content_source`: Đoạn văn bản/tài liệu mẫu (tùy chọn) để AI dựa vào đó sinh câu hỏi.
2. **Xử lý LLM**:
   - Sử dụng prompt ép chặt output JSON:
     ```json
     {
       "title": "...",
       "description": "...",
       "questions": [
         {
           "questionText": "...",
           "questionType": "single_choice",
           "points": 10,
           "explanation": "...",
           "options": [
             {"optionText": "...", "isCorrect": false},
             {"optionText": "...", "isCorrect": true}
           ]
         }
       ]
     }
     ```
3. **Chế độ Mock thông minh**:
   - Nếu chưa cấu hình `MISTRAL_API_KEY` (hoặc đang chạy test), service tự động sinh bộ câu hỏi mock theo đúng chủ đề yêu cầu mà không báo lỗi 500, giúp dev frontend và test chức năng tức thời.
4. **Lưu trữ**:
   - Có cờ `save_immediately: bool`. Nếu `True`, tự động lưu quiz vào DB qua `QuizRepository`. Nếu `False`, chỉ trả về JSON để người dùng duyệt/chỉnh sửa trên UI trước khi bấm tạo.

---

## 5. API Endpoints (`/api/v1`)

| Phương thức | Đường dẫn | Chức năng |
|---|---|---|
| `GET` | `/api/v1/health` | Kiểm tra trạng thái server & kết nối DB |
| `GET` | `/api/v1/quizzes` | Lấy danh sách quiz (có lọc theo category, search) |
| `POST` | `/api/v1/quizzes` | Tạo mới quiz thủ công |
| `GET` | `/api/v1/quizzes/{id}` | Lấy chi tiết quiz & toàn bộ câu hỏi/lựa chọn |
| `PUT` | `/api/v1/quizzes/{id}` | Cập nhật thông tin quiz |
| `DELETE` | `/api/v1/quizzes/{id}` | Xóa quiz |
| `POST` | `/api/v1/quizzes/{id}/questions` | Thêm câu hỏi vào quiz |
| `DELETE` | `/api/v1/questions/{id}` | Xóa câu hỏi |
| `POST` | `/api/v1/ai/generate-quiz` | Sinh quiz tự động bằng Mistral AI |
| `POST` | `/api/v1/attempts/start` | Bắt đầu một lượt làm bài cho participant |
| `POST` | `/api/v1/attempts/{id}/submit` | Nộp bài làm, tự động chấm điểm và trả kết quả |
| `GET` | `/api/v1/attempts/{id}` | Xem chi tiết kết quả lượt làm bài |
| `GET` | `/api/v1/quizzes/{id}/leaderboard` | Xem bảng xếp hạng điểm của một quiz |

---

## 6. Kế hoạch Kiểm thử & Xác thực

1. **Unit & Integration Tests (`tests/`)**:
   - Test `QuizRepository` (với InMemory mode).
   - Test `AttemptService` (chấm điểm đúng, tính thời gian, tính tỷ lệ %).
   - Test `QuizGeneratorService` (parse JSON, mock fallback).
   - Test FastAPI Endpoints qua `httpx.AsyncClient`.
2. **Chạy thử nghiệm Server**:
   - Khởi động uvicorn server ở port 8000.
   - Gọi endpoint `/api/v1/health` và `/api/v1/ai/generate-quiz`.
