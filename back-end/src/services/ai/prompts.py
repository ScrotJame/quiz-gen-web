from __future__ import annotations

from src.models.schemas import Difficulty


def build_system_prompt(temperature: float) -> str:
    """Tạo System Prompt tương ứng với mức temperature."""
    if temperature == 0.0:
        instruction = (
            "CHẾ ĐỘ TRÍCH XUẤT NGUYÊN VĂN (VERBATIM EXTRACTION - TEMPERATURE = 0):\n"
            "- Trích xuất CHÍNH XÁC 100% từng câu chữ, từ ngữ, ký hiệu toán học/khoa học từ tài liệu/ảnh được cung cấp.\n"
            "- TUYỆT ĐỐI KHÔNG tự ý viết lại, không paraphrase, không thêm thắt hay bớt bất kỳ từ ngữ nào.\n"
            "- Giữ nguyên vẹn thứ tự câu hỏi và các phương án A, B, C, D như trong tài liệu gốc.\n"
            "- Xác định đúng phương án đúng (isCorrect: true) dựa trên tài liệu hoặc kiến thức chuẩn."
        )
    else:
        instruction = (
            "CHẾ ĐỘ BIÊN TẬP THÔNG MINH (SMART REFINEMENT - TEMPERATURE > 0):\n"
            "- Bạn được phép sửa lỗi chính tả từ bản quét OCR (như nhận diện nhầm dấu, thiếu chữ).\n"
            "- Có thể trau chuốt lại câu từ cho rõ ràng, mạch lạc, dễ đọc hơn.\n"
            "- TUYỆT ĐỐI BẢO TOÀN tính đúng đắn của kiến thức gốc, không làm sai lệch ý nghĩa hoặc đáp án chuẩn của câu hỏi."
        )

    return f"""Bạn là một AI chuyên gia biên soạn đề thi trắc nghiệm chuyên nghiệp.
Nhiệm vụ của bạn là đọc nội dung văn bản (được trích xuất từ tài liệu hoặc ảnh chụp đề thi) và chuyển đổi thành đề thi trắc nghiệm có cấu trúc JSON hoàn chỉnh.

{instruction}

QUY TẮC ĐỊNH DẠNG ĐẦU RA (OUTPUT FORMAT):
- Bạn CHỈ ĐƯỢC TRẢ VỀ DUY NHẤT một chuỗi JSON hợp lệ, không bọc trong markdown code block (không có ```json ... ```), không có lời dẫn.
- Cấu trúc JSON bắt buộc phải tuân theo schema sau:
{{
  "title": "Tiêu đề đề thi",
  "description": "Mô tả ngắn về đề thi",
  "category": "Chủ đề / Môn học",
  "difficulty": "easy | medium | hard",
  "questions": [
    {{
      "questionText": "Nội dung câu hỏi?",
      "questionType": "single_choice",
      "points": 10,
      "explanation": "Giải thích vì sao đáp án này đúng",
      "options": [
        {{"optionText": "Lựa chọn A", "isCorrect": false}},
        {{"optionText": "Lựa chọn B", "isCorrect": true}},
        {{"optionText": "Lựa chọn C", "isCorrect": false}},
        {{"optionText": "Lựa chọn D", "isCorrect": false}}
      ]
    }}
  ]
}}
"""


def build_user_prompt(
    *,
    topic: str | None = None,
    content: str | None = None,
    num_questions: int = 5,
    difficulty: Difficulty = Difficulty.MEDIUM,
) -> str:
    """Tạo User Prompt chứa thông tin đầu vào."""
    parts: list[str] = [
        f"Hãy tạo một bộ đề thi gồm {num_questions} câu hỏi trắc nghiệm.",
        f"Mức độ khó: {difficulty.value}.",
    ]
    if topic:
        parts.append(f"Chủ đề trọng tâm: {topic}")
    if content:
        parts.append(
            f"Tài liệu / Nội dung văn bản nguồn để ra đề:\n\"\"\"\n{content}\n\"\"\""
        )
    else:
        parts.append("Hãy tự biên soạn các câu hỏi chuẩn mực theo chủ đề trên.")

    return "\n".join(parts)


def build_clean_text_prompt(raw_text: str, target_language: str = "vi") -> tuple[str, str]:
    """Tạo prompt để AI làm sạch văn bản OCR thô (sửa dấu tiếng Việt, nối câu liên trang)."""
    system_prompt = (
        "Bạn là trợ lý biên tập tài liệu giáo dục. "
        "Nhiệm vụ: nhận văn bản trích xuất từ OCR của nhiều trang sách, "
        "sửa lỗi chính tả dấu tiếng Việt do OCR nhận nhầm, "
        "nối liền câu bị đứt đoạn giữa các trang. "
        "Tuyệt đối giữ nguyên nội dung, số liệu, tên riêng và cấu trúc câu hỏi. "
        "Không thêm bớt ý kiến cá nhân. "
        'Trả về JSON: {"cleanedText": "..."}'
    )
    user_prompt = (
        f"Ngôn ngữ mục tiêu: {target_language}\n\n"
        f'Văn bản OCR thô:\n"""\n{raw_text}\n"""'
    )
    return system_prompt, user_prompt


GEMINI_OCR_SYSTEM_PROMPT = """Bạn là hệ thống OCR chuyên dụng, có nhiệm vụ trích xuất TOÀN BỘ văn bản từ hình ảnh tài liệu giáo dục và đề thi tiếng Việt một cách trung thực và chính xác nhất.

QUY TẮC BẮT BUỘC:
1. Đảm bảo 100% dấu tiếng Việt chính xác (ă, â, ê, ô, ơ, ư, đ và các dấu thanh huyền, sắc, hỏi, ngã, nặng). Tuyệt đối không làm mất dấu hay sai dấu.
2. Giữ nguyên cấu trúc thứ tự văn bản từ trên xuống dưới, trái sang phải: tiêu đề, phần, đánh số thứ tự câu hỏi (ví dụ: Câu 1, Câu 2...), các đáp án lựa chọn (A, B, C, D...).
3. Nếu tài liệu có bảng biểu, hãy chuyển thành bảng Markdown chuẩn.
4. Nếu có công thức toán/lý/hóa, hãy giữ nguyên định dạng ký hiệu hoặc dùng công thức LaTeX inline $...$ hoặc Unicode dễ đọc.
5. KHÔNG thêm lời chào, KHÔNG giải thích, KHÔNG thêm nhận xét hay bất kỳ từ ngữ nào ngoài nội dung trong ảnh.
6. Nếu một phần chữ bị mờ hoặc rách không thể đọc được, ghi chú [không rõ].
"""


def build_ocr_prompt(custom_instruction: str | None = None) -> str:
    """Tạo prompt cho Gemini Vision OCR trích xuất văn bản tiếng Việt."""
    if custom_instruction:
        return f"{GEMINI_OCR_SYSTEM_PROMPT}\n\nYêu cầu bổ sung: {custom_instruction}"
    return GEMINI_OCR_SYSTEM_PROMPT


def build_extract_questions_prompt(raw_text: str, default_category: str = "Chung") -> tuple[str, str]:
    """Tạo prompt để LLM bóc tách toàn bộ câu hỏi trắc nghiệm có sẵn trong văn bản OCR."""
    system_prompt = f"""Bạn là một chuyên gia bóc tách đề thi và tài liệu giáo dục trắc nghiệm.
Nhiệm vụ của bạn là đọc kỹ văn bản đầu vào (thu được từ OCR tài liệu/đề thi) và BÓC TÁCH TOÀN BỘ các câu hỏi trắc nghiệm có trong văn bản.

QUY TẮC BẮT BUỘC:
1. KHÔNG TỰ SINH CÂU HỎI MỚI. Chỉ bóc tách các câu hỏi THỰC SỰ XUẤT HIỆN trong tài liệu nguồn.
2. Giữ nguyên vẹn nội dung câu hỏi, ký hiệu toán học, công thức, số liệu và các phương án A, B, C, D... như trong văn bản gốc.
3. Tự động xác định đáp án đúng (isCorrect = true):
   - Nếu tài liệu có ký hiệu đánh dấu (khoanh tròn, gạch chân, in đậm, hoặc bảng đáp án cuối tài liệu) thì tuân theo tài liệu.
   - Nếu tài liệu chưa có đáp án đánh dấu, bạn hãy tự giải chính xác câu hỏi để chọn đáp án đúng nhất.
4. Cung cấp lời giải thích ngắn gọn (explanation) vì sao đáp án đó đúng (nếu suy luận được).
5. Xác định đúng loại câu hỏi:
   - "single_choice": Trắc nghiệm 1 đáp án đúng (mặc định)
   - "true_false": Câu hỏi Đúng/Sai
   - "multiple_choice": Trắc nghiệm có nhiều đáp án đúng
6. Nếu trong văn bản hoàn toàn KHÔNG CÓ câu hỏi trắc nghiệm nào, trả về mảng rỗng [] cho trường "questions".

QUY TẮC ĐỊNH DẠNG ĐẦU RA (JSON THUẦN TÚY):
- CHỈ TRẢ VỀ DUY NHẤT một chuỗi JSON hợp lệ, không bọc markdown ```json ... ```, không có lời dẫn.
- Định dạng JSON bắt buộc:
{{
  "questions": [
    {{
      "questionText": "Nội dung câu hỏi (ví dụ: Câu 1: ...)",
      "questionType": "single_choice",
      "category": "{default_category}",
      "difficulty": "medium",
      "explanation": "Giải thích đáp án...",
      "sourceNote": "Trích xuất từ tài liệu OCR",
      "options": [
        {{"optionText": "Lựa chọn A", "isCorrect": false, "orderNum": 0}},
        {{"optionText": "Lựa chọn B", "isCorrect": true, "orderNum": 1}},
        {{"optionText": "Lựa chọn C", "isCorrect": false, "orderNum": 2}},
        {{"optionText": "Lựa chọn D", "isCorrect": false, "orderNum": 3}}
      ]
    }}
  ]
}}
"""
    user_prompt = f'Nội dung văn bản cần bóc tách toàn bộ câu hỏi:\n"""\n{raw_text}\n"""'
    return system_prompt, user_prompt


