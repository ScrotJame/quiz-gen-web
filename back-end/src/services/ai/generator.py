from __future__ import annotations

import json
import logging
import re
import uuid

from src.models.schemas import (
    AIGenerateRequest,
    Difficulty,
    GeneratedQuizResponse,
    OptionCreate,
    QuestionCreate,
    QuestionType,
    QuizCreate,
)
from src.repositories.base import QuizRepository
from src.services.ai.gemini_client import call_gemini_chat, has_gemini_key
from src.services.ai.ocr import extract_text_from_image
from src.services.ai.prompts import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)


class QuizGeneratorService:
    """Service điều phối OCR và sinh câu hỏi trắc nghiệm qua Gemini AI."""

    def __init__(self, quiz_repo: QuizRepository) -> None:
        self.quiz_repo = quiz_repo

    async def generate_quiz(
        self,
        *,
        topic: str | None = None,
        content: str | None = None,
        num_questions: int = 5,
        difficulty: Difficulty = Difficulty.MEDIUM,
        temperature: float = 0.3,
        save_immediately: bool = False,
        author_name: str = "Gemini AI",
    ) -> GeneratedQuizResponse:
        """Sinh đề trắc nghiệm từ văn bản hoặc chủ đề."""
        if not topic and not content:
            topic = "Kiến thức Tổng quát"

        # Nếu chưa có GEMINI_API_KEY -> Sử dụng Mock Generator để dev không bị gián đoạn
        if not has_gemini_key():
            logger.info("Chưa có GEMINI_API_KEY, kích hoạt Mock Generator.")
            quiz_resp = self._generate_mock_quiz(
                topic=topic or "Đề trắc nghiệm từ tài liệu",
                content=content,
                num_questions=num_questions,
                difficulty=difficulty,
                temperature=temperature,
            )
        else:
            system_prompt = build_system_prompt(temperature)
            user_prompt = build_user_prompt(
                topic=topic,
                content=content,
                num_questions=num_questions,
                difficulty=difficulty,
            )

            raw_response = await call_gemini_chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
            quiz_resp = self._parse_llm_json(raw_response, default_difficulty=difficulty)

        # Lưu ngay vào database nếu được yêu cầu
        if save_immediately:
            created = await self.quiz_repo.create_quiz(
                QuizCreate(
                    title=quiz_resp.title,
                    description=quiz_resp.description,
                    category=quiz_resp.category,
                    difficulty=quiz_resp.difficulty,
                    author_name=author_name,
                    questions=quiz_resp.questions,
                )
            )
            quiz_resp.saved_quiz_id = created.id

        return quiz_resp

    async def generate_from_image(
        self,
        image_bytes: bytes,
        *,
        num_questions: int = 5,
        difficulty: Difficulty = Difficulty.MEDIUM,
        temperature: float = 0.0,
        save_immediately: bool = False,
        author_name: str = "Gemini OCR + AI",
    ) -> GeneratedQuizResponse:
        """Nhận ảnh, trích xuất text qua OCR và đưa vào LLM theo nhiệt độ temperature."""
        ocr_text = await extract_text_from_image(image_bytes)
        if not ocr_text.strip():
            # Nếu không tìm thấy text trong ảnh, vẫn tạo mock fallback
            ocr_text = "Ảnh đề thi trắc nghiệm mẫu (Không phát hiện chữ rõ ràng trong ảnh)."

        return await self.generate_quiz(
            topic="Đề thi từ ảnh chụp",
            content=ocr_text,
            num_questions=num_questions,
            difficulty=difficulty,
            temperature=temperature,
            save_immediately=save_immediately,
            author_name=author_name,
        )

    def _parse_llm_json(
        self, raw_text: str, default_difficulty: Difficulty = Difficulty.MEDIUM
    ) -> GeneratedQuizResponse:
        """Làm sạch markdown fences và parse thành GeneratedQuizResponse."""
        cleaned = raw_text.strip()
        # Loại bỏ ```json ... ``` nếu có
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except Exception as e:
            logger.error(f"Không thể parse JSON từ LLM output: {cleaned[:200]} - {e}")
            raise ValueError(f"Dữ liệu trả về từ AI không đúng định dạng JSON: {e}")

        # Parse questions
        questions_in: list[QuestionCreate] = []
        raw_questions = data.get("questions", [])
        for idx, q in enumerate(raw_questions):
            opts_in: list[OptionCreate] = []
            for o_idx, opt in enumerate(q.get("options", [])):
                opts_in.append(
                    OptionCreate(
                        option_text=opt.get("optionText", f"Lựa chọn {o_idx + 1}"),
                        is_correct=bool(opt.get("isCorrect", False)),
                        order_num=o_idx,
                    )
                )

            # Đảm bảo ít nhất 1 đáp án đúng nếu LLM quên gán
            if not any(o.is_correct for o in opts_in) and opts_in:
                opts_in[0].is_correct = True

            questions_in.append(
                QuestionCreate(
                    question_text=q.get("questionText", f"Câu hỏi {idx + 1}"),
                    question_type=QuestionType.SINGLE_CHOICE,
                    points=int(q.get("points", 10)),
                    order_num=idx,
                    explanation=q.get("explanation", ""),
                    options=opts_in,
                )
            )

        diff_str = str(data.get("difficulty", default_difficulty.value)).lower()
        diff = (
            Difficulty(diff_str)
            if diff_str in [d.value for d in Difficulty]
            else default_difficulty
        )

        return GeneratedQuizResponse(
            title=data.get("title", "Đề thi AI tạo"),
            description=data.get("description", "Được tạo tự động bởi Gemini AI."),
            category=data.get("category", "Chung"),
            difficulty=diff,
            questions=questions_in,
        )

    def _generate_mock_quiz(
        self,
        *,
        topic: str,
        content: str | None = None,
        num_questions: int = 5,
        difficulty: Difficulty = Difficulty.MEDIUM,
        temperature: float = 0.3,
    ) -> GeneratedQuizResponse:
        """Tạo bộ đề mock chất lượng cao phục vụ testing và dev local."""
        questions: list[QuestionCreate] = []
        prefix = "Trích xuất" if temperature == 0.0 else "Biên soạn"

        for i in range(1, num_questions + 1):
            questions.append(
                QuestionCreate(
                    question_text=f"[{prefix}] Câu {i}: Nội dung câu hỏi kiểm tra về {topic}?",
                    question_type=QuestionType.SINGLE_CHOICE,
                    points=10,
                    order_num=i - 1,
                    explanation=f"Giải thích chi tiết: Phương án A là đáp án chính xác theo tài liệu {topic}.",
                    options=[
                        OptionCreate(
                            option_text=f"Phương án A (Chính xác cho câu {i})",
                            is_correct=True,
                            order_num=0,
                        ),
                        OptionCreate(
                            option_text=f"Phương án B (Chưa chính xác cho câu {i})",
                            is_correct=False,
                            order_num=1,
                        ),
                        OptionCreate(
                            option_text=f"Phương án C (Nhiễu 1 cho câu {i})",
                            is_correct=False,
                            order_num=2,
                        ),
                        OptionCreate(
                            option_text=f"Phương án D (Nhiễu 2 cho câu {i})",
                            is_correct=False,
                            order_num=3,
                        ),
                    ],
                )
            )

        desc = f"Đề thi gồm {num_questions} câu về chủ đề '{topic}'."
        if content:
            desc += f" (Trích xuất từ nguồn văn bản: {len(content)} ký tự)."

        return GeneratedQuizResponse(
            title=f"Đề kiểm tra: {topic}",
            description=desc,
            category=topic[:30],
            difficulty=difficulty,
            questions=questions,
        )
