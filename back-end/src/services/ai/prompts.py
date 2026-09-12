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
