from __future__ import annotations

import json
import logging
import re
import uuid

from src.core.exceptions import ExternalServiceError
from src.models.schemas import (
    AIGenerateRequest,
    BankOptionCreate,
    BankQuestionCreate,
    Difficulty,
    ExtractQuestionsResponse,
    GeneratedQuizResponse,
    OptionCreate,
    QuestionCreate,
    QuestionType,
    QuizCreate,
)
from src.repositories.base import QuizRepository
from src.services.ai.gemini_client import call_gemini_chat, has_gemini_key
from src.services.ai.mistral_client import call_mistral_chat, has_mistral_key
from src.services.ai.ocr import extract_text_from_image
from src.services.ai.prompts import (
    build_clean_text_prompt,
    build_extract_questions_prompt,
    build_system_prompt,
    build_user_prompt,
)

logger = logging.getLogger(__name__)


class QuizGeneratorService:
    """Service điều phối OCR và sinh câu hỏi trắc nghiệm qua Mistral AI / Gemini AI."""

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
        author_name: str = "AI Quiz Generator",
    ) -> GeneratedQuizResponse:
        """Sinh đề trắc nghiệm từ văn bản hoặc chủ đề (ưu tiên Mistral AI)."""
        if not topic and not content:
            topic = "Kiến thức Tổng quát"

        system_prompt = build_system_prompt(temperature)
        user_prompt = build_user_prompt(
            topic=topic,
            content=content,
            num_questions=num_questions,
            difficulty=difficulty,
        )

        quiz_resp: GeneratedQuizResponse | None = None
        actual_provider = "Mock AI"

        # 1. Ưu tiên sử dụng Gemini AI (gemini-3.5-flash-lite)
        if has_gemini_key():
            try:
                logger.info("Đang sinh câu hỏi bằng Gemini AI (gemini-3.5-flash-lite)...")
                raw_response = await call_gemini_chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    model="gemini-3.5-flash-lite",
                )
                quiz_resp = self._parse_llm_json(raw_response, default_difficulty=difficulty)
                actual_provider = "Gemini AI"
            except Exception as e:
                logger.warning(
                    f"Sinh câu hỏi bằng Gemini AI thất bại ({e}), chuyển sang kiểm tra fallback..."
                )

        # 2. Fallback sang Mistral AI nếu Gemini không có key hoặc gặp lỗi
        if quiz_resp is None and has_mistral_key():
            try:
                logger.info("Đang sinh câu hỏi bằng Mistral AI (fallback)...")
                raw_response = await call_mistral_chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
                quiz_resp = self._parse_llm_json(raw_response, default_difficulty=difficulty)
                actual_provider = "Mistral AI"
            except Exception as e:
                logger.error(f"Sinh câu hỏi bằng Mistral AI thất bại: {e}")

        # 3. Fallback sang Mock Generator nếu không có API key hoặc cả hai đều lỗi
        if quiz_resp is None:
            logger.info("Kích hoạt Mock Generator làm fallback.")
            quiz_resp = self._generate_mock_quiz(
                topic=topic or "Đề trắc nghiệm từ tài liệu",
                content=content,
                num_questions=num_questions,
                difficulty=difficulty,
                temperature=temperature,
            )
            actual_provider = "Mock Generator"

        # Điều chỉnh author_name nếu đang dùng giá trị mặc định chung
        final_author = author_name
        if not final_author or final_author in ("Gemini AI", "Mistral AI", "AI Quiz Generator", "Gemini OCR + AI"):
            final_author = actual_provider

        # Lưu ngay vào database nếu được yêu cầu
        if save_immediately:
            created = await self.quiz_repo.create_quiz(
                QuizCreate(
                    title=quiz_resp.title,
                    description=quiz_resp.description,
                    category=quiz_resp.category,
                    difficulty=quiz_resp.difficulty,
                    author_name=final_author,
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
        author_name: str = "AI Quiz Generator",
        preferred_engine: str = "auto",
    ) -> GeneratedQuizResponse:
        """Nhận ảnh, trích xuất text qua OCR và đưa vào LLM theo nhiệt độ temperature."""
        ocr_text = await extract_text_from_image(
            image_bytes, preferred_engine=preferred_engine
        )
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

    async def clean_text(self, raw_text: str, target_language: str = "vi") -> str:
        """Làm sạch văn bản OCR thô bằng AI (sửa dấu tiếng Việt, chuẩn hóa cấu trúc)."""
        if not has_mistral_key() and not has_gemini_key():
            logger.info("Không có API key AI nào — trả nguyên raw_text làm fallback.")
            return raw_text

        system_prompt, user_prompt = build_clean_text_prompt(raw_text, target_language)
        raw_response: str | None = None
        try:
            if has_gemini_key():
                raw_response = await call_gemini_chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.2,
                    model="gemini-3.5-flash-lite",
                )
            elif has_mistral_key():
                raw_response = await call_mistral_chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.2,
                )
        except Exception as e:
            logger.error(f"Lỗi khi gọi AI để làm sạch text: {e}", exc_info=True)
            raise ExternalServiceError("Không thể kết nối với dịch vụ AI. Vui lòng thử lại sau.")

        if not raw_response:
            return raw_text

        try:
            cleaned = raw_response.strip()
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            parsed = json.loads(cleaned)
            return parsed.get("cleanedText", raw_text)
        except Exception:
            logger.warning("Không parse được JSON từ AI clean-text, dùng raw_text fallback.")
            return raw_text

    def _parse_extracted_questions_json(
        self,
        raw_json: str,
        default_category: str = "Chung",
        default_difficulty: str = "medium",
    ) -> list[BankQuestionCreate]:
        """Chuyển đổi chuỗi JSON từ LLM thành danh sách BankQuestionCreate."""
        cleaned = raw_json.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        data = json.loads(cleaned)
        if isinstance(data, list):
            raw_qs = data
        elif isinstance(data, dict):
            raw_qs = data.get("questions", [])
        else:
            raw_qs = []
        result: list[BankQuestionCreate] = []

        for q in raw_qs:
            opts: list[BankOptionCreate] = []
            for idx, opt in enumerate(q.get("options", [])):
                opts.append(
                    BankOptionCreate(
                        option_text=opt.get("optionText", f"Lựa chọn {idx + 1}"),
                        is_correct=bool(opt.get("isCorrect", False)),
                        order_num=int(opt.get("orderNum", idx)),
                    )
                )
            if opts and not any(o.is_correct for o in opts):
                opts[0].is_correct = True

            q_type_str = q.get("questionType", "single_choice")
            try:
                q_type = QuestionType(q_type_str)
            except ValueError:
                q_type = QuestionType.SINGLE_CHOICE

            result.append(
                BankQuestionCreate(
                    question_text=q.get("questionText", "Nội dung câu hỏi"),
                    question_type=q_type,
                    category=q.get("category") or default_category,
                    difficulty=q.get("difficulty") or default_difficulty,
                    explanation=q.get("explanation"),
                    source_note=q.get("sourceNote", "Bóc tách từ tài liệu OCR"),
                    options=opts,
                )
            )
        return result

    def _extract_questions_fallback(
        self,
        text: str,
        default_category: str = "Chung",
        default_difficulty: str = "medium",
    ) -> list[BankQuestionCreate]:
        """Fallback trích xuất câu hỏi bằng regex khi không có AI LLM."""
        pattern = r"(?=(?:^|\n)\s*(?:[Cc][âa]u|[Bb]ài|[Bb]ai|[Qq]uestion)\s*\d+[:.]|\b(?:[Cc][âa]u|[Bb]ài|[Bb]ai|[Qq]uestion)\s*\d+[:.])"
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        questions: list[BankQuestionCreate] = []

        for part in parts:
            chunk = part.strip()
            if not chunk:
                continue

            match_header = re.match(
                r"^(?:(?:[Cc][âa]u|[Bb]ài|[Bb]ai|[Qq]uestion)\s*\d+[:.]|\d+[:.])\s*(.+)",
                chunk,
                flags=re.DOTALL | re.IGNORECASE,
            )
            if not match_header:
                continue

            opt_pattern = r"(?:^|\n)\s*([A-D])[\.:\)]\s*(.+?)(?=(?:(?:^|\n)\s*[A-D][\.:\)])|\Z)"
            opt_matches = list(re.finditer(opt_pattern, chunk, flags=re.DOTALL | re.IGNORECASE))

            if len(opt_matches) >= 2:
                first_opt_start = opt_matches[0].start()
                q_text = chunk[:first_opt_start].strip()

                options: list[BankOptionCreate] = []
                for idx, opt_m in enumerate(opt_matches):
                    opt_letter = opt_m.group(1).upper()
                    opt_content = opt_m.group(2).strip()
                    is_correct = bool(re.search(r"(\[\s*[xX*]\s*\]|\*|\(đúng\))", opt_content))
                    opt_cleaned = re.sub(r"(\[\s*[xX*]\s*\]|\*|\(đúng\))", "", opt_content).strip()
                    opt_text = (
                        f"{opt_letter}. {opt_cleaned}"
                        if not opt_cleaned.startswith(f"{opt_letter}.")
                        else opt_cleaned
                    )
                    options.append(
                        BankOptionCreate(
                            option_text=opt_text,
                            is_correct=is_correct,
                            order_num=idx,
                        )
                    )

                if not any(o.is_correct for o in options) and options:
                    options[0].is_correct = True

                questions.append(
                    BankQuestionCreate(
                        question_text=q_text,
                        question_type=QuestionType.SINGLE_CHOICE,
                        category=default_category,
                        difficulty=default_difficulty,
                        explanation="Trích xuất từ cấu trúc đề thi văn bản.",
                        source_note="Bóc tách từ tài liệu OCR",
                        options=options,
                    )
                )

        return questions

    async def extract_questions(
        self,
        raw_text: str,
        default_category: str = "Chung",
        default_difficulty: str = "medium",
    ) -> ExtractQuestionsResponse:
        """Bóc tách toàn bộ câu hỏi trắc nghiệm có sẵn trong văn bản OCR bằng LLM (hoặc regex fallback)."""
        if not raw_text.strip():
            return ExtractQuestionsResponse(questions=[], total_extracted=0)

        questions: list[BankQuestionCreate] | None = None

        if has_gemini_key() or has_mistral_key():
            system_prompt, user_prompt = build_extract_questions_prompt(
                raw_text, default_category=default_category
            )
            raw_response: str | None = None
            # 1. Ưu tiên Gemini AI (gemini-3.5-flash-lite)
            if has_gemini_key():
                try:
                    logger.info("Đang bóc tách câu hỏi bằng Gemini AI (gemini-3.5-flash-lite)...")
                    raw_response = await call_gemini_chat(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.0,
                        model="gemini-3.5-flash-lite",
                    )
                    if raw_response:
                        questions = self._parse_extracted_questions_json(
                            raw_response,
                            default_category=default_category,
                            default_difficulty=default_difficulty,
                        )
                except Exception as e:
                    logger.warning(
                        f"Bóc tách câu hỏi bằng Gemini AI gặp lỗi ({e}), chuyển sang kiểm tra fallback..."
                    )

            # 2. Fallback sang Mistral AI nếu Gemini không thành công
            if questions is None and has_mistral_key():
                try:
                    logger.info("Đang bóc tách câu hỏi bằng Mistral AI (fallback)...")
                    raw_response = await call_mistral_chat(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.0,
                    )
                    if raw_response:
                        questions = self._parse_extracted_questions_json(
                            raw_response,
                            default_category=default_category,
                            default_difficulty=default_difficulty,
                        )
                except Exception as e:
                    logger.warning(
                        f"Bóc tách câu hỏi bằng Mistral AI gặp lỗi ({e}), chuyển sang regex fallback."
                    )

        if questions is None:
            logger.info("Dùng fallback regex để bóc tách câu hỏi từ văn bản.")
            questions = self._extract_questions_fallback(
                raw_text,
                default_category=default_category,
                default_difficulty=default_difficulty,
            )

        return ExtractQuestionsResponse(
            questions=questions,
            total_extracted=len(questions),
        )

