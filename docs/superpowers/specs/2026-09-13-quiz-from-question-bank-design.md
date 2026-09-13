# Design Specification: Tạo Đề Thi Từ Thư Viện Câu Hỏi (Question Bank) — Áp dụng TDD

## 1. Tổng quan & Mục tiêu

Hệ thống bổ sung luồng tạo đề thi trực tiếp từ **Ngân hàng câu hỏi (Question Bank)** đã lưu, không bắt buộc phải đi qua quy trình quét OCR:
1. **Trang Ngân hàng câu hỏi riêng biệt (`/bank`):**
   - Quản lý toàn bộ câu hỏi trong kho: tìm kiếm theo từ khóa, lọc theo môn học/danh mục, lọc theo độ khó, xem trước đáp án/lời giải, chỉnh sửa (`PUT`) và xóa (`DELETE`).
   - Hỗ trợ chọn thủ công câu hỏi bằng checkbox kèm thanh công cụ nổi (**Floating Action Bar**) ở đáy màn hình: *"Đã chọn X câu"* $\rightarrow$ *"Tạo đề thi"*.
   - Hỗ trợ sinh đề tự động bằng **Ma trận tiêu chí (Matrix Generator)**: Cấu hình môn học, số lượng câu Dễ / Trung bình / Khó $\rightarrow$ Hệ thống bốc ngẫu nhiên từ kho, cảnh báo rõ ràng nếu thiếu câu và chuyển tiếp sang trang biên tập.
2. **Trang Biên tập đề thi toàn màn hình (`/create/from-bank`):**
   - Nạp các câu hỏi đã chọn hoặc vừa bốc ngẫu nhiên vào `QuizEditor` toàn màn hình.
   - Cho phép người dùng xem xét, tinh chỉnh tên đề, thời gian làm bài, điểm số, thứ tự câu hỏi, thêm câu hỏi thủ công hoặc nhặt thêm câu hỏi từ kho.
   - Lưu & Xuất bản đề thi độc lập thông qua API `POST /api/v1/quizzes` và chuyển hướng tới phòng thi `/quiz/{quizId}`.
3. **Quy trình phát triển:** Tuân thủ nghiêm ngặt **TDD (Test-Driven Development)**:
   - Viết test trước cho repository và API backend (Red) $\rightarrow$ Viết code tối giản để vượt qua test (Green) $\rightarrow$ Tối ưu hóa (Refactor).

---

## 2. Mô hình Dữ liệu & Backend Architecture

### 2.1. Pydantic Schemas mới (`back-end/src/models/schemas.py`)
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

### 2.2. Backend Repository & Service (`SqlBankRepository` & `BankService`)
Thêm phương thức `sample_by_matrix`:
```python
async def sample_by_matrix(
    self,
    category: str | None,
    easy_count: int,
    medium_count: int,
    hard_count: int,
) -> tuple[list[BankQuestionTable], list[str]]:
```
- **Chiến lược truy vấn & Chống N+1:**
  - Với mỗi mức độ khó (`easy`, `medium`, `hard`):
    - Dùng `select(BankQuestionTable).options(selectinload(BankQuestionTable.options)).where(BankQuestionTable.difficulty == level)`.
    - Nếu `category` có giá trị, thêm `.where(BankQuestionTable.category == category)`.
    - Sắp xếp ngẫu nhiên bằng `func.random()` và giới hạn số lượng bằng `.limit(count)`.
  - Kiểm tra số lượng thực tế lấy được:
    - Nếu `len(results) < count`: Thêm cảnh báo vào `warnings`, ví dụ:
      `"Mức độ 'Khó': Kho chỉ có 3 câu (yêu cầu 5 câu), đã lấy toàn bộ 3 câu."`
  - Gộp danh sách câu hỏi và trả về `(questions, warnings)`.

### 2.3. REST Endpoint mới (`back-end/src/api/bank.py`)
- `POST /api/v1/bank/matrix-generate`
  - Body: `BankMatrixGenerateRequest`
  - Response: `BankMatrixGenerateResponse` (status 200 OK)

---

## 3. Thiết kế Frontend & Giao diện Người dùng

### 3.1. Cập nhật Điều hướng (`Navbar.tsx`)
- Bổ sung nút/liên kết **"Ngân hàng câu hỏi"** (`/bank`) trên thanh Navbar để người dùng có thể truy cập kho từ mọi trang.

### 3.2. Trang Ngân hàng câu hỏi (`/bank/page.tsx`)
- **Header:**
  - Tiêu đề "Ngân hàng câu hỏi", hiển thị tổng số câu hiện có trong kho.
  - Nút chính nổi bật: **"Tạo đề theo Ma trận"** (mở `MatrixGenerateModal`).
- **Thanh công cụ lọc (Filter Toolbar):**
  - Ô tìm kiếm text (debounced 300ms).
  - Dropdown lọc theo Danh mục/Môn học (`GET /api/v1/bank/categories`).
  - Dropdown lọc theo Độ khó (`easy`, `medium`, `hard`).
- **Danh sách câu hỏi:**
  - Hỗ trợ checkbox chọn từng câu hoặc chọn tất cả câu hỏi hiển thị trên trang hiện tại.
  - Hiển thị badge môn học, badge độ khó, nút mở rộng xem đáp án và giải thích chi tiết.
  - Nút sửa (mở modal chỉnh sửa câu hỏi) và nút xóa (xác nhận và gọi API xóa).
  - Phân trang server-side.
- **Thanh tác vụ nổi (Floating Action Bar):**
  - Hiển thị cố định ở chân trang khi số câu chọn $\ge 1$.
  - Hiển thị: *"Đã chọn **X** câu hỏi"*.
  - Nút "Bỏ chọn" và nút hành động chính: **"Tạo đề thi từ X câu đã chọn"** $\rightarrow$ Lưu danh sách vào `sessionStorage` (`quiz_bank_staging`) và chuyển hướng sang `/create/from-bank`.

### 3.3. Modal Sinh đề theo Ma trận (`MatrixGenerateModal.tsx`)
- Lựa chọn danh mục môn học (hoặc "Tất cả môn học").
- Bộ cấu hình số câu hỏi Dễ, Trung bình, Khó (kèm bộ đếm số +/-).
- Tự động hiển thị tổng số câu hỏi dự kiến.
- Khi nhấn "Sinh đề thi":
  - Gọi API `POST /api/v1/bank/matrix-generate`.
  - Hiển thị cảnh báo nếu có `warnings`.
  - Lưu danh sách câu hỏi vào `sessionStorage` (`quiz_bank_staging`) và chuyển hướng sang `/create/from-bank`.

### 3.4. Trang Biên tập đề thi từ kho (`/create/from-bank/page.tsx`)
- Toàn màn hình (tương tự Bước 4 của Studio).
- Khôi phục dữ liệu từ `sessionStorage`:
  - Chuyển đổi `BankQuestionSchema[]` sang `QuestionEdit[]` nạp vào `QuizEditor`.
  - Nếu `sessionStorage` rỗng: Hiển thị Empty State kèm nút quay lại `/bank`.
- Tận dụng `QuizEditor`:
  - Đặt tiêu đề, mô tả, môn học, thời gian làm bài.
  - Kéo thả/mũi tên đổi thứ tự câu hỏi, sửa nội dung/đáp án/giải thích/điểm số.
  - Nút `+ Thêm từ Thư viện` (mở `QuestionBankPickerModal`) để chọn thêm câu hỏi từ kho.
  - Nút `+ Tự tạo câu hỏi mới` để viết thêm câu hỏi thủ công.
  - Nút **"Lưu & Xuất bản đề thi"**: Gọi `POST /api/v1/quizzes` $\rightarrow$ Xóa staging $\rightarrow$ Điều hướng tới `/quiz/{quizId}`.

---

## 4. Kế hoạch Thực hiện theo TDD (Test-Driven Development)

### Giai đoạn 1: Backend TDD
1. **Red:** Viết test trong `tests/test_bank_matrix.py`:
   - Test bốc câu hỏi theo ma trận khi kho có đủ câu.
   - Test xử lý khi kho không đủ câu hỏi theo độ khó (bốc tối đa + kiểm tra thông báo cảnh báo).
   - Test lọc ma trận kết hợp môn học (`category`).
   - Test chống N+1 queries khi nạp options.
   - Test endpoint `POST /api/v1/bank/matrix-generate`.
2. **Green:**
   - Triển khai `BankMatrixGenerateRequest` và `BankMatrixGenerateResponse` trong `schemas.py`.
   - Triển khai `sample_by_matrix` trong `SqlBankRepository` và `BankService`.
   - Triển khai router endpoint `POST /api/v1/bank/matrix-generate` trong `api/bank.py`.
   - Chạy test cho đến khi 100% test case Green.
3. **Refactor:** Tối ưu hóa code và kiểm tra type hint.

### Giai đoạn 2: Frontend Client & Components
1. Bổ sung `generateBankMatrix` vào `front-end/src/lib/api-client.ts` và types liên quan trong `types.ts`.
2. Tạo component `MatrixGenerateModal.tsx`.
3. Tạo trang `front-end/src/app/bank/page.tsx` với bộ lọc, checkbox, floating action bar, modal sửa câu hỏi và modal ma trận.
4. Cập nhật `Navbar.tsx` bổ sung liên kết tới `/bank`.
5. Tạo trang `front-end/src/app/create/from-bank/page.tsx` tích hợp `QuizEditor` và quản lý staging.

### Giai đoạn 3: E2E Verification
1. Chạy toàn bộ test backend với `pytest`.
2. Kiểm tra giao diện người dùng:
   - Truy cập `/bank`, xem danh sách câu hỏi.
   - Thử nghiệm sinh đề tự động bằng modal ma trận.
   - Thử nghiệm tích chọn 2-3 câu lẻ $\rightarrow$ bấm tạo đề thi.
   - Hoàn tất xuất bản đề thi tại `/create/from-bank` và kiểm tra vào phòng thi `/quiz/{quizId}`.
