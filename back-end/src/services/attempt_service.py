from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.models.schemas import (
    AnswerSubmission,
    AttemptAnswerDetail,
    AttemptResult,
    AttemptStatus,
    LeaderboardEntry,
    QuestionType,
    SubmitAttemptRequest,
)
from src.repositories.base import AttemptRepository, QuizRepository


class AttemptServiceError(Exception):
    """Lỗi nghiệp vụ làm bài thi."""
    pass


class AttemptService:
    """Nghiệp vụ làm bài thi, tự động chấm điểm và tính thứ hạng.

    Độc lập với HTTP/FastAPI, nhận repositories qua constructor injection.
    """

    def __init__(
        self,
        attempt_repo: AttemptRepository,
        quiz_repo: QuizRepository,
    ) -> None:
        self.attempt_repo = attempt_repo
        self.quiz_repo = quiz_repo

    async def start_attempt(
        self, quiz_id: uuid.UUID, participant_name: str
    ) -> AttemptResult:
        quiz = await self.quiz_repo.get_quiz(quiz_id)
        if not quiz:
            raise AttemptServiceError(f"Không tìm thấy đề thi với mã: {quiz_id}")
        if not quiz.is_published:
            raise AttemptServiceError("Đề thi này chưa được phát hành.")

        cleaned_name = participant_name.strip() or "Thí sinh"
        return await self.attempt_repo.create_attempt(quiz_id, cleaned_name)

    async def get_attempt(self, attempt_id: uuid.UUID) -> AttemptResult:
        attempt = await self.attempt_repo.get_attempt(attempt_id)
        if not attempt:
            raise AttemptServiceError(f"Không tìm thấy lượt làm bài: {attempt_id}")
        return attempt

    async def submit_attempt(
        self, attempt_id: uuid.UUID, data: SubmitAttemptRequest
    ) -> AttemptResult:
        attempt = await self.get_attempt(attempt_id)
        if attempt.status == AttemptStatus.COMPLETED:
            raise AttemptServiceError("Lượt thi này đã được nộp trước đó.")

        quiz = await self.quiz_repo.get_quiz(attempt.quiz_id)
        if not quiz:
            raise AttemptServiceError("Đề thi tương ứng không tồn tại.")

        # Lập map câu hỏi và đáp án đúng
        question_map = {q.id: q for q in quiz.questions}
        submission_map: dict[uuid.UUID, list[uuid.UUID]] = {
            ans.question_id: ans.selected_option_ids for ans in data.answers
        }

        total_earned_score = 0
        total_max_score = sum(q.points for q in quiz.questions)
        answer_details: list[AttemptAnswerDetail] = []

        for q in quiz.questions:
            selected_ids = submission_map.get(q.id, [])
            correct_option_ids = [opt.id for opt in q.options if opt.is_correct]

            # Kiểm tra đáp án
            is_correct = False
            earned_points = 0

            # So sánh tập hợp ID đã chọn với tập hợp ID đúng
            if set(selected_ids) == set(correct_option_ids) and len(correct_option_ids) > 0:
                is_correct = True
                earned_points = q.points
                total_earned_score += earned_points

            answer_details.append(
                AttemptAnswerDetail(
                    id=uuid.uuid4(),
                    question_id=q.id,
                    selected_option_ids=selected_ids,
                    is_correct=is_correct,
                    earned_points=earned_points,
                )
            )

        percentage = (
            round((total_earned_score / total_max_score) * 100, 2)
            if total_max_score > 0
            else 0.0
        )

        completed_attempt = await self.attempt_repo.submit_attempt(
            attempt_id=attempt_id,
            answers=answer_details,
            score=total_earned_score,
            max_score=total_max_score,
            percentage=percentage,
        )
        if not completed_attempt:
            raise AttemptServiceError("Không thể lưu kết quả chấm thi.")

        return completed_attempt

    async def get_leaderboard(
        self, quiz_id: uuid.UUID, limit: int = 20
    ) -> list[LeaderboardEntry]:
        quiz = await self.quiz_repo.get_quiz(quiz_id)
        if not quiz:
            raise AttemptServiceError(f"Không tìm thấy đề thi với mã: {quiz_id}")
        return await self.attempt_repo.get_leaderboard(quiz_id, limit=limit)
