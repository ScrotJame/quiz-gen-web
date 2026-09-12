import pytest

from src.models.schemas import (
    AnswerSubmission,
    Difficulty,
    OptionCreate,
    QuestionCreate,
    QuestionType,
    QuizCreate,
    SubmitAttemptRequest,
)
from src.repositories.memory import InMemoryAttemptRepository, InMemoryQuizRepository
from src.services.attempt_service import AttemptService, AttemptServiceError
from src.services.quiz_service import QuizService, QuizServiceError


@pytest.fixture
def memory_repos():
    q_repo = InMemoryQuizRepository()
    att_repo = InMemoryAttemptRepository()
    return q_repo, att_repo


@pytest.mark.asyncio
async def test_quiz_service_validation(memory_repos):
    q_repo, _ = memory_repos
    service = QuizService(q_repo)

    # Empty title error
    with pytest.raises(QuizServiceError, match="không được để trống"):
        await service.create_quiz(QuizCreate(title=""))

    # Question without correct option error
    with pytest.raises(QuizServiceError, match="ít nhất 1 đáp án đúng"):
        await service.create_quiz(
            QuizCreate(
                title="Invalid Quiz",
                questions=[
                    QuestionCreate(
                        question_text="Q1",
                        options=[
                            OptionCreate(option_text="A", is_correct=False),
                            OptionCreate(option_text="B", is_correct=False),
                        ],
                    )
                ],
            )
        )


@pytest.mark.asyncio
async def test_attempt_scoring_flow(memory_repos):
    q_repo, att_repo = memory_repos
    quiz_service = QuizService(q_repo)
    attempt_service = AttemptService(att_repo, q_repo)

    # Create 2 questions: Q1 (10 pts), Q2 (20 pts) -> max = 30 pts
    quiz = await quiz_service.create_quiz(
        QuizCreate(
            title="Math Quiz",
            difficulty=Difficulty.EASY,
            questions=[
                QuestionCreate(
                    question_text="1 + 1 = ?",
                    points=10,
                    options=[
                        OptionCreate(option_text="2", is_correct=True),
                        OptionCreate(option_text="3", is_correct=False),
                    ],
                ),
                QuestionCreate(
                    question_text="3 * 3 = ?",
                    points=20,
                    options=[
                        OptionCreate(option_text="6", is_correct=False),
                        OptionCreate(option_text="9", is_correct=True),
                    ],
                ),
            ],
        )
    )

    q1 = quiz.questions[0]
    q2 = quiz.questions[1]
    q1_correct = [o for o in q1.options if o.is_correct][0]
    q2_wrong = [o for o in q2.options if not o.is_correct][0]

    # Start attempt
    att = await attempt_service.start_attempt(quiz.id, "Student 1")
    assert att.score == 0

    # Submit: Q1 correct, Q2 wrong
    result = await attempt_service.submit_attempt(
        att.id,
        SubmitAttemptRequest(
            answers=[
                AnswerSubmission(
                    question_id=q1.id,
                    selected_option_ids=[q1_correct.id],
                ),
                AnswerSubmission(
                    question_id=q2.id,
                    selected_option_ids=[q2_wrong.id],
                ),
            ]
        ),
    )

    assert result.score == 10
    assert result.max_score == 30
    assert result.percentage == round((10 / 30) * 100, 2)
    assert len(result.answers) == 2
    assert result.answers[0].is_correct is True
    assert result.answers[0].earned_points == 10
    assert result.answers[1].is_correct is False
    assert result.answers[1].earned_points == 0

    # Cannot resubmit completed attempt
    with pytest.raises(AttemptServiceError, match="đã được nộp trước đó"):
        await attempt_service.submit_attempt(att.id, SubmitAttemptRequest(answers=[]))

    # Leaderboard
    lb = await attempt_service.get_leaderboard(quiz.id)
    assert len(lb) == 1
    assert lb[0].participant_name == "Student 1"
    assert lb[0].score == 10
