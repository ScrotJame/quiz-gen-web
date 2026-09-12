# Thiết Kế Chi Tiết: Studio Quét Ảnh OCR Nhiều Trang & Tạo Đề Thi (Multi-page OCR Quiz Studio)

Tài liệu đặc tả kiến trúc, giao diện người dùng và luồng xử lý dữ liệu cho tính năng **Studio Quét Tài Liệu Nhiều Trang (Multi-page Document Scanner & Quiz Generator)**.

---

## 1. Mục tiêu & Phạm vi (Goals & Scope)

### 1.1. Mục tiêu
- Cung cấp một môi trường làm việc chuyên nghiệp (Studio) tại đường dẫn `/create/ocr` cho phép giáo viên, học sinh và người học chuyển đổi tập hợp các ảnh chụp đề thi (nhiều trang sách, slide bài giảng, đề cương ôn tập) thành bộ câu hỏi trắc nghiệm hoàn chỉnh.
- Xóa bỏ rào cản lớn nhất của OCR đơn lẻ: ảnh chụp nhiều trang bị đứt đoạn câu giữa trang, lỗi chính tả dấu tiếng Việt, chữ bị dính hoặc mờ.
- Cho phép người dùng duyệt, tinh chỉnh trực tiếp các câu hỏi do AI tạo ra (sửa đề, sửa đáp án, thêm/xóa câu) ngay trong Studio trước khi phát hành.

### 1.2. Phạm vi (In-Scope)
- **Giao diện Studio 3 bước (Stepper)**:
  1. *Quét & Đối chiếu tài liệu (Scan & Align)*: Quản lý dải thumbnail (Filmstrip), đối chiếu song song ảnh gốc và văn bản OCR (Split-screen).
  2. *Hợp nhất & Chuẩn hóa AI (Merge & AI Clean)*: Ghép nối các trang, công cụ AI tự động sửa lỗi chính tả và nối câu đứt đoạn.
  3. *Biên tập đề thi (Quiz Editor)*: Xem trước danh sách câu hỏi AI vừa sinh, chỉnh sửa toàn diện câu hỏi/đáp án/lời giải, lưu vào cơ sở dữ liệu.
- **Backend API**:
  - Endpoint OCR từng trang độc lập, chạy bất đồng bộ qua threadpool để hỗ trợ tải nhiều trang cùng lúc.
  - Endpoint AI làm sạch và sửa lỗi chính tả văn bản tiếng Việt.
  - Tích hợp pipeline sinh câu hỏi và lưu trữ đã có.

### 1.3. Ngoài phạm vi (Out-of-Scope)
- Không lưu trữ vĩnh viễn các file ảnh thô trên server (tuân thủ nguyên tắc stateless và bảo mật dữ liệu người dùng).
- Không yêu cầu người dùng phải đăng ký tài khoản mới được quét tài liệu.

---

## 2. Kiến trúc hệ thống & Luồng dữ liệu (Architecture & Data Flow)

### 2.1. Sơ đồ luồng xử lý (Data Flow Diagram)

```
[Người dùng tải N ảnh] 
         │
         ▼
[Frontend: Studio State (IndexedDB / memory)]
         │
         ├──(Song song từng trang)──► [POST /api/v1/ai/ocr-page] (FastAPI + RapidOCR)
         │                                      │
         │◄──(Trả về text & confidence)─────────┘
         │
         ▼ (Người dùng sắp xếp trang, đối chiếu ảnh/text)
[Gộp toàn bộ trang] ───────────────► [POST /api/v1/ai/clean-text] (Mistral AI)
         │                                      │
         │◄──(Văn bản liền mạch, chuẩn dấu)─────┘
         │
         ▼ (Chọn số câu, độ khó, chủ đề)
[Sinh câu hỏi AI] ─────────────────► [POST /api/v1/ai/generate] (Mistral AI Generator)
         │                                      │
         │◄──(Danh sách câu hỏi trắc nghiệm)────┘
         │
         ▼ (Người dùng tinh chỉnh trong Quiz Editor)
[Hoàn tất & Lưu] ──────────────────► [POST /api/v1/quizzes] (SQLite DB)
         │
         ├──► Điều hướng tới /quiz/[id] (Làm bài ngay)
         └──► Hoặc quay về / (Dashboard)
```

---

## 3. Đặc tả API Backend (API Contracts)

### 3.1. `POST /api/v1/ai/ocr-page`
Xử lý OCR cho từng trang ảnh đơn lẻ. Chạy qua `run_in_threadpool` của FastAPI để không block event loop.

- **Request**: `multipart/form-data`
  - `file`: `UploadFile` (ảnh PNG, JPG, JPEG, WEBP; dung lượng tối đa 10MB).
- **Xử lý**:
  - Đọc bytes ảnh, tiền xử lý qua OpenCV (nếu cần).
  - Gọi `rapidocr-onnxruntime` trích xuất danh sách các dòng kèm điểm tin cậy (confidence).
- **Response (`200 OK`)**:
  ```json
  {
    "text": "1. Khái niệm về phản ứng hoá học...\nA. Là quá trình biến đổi chất này thành chất khác.\nB...",
    "lineCount": 14,
    "averageConfidence": 0.94
  }
  ```
- **Error Response**:
  - `400 Bad Request`: Định dạng file không hợp lệ hoặc file rỗng.
  - `422 Unprocessable Entity`: Không nhận diện được văn bản nào trong ảnh (`NO_TEXT_FOUND`).

### 3.2. `POST /api/v1/ai/clean-text`
Sử dụng Mistral AI để chuẩn hóa văn bản sau khi gộp nhiều trang OCR.

- **Request (`application/json`)**:
  ```json
  {
    "rawText": "Văn bản thô ghép từ các trang...",
    "targetLanguage": "vi"
  }
  ```
- **Prompt Engineering**:
  - System Prompt: *"Bạn là trợ lý biên tập tài liệu giáo dục. Nhiệm vụ của bạn là nhận văn bản trích xuất từ OCR của nhiều trang sách, sửa các lỗi chính tả dấu tiếng Việt do OCR nhận nhầm, và nối liền các câu bị đứt đoạn giữa các trang. Tuyệt đối giữ nguyên nội dung, số liệu, tên riêng và cấu trúc câu hỏi nếu có. Không thêm bớt ý kiến cá nhân."*
- **Response (`200 OK`)**:
  ```json
  {
    "cleanedText": "Văn bản đã được sửa lỗi chính tả và nối câu hoàn chỉnh..."
  }
  ```

### 3.3. Tái sử dụng các API hiện có
- `POST /api/v1/ai/generate`: Nhận `cleanedText` để sinh ra cấu trúc `GeneratedQuizResponse`.
- `POST /api/v1/quizzes`: Nhận payload `QuizCreate` từ Quiz Editor để lưu đề thi chính thức vào DB.

---

## 4. Đặc tả Giao diện Người dùng (UI/UX Specification)

Trang Studio được đặt tại `front-end/src/app/create/ocr/page.tsx` với thiết kế giao diện theo chuẩn **UI/UX Pro Max**:

### 4.1. Header Studio
- Nút "Quay lại" (kèm popup xác nhận nếu chưa lưu).
- Stepper thanh tiến trình 3 bước trực quan:
  - **Bước 1: Quét tài liệu** (Upload & OCR)
  - **Bước 2: Chuẩn hóa nội dung** (AI Clean & Merge)
  - **Bước 3: Biên tập đề thi** (Quiz Editor)
- Huy hiệu lưu nháp tự động (`localStorage` draft).

### 4.2. Giai đoạn 1: Bố cục Filmstrip + Split Screen đối chiếu
- **Cột trái (Filmstrip - 280px)**:
  - Nút "+ Thêm trang ảnh" (hỗ trợ chọn nhiều file hoặc kéo thả).
  - Danh sách thumbnail các trang được đánh số thứ tự: `Trang 1`, `Trang 2`, `Trang 3`...
  - Mỗi thumbnail có:
    - Nút xoay 90° (để sửa ảnh chụp ngang/ngược).
    - Nút xóa trang.
    - Trạng thái: Đang quét (spinner), Hoàn thành (icon xanh), Lỗi (icon đỏ).
  - Nút "Đổi vị trí" (Lên / Xuống) để đảm bảo thứ tự mạch lạc của tài liệu.
- **Khu vực trung tâm (Split Screen - 50/50)**:
  - **Khung bên trái**: Xem ảnh phóng to của trang đang chọn, có nút Zoom In, Zoom Out, Reset kích thước.
  - **Khung bên phải**: Khung soạn thảo văn bản OCR trích xuất của trang đó. Cho phép người dùng chỉnh sửa trực tiếp nếu phát hiện sai sót.
  - Phía dưới là nút chuyển nhanh: `← Trang trước` và `Trang tiếp theo →`.
- **Thanh tác vụ dưới cùng**:
  - Thống kê: `Đã quét X/Y trang` • `Z từ`.
  - Nút chính: **"Tiếp tục: Chuẩn hóa tài liệu & Nối trang"** (chuyển sang Giai đoạn 2).

### 4.3. Giai đoạn 2: Hợp nhất & Chuẩn hóa AI (Merge & AI Clean)
- Hiển thị toàn bộ văn bản sau khi gộp N trang.
- Hộp công cụ AI:
  - Nút nổi bật: **"AI Sửa lỗi chính tả & Nối đoạn"** kèm hiệu ứng lấp lánh (Sparkles).
  - Khi kích hoạt, hiển thị thanh so sánh (Diff view hoặc Badge "Đã chuẩn hóa 12 lỗi chính tả và 3 đoạn nối").
- Bảng cấu hình đề thi:
  - Tiêu đề đề thi (AI tự đề xuất dựa vào nội dung).
  - Thể loại (Toán, Văn, Sử, Khoa học, Tiếng Anh, v.v.).
  - Số lượng câu hỏi muốn sinh: `3`, `5`, `10`, `15`, `20`.
  - Mức độ khó: `Dễ`, `Trung bình`, `Khó`.
  - Loại câu hỏi ưu tiên: `Chọn 1 đáp án` hoặc `Hỗn hợp`.
- Nút bấm chính: **"Sinh câu hỏi trắc nghiệm bằng AI"**.

### 4.4. Giai đoạn 3: Trình biên tập đề thi (Quiz Editor)
- Danh sách câu hỏi trắc nghiệm dạng thẻ (Card list):
  - Mỗi thẻ câu hỏi gồm:
    - Tiêu đề câu: Ô nhập text cho phép chỉnh sửa nội dung câu hỏi.
    - Điểm số: Mặc định 10 điểm (cho phép sửa).
    - Danh sách đáp án (A, B, C, D):
      - Ô text sửa nội dung từng đáp án.
      - Nút radio/checkbox chọn đáp án nào là **Đáp án đúng** (tô màu xanh nổi bật).
      - Nút xóa phương án hoặc thêm phương án E, F...
    - Ô nhập "Giải thích chi tiết" (`explanation`).
    - Nút xóa câu hỏi hoặc nhân bản câu hỏi.
  - Nút bấm **"+ Thêm câu hỏi mới"** ở cuối danh sách.
- Thanh hành động cố định ở chân trang (Sticky Footer):
  - Tổng số câu hỏi hiện tại.
  - Nút **"Lưu đề thi vào Thư viện"** (Lưu và về Dashboard).
  - Nút **"Lưu & Bắt đầu làm bài ngay"** (Lưu và chuyển hướng tới `/quiz/[quizId]`).

---

## 5. Xử lý Lỗi & Khả năng Phục hồi (Error Handling & Edge Cases)

1. **Ảnh quá mờ hoặc không có chữ**:
   - Hiển thị thông báo trên thumbnail trang: *"Không tìm thấy văn bản đủ rõ"*.
   - Cho phép người dùng chụp/tải lại ảnh riêng cho trang đó mà không làm mất các trang khác.
2. **Lỗi kết nối mạng khi tải nhiều ảnh**:
   - Cơ chế Retry độc lập cho từng trang (trang nào lỗi thì hiện nút "Quét lại" riêng trang đó).
3. **Mất dữ liệu khi tải lại trang**:
   - Lưu trữ nháp toàn bộ văn bản và thumbnail vào `localStorage` (`ocr_studio_draft`).
   - Khi vào lại `/create/ocr`, tự động hỏi: *"Bạn có muốn tiếp tục bản quét dở trước đó không?"*.
4. **Văn bản quá dài vượt token LLM**:
   - Backend tự động cắt chunk theo đoạn văn có ý nghĩa nếu tài liệu vượt quá 8.000 từ, sau đó ghép kết quả câu hỏi trắc nghiệm.

---

## 6. Kế hoạch Kiểm thử & Xác minh (Verification Plan)

### 6.1. Kiểm thử Backend (FastAPI Unit Tests)
- Tạo tệp `back-end/tests/test_ocr_studio.py`:
  - Test endpoint `POST /api/v1/ai/ocr-page` với ảnh mẫu (xác nhận trả về text, lineCount, confidence).
  - Test endpoint `POST /api/v1/ai/clean-text` với văn bản mẫu có ngắt câu và thiếu dấu.
  - Chạy toàn bộ test suite `pytest` bảo đảm 100% pass.

### 6.2. Kiểm thử Frontend (Next.js)
- Kiểm tra linter `npx eslint src/` bảo đảm không có lỗi code convention hay React hook warning.
- Kiểm tra production build `npm run build` xác nhận trang `/create/ocr` biên dịch chuẩn xác.
- Kiểm tra trực quan:
  - Tải 3 ảnh đề thi mẫu.
  - Kiểm tra dải Filmstrip, xoay ảnh và đối chiếu Split-screen.
  - Thử tính năng AI Clean Text và sinh đề.
  - Kiểm tra Quiz Editor chỉnh sửa câu hỏi và lưu thành công vào cơ sở dữ liệu.
