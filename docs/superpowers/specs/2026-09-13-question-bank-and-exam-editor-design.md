# Design Specification: Question Bank & Exam Editor (Áp dụng TDD)

## 1. Tổng quan & Mục tiêu

Hệ thống bổ sung luồng tách biệt giữa **Ngân hàng câu hỏi (Question Bank)** và **Biên tập đề thi (Exam Editor)** trong OCR Studio:
1. Sau khi quét OCR và chuẩn hóa văn bản, người dùng có thể bóc tách các câu hỏi và xem màn hình **"Duyệt & Lưu Thư viện câu hỏi"**.
2. Người dùng chỉnh sửa, gắn nhãn danh mục/độ khó và lưu toàn bộ câu hỏi vào kho chung thông qua batch insert (tối ưu chống N+1).
3. Sau khi lưu thành công vào thư viện, hệ thống chuyển tiếp sang màn hình **"Biên tập đề thi"**:
   - Tự động nạp sẵn các câu hỏi vừa lưu từ thư viện (theo cơ chế **sao chép độc lập - snapshot**).
   - Cho phép mở modal **"+ Thêm từ Thư viện"** để tra cứu và tích chọn thêm câu hỏi từ toàn bộ kho trong hệ thống.
   - Cho phép **"+ Tự tạo câu hỏi mới"** để viết câu hỏi thủ công trực tiếp vào đề thi.
   - Tùy chỉnh thông tin đề thi và lưu thành đề thi hoàn chỉnh độc lập.
4. Quá trình phát triển tuân thủ nghiêm ngặt **TDD (Test-Driven Development)**: Viết test trước (Red) -> Viết code tối giản để vượt qua test (Green) -> Tối ưu hóa/Refactor.

---

## 2. Mô hình Dữ liệu (Database Schema & Anti-N+1 Strategy)

### 2.1. Bảng cơ sở dữ liệu mới (Backend SQLAlchemy)
Tạo 2 bảng mới độc lập trong `back-end/src/models/tables/`:

#### `BankQuestionTable` (`bank_questions`):
- `id`: UUID (Khóa chính, tự sinh `uuid.uuid4`)
- `question_text`: Text (Nội dung câu hỏi)
- `question_type`: Enum (`QuestionType`: `single_choice`, `multiple_choice`, `true_false`)
- `category`: String (Chủ đề / Môn học, indexed)
- `difficulty`: String / Enum (`easy`, `medium`, `hard`, default: `medium`)
- `explanation`: Text (nullable, Lời giải thích)
- `source_note`: String (nullable, ví dụ: "OCR từ bộ tài liệu A")
- `created_at`: DateTime (Timestamp UTC)
- `updated_at`: DateTime (Timestamp UTC)
- Relationship `options`: `list[BankOptionTable]` (cascade="all, delete-orphan", lazy="selectin")

#### `BankOptionTable` (`bank_options`):
- `id`: UUID (Khóa chính)
- `question_id`: UUID (Foreign Key trỏ tới `bank_questions.id`, ondelete="CASCADE", indexed)
- `option_text`: Text (Nội dung đáp án)
- `is_correct`: Boolean (True nếu là đáp án đúng)
- `order_num`: Integer (Thứ tự hiển thị 1, 2, 3...)
- Relationship `question`: trỏ về `BankQuestionTable`

### 2.2. Chiến lược Tối ưu hóa Chống N+1 (Anti-N+1 Query & Batch Insert)
- **Batch Insert (Ghi):**
  - Endpoint `POST /api/v1/bank/questions/batch` nhận danh sách `list[BankQuestionCreate]`.
  - Sinh sẵn `UUID` cho từng câu hỏi và gán `question_id` cho các options tương ứng.
  - Sử dụng `session.add_all()` cho cả câu hỏi và các options, thực thi trong duy nhất **1 database transaction** (`session.begin()`).
- **Batch Query (Đọc):**
  - Khi truy vấn danh sách câu hỏi trong ngân hàng (`GET /api/v1/bank/questions`), sử dụng `selectinload(BankQuestionTable.options)` của SQLAlchemy 2.0.
  - Đảm bảo câu lệnh SQL chỉ sinh ra chính xác 2 queries:
    1. Query 1: Lấy danh sách câu hỏi theo phân trang (`LIMIT ... OFFSET ...`).
    2. Query 2: Lấy toàn bộ options thuộc danh sách câu hỏi đó (`WHERE question_id IN (...)`).
  - Triệt tiêu 100% lỗi N+1 query.

---

## 3. Kiến trúc API Contracts (Pydantic Schemas)

### 3.1. Schemas
- `BankOptionCreate`: `{ option_text: str, is_correct: bool, order_num: int }`
- `BankOptionSchema`: `{ id: UUID, question_id: UUID, option_text: str, is_correct: bool, order_num: int }`
- `BankQuestionCreate`: `{ question_text: str, question_type: QuestionType, category: str, difficulty: str, explanation: str | None, source_note: str | None, options: list[BankOptionCreate] }`
- `BankQuestionBatchCreate`: `{ questions: list[BankQuestionCreate] }`
- `BankQuestionSchema`: `{ id: UUID, question_text: str, question_type: QuestionType, category: str, difficulty: str, explanation: str | None, source_note: str | None, created_at: datetime, updated_at: datetime, options: list[BankOptionSchema] }`
- `BankQuestionListResponse`: `{ items: list[BankQuestionSchema], total: int, page: int, limit: int }`
- `BankCategoriesResponse`: `{ categories: list[str] }`

### 3.2. REST Endpoints (`/api/v1/bank`)
- `POST /api/v1/bank/questions/batch`: Batch insert danh sách câu hỏi vào kho.
- `GET /api/v1/bank/questions`: Danh sách câu hỏi kèm bộ lọc (`category`, `difficulty`, `search`, `page`, `limit`).
- `GET /api/v1/bank/categories`: Danh sách các danh mục có trong kho.
- `GET /api/v1/bank/questions/{id}`: Chi tiết 1 câu hỏi trong kho.
- `PUT /api/v1/bank/questions/{id}`: Cập nhật 1 câu hỏi trong kho.
- `DELETE /api/v1/bank/questions/{id}`: Xóa 1 câu hỏi khỏi kho.

---

## 4. Thiết kế Frontend & Giao diện Studio 4 Bước

### 4.1. Quy trình Stepper tại `/create/ocr`:
- **Bước 1 (Quét ảnh):** Quét từng trang ảnh bằng OCR, hiển thị Filmstrip & SplitScreen.
- **Bước 2 (Chuẩn hóa & Bóc tách):** Gộp văn bản, làm sạch chính tả bằng AI, nhấn nút "Bóc tách câu hỏi".
- **Bước 3 (Duyệt & Lưu Thư viện - `BankReviewPanel`):**
  - Hiển thị danh sách câu hỏi trích xuất được.
  - Cho phép chỉnh sửa câu hỏi/đáp án/giải thích/danh mục chung.
  - Nút **"Lưu vào Thư viện câu hỏi"** (gọi batch API).
  - Khóa chuyển tiếp sang Bước 4 chỉ mở sau khi đã lưu thành công vào Thư viện.
- **Bước 4 (Biên tập đề thi - `QuizEditor` nâng cấp):**
  - Tự động nạp sẵn các câu hỏi vừa lưu (clone sang dạng `QuestionEdit`).
  - Thanh công cụ có thêm 2 nút:
    1. **`+ Thêm từ Thư viện`**: Mở modal `QuestionBankPickerModal` hỗ trợ tìm kiếm, lọc theo môn học, tích chọn và copy vào đề thi.
    2. **`+ Tự tạo câu hỏi mới`**: Thêm một form câu hỏi trống để nhập tay.
  - Lưu đề thi độc lập thông qua API `POST /api/v1/quizzes`.

### 4.2. Khôi phục nháp (Draft Persistence):
- Cập nhật cấu trúc `SavedDraft` trong `localStorage` để lưu trữ trạng thái của cả 4 bước.

---

## 5. Kế hoạch Thực hiện theo Phương pháp TDD (Test-Driven Development)

### Giai đoạn 1: Backend TDD
1. **Test-First Tables & Repository:**
   - Viết `test_bank_repository.py`:
     - Test batch insert câu hỏi và options.
     - Test query phân trang, tìm kiếm và lọc danh mục.
     - Test xác nhận N+1 query không xảy ra (đếm số câu lệnh SQL sinh ra).
     - Test update và delete câu hỏi.
   - Triển khai `BankQuestionTable`, `BankOptionTable` và `SqlBankRepository` cho đến khi tất cả tests chuyển sang xanh (Green).
2. **Test-First API Endpoints:**
   - Viết `test_bank_api.py`:
     - Test endpoint `POST /api/v1/bank/questions/batch` với dữ liệu hợp lệ và không hợp lệ.
     - Test `GET /api/v1/bank/questions` với pagination và filter query params.
     - Test `GET /api/v1/bank/categories`.
     - Test `PUT` và `DELETE`.
   - Triển khai router `/api/v1/bank` và tích hợp vào FastAPI app cho đến khi tests chuyển sang xanh (Green).

### Giai đoạn 2: Frontend Client & Component TDD / Integration
1. Viết các hàm API client trong `lib/api-client.ts`: `batchCreateBankQuestions`, `getBankQuestions`, `getBankCategories`.
2. Tạo component `BankReviewPanel`: Cho phép duyệt, sửa, chọn danh mục và lưu batch.
3. Tạo modal `QuestionBankPickerModal`: Cho phép tìm kiếm câu hỏi trong kho và chọn đưa vào đề thi.
4. Cập nhật `QuizEditor` & Stepper trong `/create/ocr/page.tsx` từ 3 bước sang 4 bước.

### Giai đoạn 3: Kiểm thử End-to-End & Xác minh
- Chạy toàn bộ test suite backend bằng `pytest`.
- Kiểm tra luồng Studio: Quét ảnh mẫu -> Chuẩn hóa -> Lưu vào Bank -> Tạo đề thi (kết hợp câu hỏi ngân hàng + câu hỏi tự tạo) -> Lưu đề thi và vào phòng thi.
