# Quiz Web Backend

Hệ thống backend cho dự án **Quiz Web** được thiết kế theo mô hình **Clean Architecture 3 lớp** chuẩn mực kế thừa từ dự án AI20K (`P-131`), tích hợp module bóc tách hình ảnh bằng **RapidOCR** và sinh đề thi trắc nghiệm thông minh qua **Mistral AI** (`mistral-large-2512` / `mistral-small-2603`).

---

## 1. Kiến trúc Hệ thống (3-Tier Layered Architecture)

Dự án áp dụng nguyên tắc phụ thuộc một chiều nghiêm ngặt:

```
[ Next.js Frontend ] (port 3000)
        │
        ▼ HTTP (JSON format: camelCase qua CamelModel)
[ API Layer: src/api/ ]
  - Routes (/api/v1/health, /api/v1/quizzes, /api/v1/attempts, /api/v1/ai)
  - Dependency Injection (src/api/deps.py)
  - Input Validation & Error Handling
        │
        ▼ Constructor Injection
[ Service Layer: src/services/ ]
  - QuizService: Quản lý nghiệp vụ đề thi, câu hỏi và đáp án
  - AttemptService: Quản lý làm bài, thuật toán chấm điểm tự động và tính bảng xếp hạng
  - AIService: RapidOCR xử lý ảnh + Mistral AI Generator theo mức nhiệt độ temperature
        │
        ▼ Abstract Contracts (src/repositories/base.py)
[ Repository Layer: src/repositories/ ]
  - base.py: Interface trừu tượng (ABC)
  - sql.py: Triển khai SQLAlchemy Async (hỗ trợ SQLite và PostgreSQL)
  - memory.py: In-Memory test double (chạy unit test độc lập không cần DB)
  - __init__.py: Provider factory tự động chuyển đổi qua cấu hình `USE_IN_MEMORY_REPOS`
        │
        ▼
[ Storage Layer: src/db/ & src/models/tables/ ]
```

---

## 2. Điểm nổi bật & Tính năng cốt lõi

1. **OCR Ảnh + Mistral AI theo Temperature**:
   - Tải file ảnh chụp đề thi (PNG, JPG, WEBP) qua endpoint `POST /api/v1/ai/generate-from-image`.
   - **`temperature = 0.0` (Trích xuất nguyên văn)**: Yêu cầu LLM bám sát 100% câu chữ, đáp án từ ảnh.
   - **`temperature > 0.0` (Biên tập thông minh)**: Sửa lỗi chính tả OCR, trau chuốt câu từ nhưng bảo toàn 100% tính đúng đắn của kiến thức.
   - **Mock Generator Fallback**: Khi chưa cấu hình `MISTRAL_API_KEY`, hệ thống tự động sinh bộ câu hỏi mock chất lượng cao để test UI liền mạch mà không bị lỗi 500.
2. **Thân thiện với Frontend Next.js 16**:
   - Dùng Pydantic `CamelModel`: Code Python dùng `snake_case`, nhưng JSON trả về tự động là `camelCase` (ví dụ: `timeLimitMinutes`, `participantName`, `numQuestions`).
3. **Môi trường sử dụng nội bộ**:
   - Không yêu cầu token/JWT hay màn hình đăng nhập phức tạp.

---

## 3. Cài đặt & Khởi chạy

### 3.1. Cài đặt thư viện
```bash
cd back-end
pip install -r requirements.txt
```

### 3.2. Cấu hình môi trường (.env)
Tạo file `.env` từ `.env.example`:
```bash
cp .env.example .env
```
Các cấu hình quan trọng:
- `DATABASE_URL="sqlite+aiosqlite:///./quiz.db"` (mặc định) hoặc PostgreSQL `postgresql+asyncpg://user:password@localhost:5432/quizdb`
- `MISTRAL_API_KEY="your-mistral-api-key"`
- `MISTRAL_MODEL="mistral-large-2512"` (hoặc `mistral-small-2603`)
- `USE_IN_MEMORY_REPOS=false` (đổi thành `true` nếu muốn chạy hoàn toàn trên RAM)

### 3.3. Khởi tạo Database & Nạp dữ liệu mẫu
```bash
python -m src.db.init_db
```

### 3.4. Khởi chạy Server Backend
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```
- **Swagger UI Interactive Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/api/v1/health`

---

## 4. Kiểm thử Tự động (Testing)

Chạy toàn bộ test suite (18 tests kiểm thử toàn diện các tầng):
```bash
pytest tests/ -v
```

---

## 5. Danh sách API Endpoints (`/api/v1`)

| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/api/v1/health` | Kiểm tra trạng thái máy chủ và kết nối database |
| `GET` | `/api/v1/quizzes` | Lấy danh sách đề thi (hỗ trợ phân trang, lọc theo category, tìm kiếm) |
| `POST` | `/api/v1/quizzes` | Tạo mới đề thi thủ công |
| `GET` | `/api/v1/quizzes/{id}` | Lấy chi tiết đề thi kèm toàn bộ câu hỏi và đáp án |
| `PUT` | `/api/v1/quizzes/{id}` | Cập nhật đề thi |
| `DELETE` | `/api/v1/quizzes/{id}` | Xóa đề thi |
| `POST` | `/api/v1/quizzes/{id}/questions` | Thêm câu hỏi mới vào đề thi |
| `DELETE` | `/api/v1/questions/{id}` | Xóa câu hỏi khỏi đề thi |
| `POST` | `/api/v1/attempts/start` | Bắt đầu một lượt làm bài thi mới |
| `POST` | `/api/v1/attempts/{id}/submit` | Nộp bài làm, tự động chấm điểm và trả kết quả |
| `GET` | `/api/v1/attempts/{id}` | Xem chi tiết kết quả lượt thi |
| `GET` | `/api/v1/quizzes/{id}/leaderboard` | Xem bảng xếp hạng điểm của đề thi |
| `POST` | `/api/v1/ai/generate` | Sinh đề thi tự động bằng AI từ chủ đề hoặc văn bản |
| `POST` | `/api/v1/ai/generate-from-image` | Tải ảnh đề thi lên, OCR và sinh câu hỏi theo nhiệt độ |
