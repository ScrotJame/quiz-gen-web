# Thiết kế Kỹ thuật & Đánh giá Chi phí Backend Quiz Web (Kế thừa P-131)

**Ngày cập nhật:** 2026-09-12  
**Phiên bản:** 1.1  
**Mục tiêu:** Xây dựng hệ thống backend cho Quiz Web tại thư mục `back-end/` áp dụng Clean Architecture 3 lớp chuẩn mực từ `D:\VIN.AI\VIN_team_131\P-131\src`, tích hợp module OCR + AI Quiz Generation bằng **Mistral AI** (`mistral-large-2512` / `mistral-small-2603`), lược bỏ xác thực đăng nhập phục vụ nội bộ.

---

## 1. Đánh giá Chi phí Vận hành (Cost Estimation)

### 1.1. Chi phí Bản quyền & Hạ tầng
| Thành phần | Công nghệ | Chi phí | Ghi chú |
|---|---|:---:|---|
| **Backend Framework** | FastAPI + Uvicorn + Pydantic v2 | **0 VNĐ** | Mã nguồn mở (MIT) |
| **Data Storage** | SQLite Async (`aiosqlite`) / PostgreSQL | **0 VNĐ** | Chạy local / self-hosted không tốn phí |
| **Bộ giải mã OCR** | `rapidocr-onnxruntime` (ONNX thuần Python) | **0 VNĐ** | Chạy trực tiếp trên CPU server/máy tính, không mất phí API bên thứ 3 (như Google Vision / AWS Textract) |
| **Frontend Integration** | Next.js 16 (có sẵn trong `front-end`) | **0 VNĐ** | Chạy trực tiếp |

---

### 1.2. Chi phí API Mistral AI (Ước tính theo Token)

Đơn giá tham chiếu chính thức từ Mistral AI:
- **`mistral-large-2512`**: Input **$2.00 / 1M tokens** (~50 VNĐ) | Output **$6.00 / 1M tokens** (~150 VNĐ)
- **`mistral-small-2603`**: Input **$0.20 / 1M tokens** (~5 VNĐ) | Output **$0.60 / 1M tokens** (~15 VNĐ) *(Rẻ hơn 10 lần)*

#### Ước tính cụ thể cho 1 lần tạo đề Quiz (10 câu trắc nghiệm từ ảnh chụp):
- **Văn bản sau OCR gửi vào (Input)**: ~1.000 tokens (ảnh 1 trang tài liệu/đề thi).
- **Cấu trúc JSON Quiz trả về (Output)**: ~1.500 tokens (10 câu hỏi, 4 lựa chọn A/B/C/D, giải thích chi tiết).
- **Tổng chi phí trên mỗi lượt tạo đề**:
  - Với **`mistral-large-2512`**: `(1.000 * 2$ + 1.500 * 6$) / 1.000.000` = **$0.011 / đề** (**~280 VNĐ / đề**).
  - Với **`mistral-small-2603`**: `(1.000 * 0.2$ + 1.500 * 0.6$) / 1.000.000` = **$0.0011 / đề** (**~28 VNĐ / đề**).

#### Bảng tổng hợp chi phí hàng tháng (Môi trường Nội bộ):
| Số lượt sinh đề / tháng | Dùng `mistral-small-2603` | Dùng `mistral-large-2512` | Gateway nội bộ công ty (Self-hosted/Quota) |
|:---:|:---:|:---:|:---:|
| **100 đề / tháng** | ~2.800 VNĐ | ~28.000 VNĐ | **0 VNĐ** |
| **500 đề / tháng** | ~14.000 VNĐ | ~140.000 VNĐ | **0 VNĐ** |
| **2.000 đề / tháng** | ~56.000 VNĐ | ~560.000 VNĐ | **0 VNĐ** |

> **Nhận định**: Chi phí vận hành gần như bằng 0 đối với hạ tầng và cực kỳ nhỏ đối với token AI (dưới một bữa ăn sáng cho cả tháng sử dụng nội bộ).

---

## 2. Kiến trúc Hệ thống (3-Tier Clean Architecture)

Kế thừa nghiêm ngặt chuẩn mực phân tầng từ `P-131`:

```
                       ┌─────────────────────────────────────┐
                       │        Next.js Frontend (SPA)       │
                       │           (port 3000)               │
                       └──────────────────┬──────────────────┘
                                          │ HTTP (CamelModel JSON)
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ TẦNG 1: API LAYER (src/api/)                                                │
│ ├─ Router /api/v1 (health, quizzes, questions, attempts, ai, leaderboard)   │
│ ├─ Validation & Serialization (Pydantic schemas.py)                         │
│ └─ Dependency Injection (deps.py)                                           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ constructor injection
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ TẦNG 2: SERVICE LAYER (src/services/)                                       │
│ ├─ QuizService (Nghiệp vụ tạo/sửa quiz, kiểm soát dữ liệu)                  │
│ ├─ AttemptService (Nghiệp vụ làm bài, tự động chấm điểm, tính thời gian)    │
│ └─ AIService (OCR qua RapidOCR + Mistral LLM Generator)                     │
│    ├─ temperature = 0.0: Giữ nguyên 100% câu chữ từ ảnh OCR                 │
│    └─ temperature > 0.0: Cho phép tinh chỉnh văn phong, bảo toàn chân lý    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ abstract contracts
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ TẦNG 3: REPOSITORY LAYER (src/repositories/)                                │
│ ├─ base.py: Abstract Repository Contracts (ABC)                             │
│ ├─ sql.py: SQLAlchemy Async Repository (Postgres / aiosqlite)               │
│ ├─ memory.py: In-Memory Repository (Test double cho Pytest)                 │
│ └─ __init__.py: Provider Factory tự tráo đổi theo config                    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ DATABASE & STORAGE (src/db/)                                                │
│ ├─ AsyncEngine + AsyncSession (session.py)                                  │
│ └─ Declarative Base + Tables (models/tables/)                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Cấu trúc Thư mục Chi tiết `back-end/`

```
back-end/
├── src/
│   ├── api/
│   │   ├── deps.py               # Dependency Injection (FastAPI Depends)
│   │   ├── routes.py             # Router tổng hợp đăng ký vào /api/v1
│   │   ├── health.py             # GET /api/v1/health (ping DB)
│   │   ├── quizzes.py            # CRUD Quiz: GET/POST/PUT/DELETE
│   │   ├── questions.py          # Quản lý câu hỏi & đáp án
│   │   ├── attempts.py           # Start attempt, submit answer, finish attempt
│   │   ├── ai.py                 # POST /api/v1/ai/generate (từ text & upload ảnh)
│   │   └── leaderboard.py        # Thống kê điểm số & bảng thành tích
│   ├── config.py                 # Pydantic BaseSettings (.env, DB, Mistral Key)
│   ├── db/
│   │   ├── base.py               # Base class, UUID pk, Timestamps, enum_column helper
│   │   ├── session.py            # async_engine, async_sessionmaker, lifespan startup
│   │   └── init_db.py            # Khởi tạo tables & seed đề mẫu
│   ├── models/
│   │   ├── schemas.py            # CamelModel Pydantic schemas (JSON camelCase)
│   │   └── tables/               # SQLAlchemy ORM Tables (quiz, question, option, attempt)
│   ├── repositories/
│   │   ├── base.py               # Abstract Base Classes (ABC)
│   │   ├── sql.py                # Triển khai async SQLAlchemy
│   │   ├── memory.py             # Triển khai In-Memory cho test
│   │   └── __init__.py           # Provider functions
│   ├── services/
│   │   ├── ai/
│   │   │   ├── ocr.py            # Module RapidOCR xử lý ảnh chụp đề thi sang text
│   │   │   ├── mistral_client.py # Client kết nối Mistral AI (`mistral-large-2512`)
│   │   │   ├── prompts.py        # Prompt kỹ thuật bám sát temperature = 0 và > 0
│   │   │   └── generator.py      # AI Quiz Generator orchestrator
│   │   ├── quiz_service.py       # Quản lý đề thi & câu hỏi
│   │   └── attempt_service.py    # Chấm điểm tự động & xếp hạng
│   ├── main.py                   # FastAPI app, lifespan, CORS, error handlers
│   └── tests/                    # Pytest suite async
├── .env.example                  # Mẫu cấu hình môi trường chuẩn
├── requirements.txt              # Danh sách thư viện cần thiết
└── README.md                     # Hướng dẫn chạy và tài liệu API
```

---

## 4. Đặc tả API Endpoints

| Phương thức | Đường dẫn | Tham số chính | Chức năng |
|---|---|---|---|
| `GET` | `/api/v1/health` | — | Kiểm tra trạng thái server & DB |
| `GET` | `/api/v1/quizzes` | `category`, `search`, `limit`, `offset` | Lấy danh sách đề thi |
| `POST` | `/api/v1/quizzes` | `CreateQuizRequest` | Tạo đề thi thủ công |
| `GET` | `/api/v1/quizzes/{id}` | — | Lấy chi tiết đề thi (kèm câu hỏi & đáp án) |
| `PUT` | `/api/v1/quizzes/{id}` | `UpdateQuizRequest` | Cập nhật đề thi |
| `DELETE` | `/api/v1/quizzes/{id}` | — | Xóa đề thi |
| `POST` | `/api/v1/ai/generate` | `topic`, `content`, `numQuestions`, `difficulty`, `temperature` | Sinh đề từ chủ đề / văn bản |
| `POST` | `/api/v1/ai/generate-from-image` | `file` (ảnh), `numQuestions`, `temperature`, `saveImmediately` | **OCR ảnh + LLM sinh đề theo temperature** |
| `POST` | `/api/v1/attempts/start` | `quizId`, `participantName` | Bắt đầu lượt làm bài thi |
| `POST` | `/api/v1/attempts/{id}/submit` | `SubmitAttemptRequest` (các câu trả lời) | Nộp bài, tự động chấm điểm ngay lập tức |
| `GET` | `/api/v1/attempts/{id}` | — | Xem chi tiết bài làm đã chấm |
| `GET` | `/api/v1/quizzes/{id}/leaderboard` | `limit` | Xem bảng xếp hạng của đề thi |

---

## 5. Kế hoạch Triển khai & Xác thực (Verification)

1. **Khởi tạo môi trường & dependencies**:
   - `requirements.txt` với FastAPI, uvicorn, pydantic v2, sqlalchemy asyncio, aiosqlite/asyncpg, rapidocr-onnxruntime, mistralai, pytest.
2. **Triển khai tuần tự theo 3 lớp**:
   - `config.py` & `db/` (Session & Base)
   - `models/` (Tables & CamelModel Schemas)
   - `repositories/` (Base ABC, In-Memory, SQL Async, Factory Provider)
   - `services/` (Quiz, Attempt chấm điểm, AI OCR + Mistral)
   - `api/` (Deps, Routes, Endpoints)
   - `main.py` (CORS Next.js, Lifespan, Exceptions)
3. **Kiểm thử tự động & khởi chạy**:
   - Chạy Pytest kiểm thử unit test cho luồng chấm điểm và CRUD quiz.
   - Khởi động server backend và kiểm tra qua healthcheck.
