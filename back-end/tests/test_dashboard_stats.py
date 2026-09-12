import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_dashboard_stats_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Gọi endpoint stats
        res = await client.get("/api/v1/quizzes/stats")
        assert res.status_code == 200
        data = res.json()
        assert "totalQuizzes" in data
        assert "averageScore" in data
        assert "totalQuestionsCompleted" in data
        assert "totalAttempts" in data
        assert isinstance(data["totalQuizzes"], int)
        assert isinstance(data["averageScore"], (int, float))
        assert isinstance(data["totalQuestionsCompleted"], int)
        assert isinstance(data["totalAttempts"], int)

        # 2. Tạo 1 quiz mới và verify totalQuizzes tăng lên
        initial_quizzes = data["totalQuizzes"]
        payload = {
            "title": "Dashboard Test Quiz",
            "category": "Stats",
            "difficulty": "medium",
            "questions": [
                {
                    "questionText": "Stat Question 1?",
                    "points": 10,
                    "options": [
                        {"optionText": "Ans 1", "isCorrect": True},
                        {"optionText": "Ans 2", "isCorrect": False},
                    ],
                }
            ],
        }
        create_res = await client.post("/api/v1/quizzes", json=payload)
        assert create_res.status_code == 201

        # Check lại stats
        res_after = await client.get("/api/v1/quizzes/stats")
        assert res_after.status_code == 200
        stats_after = res_after.json()
        assert stats_after["totalQuizzes"] == initial_quizzes + 1
