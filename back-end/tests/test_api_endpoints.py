import io
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw

from src.main import app


@pytest.fixture
def test_image_file() -> tuple[str, bytes, str]:
    img = Image.new("RGB", (200, 80), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), "Quiz Test 1+1=2", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return ("test_quiz.png", buf.getvalue(), "image/png")


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert data["appName"] == "Quiz Web Backend"


@pytest.mark.asyncio
async def test_quizzes_crud_and_attempts_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create quiz
        payload = {
            "title": "API Flow Quiz",
            "category": "Testing",
            "difficulty": "easy",
            "timeLimitMinutes": 10,
            "questions": [
                {
                    "questionText": "What is 10 + 10?",
                    "questionType": "single_choice",
                    "points": 10,
                    "options": [
                        {"optionText": "20", "isCorrect": True},
                        {"optionText": "30", "isCorrect": False},
                    ],
                }
            ],
        }
        create_res = await client.post("/api/v1/quizzes", json=payload)
        assert create_res.status_code == 201
        quiz_data = create_res.json()
        quiz_id = quiz_data["id"]
        assert len(quiz_data["questions"]) == 1
        q_id = quiz_data["questions"][0]["id"]
        correct_opt_id = quiz_data["questions"][0]["options"][0]["id"]

        # 2. List quizzes
        list_res = await client.get("/api/v1/quizzes")
        assert list_res.status_code == 200
        assert list_res.json()["total"] >= 1

        # 3. Start attempt
        start_res = await client.post(
            "/api/v1/attempts/start",
            json={"quizId": quiz_id, "participantName": "Nguyen Van A"},
        )
        assert start_res.status_code == 201
        attempt_id = start_res.json()["id"]

        # 4. Submit attempt
        submit_res = await client.post(
            f"/api/v1/attempts/{attempt_id}/submit",
            json={
                "answers": [
                    {
                        "questionId": q_id,
                        "selectedOptionIds": [correct_opt_id],
                    }
                ]
            },
        )
        assert submit_res.status_code == 200
        result = submit_res.json()
        assert result["score"] == 10
        assert result["percentage"] == 100.0

        # 5. Leaderboard
        lb_res = await client.get(f"/api/v1/quizzes/{quiz_id}/leaderboard")
        assert lb_res.status_code == 200
        lb_data = lb_res.json()
        assert len(lb_data) >= 1
        assert lb_data[0]["participantName"] == "Nguyen Van A"


@pytest.mark.asyncio
async def test_ai_generate_endpoints(test_image_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Generate from text
        ai_res = await client.post(
            "/api/v1/ai/generate",
            json={
                "topic": "JavaScript ES6",
                "numQuestions": 3,
                "difficulty": "medium",
                "temperature": 0.3,
                "saveImmediately": False,
            },
        )
        assert ai_res.status_code == 200
        gen_data = ai_res.json()
        assert len(gen_data["questions"]) == 3
        assert "JavaScript ES6" in gen_data["title"]

        # 2. Generate from image
        filename, img_bytes, content_type = test_image_file
        files = {"file": (filename, img_bytes, content_type)}
        data = {
            "numQuestions": "2",
            "temperature": "0.0",
            "saveImmediately": "false",
        }
        img_res = await client.post(
            "/api/v1/ai/generate-from-image",
            files=files,
            data=data,
        )
        assert img_res.status_code == 200
        img_quiz = img_res.json()
        assert len(img_quiz["questions"]) == 2
