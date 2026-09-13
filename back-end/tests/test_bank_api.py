"""TDD - RED PHASE: Test cho Bank API Endpoints.

Chạy: pytest back-end/tests/test_bank_api.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from src.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ─── POST /api/v1/bank/questions/batch ───────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_create_success(client):
    """Batch insert thành công trả về 201 và danh sách câu hỏi."""
    payload = {
        "questions": [
            {
                "questionText": "Thủ đô Pháp là gì?",
                "questionType": "single_choice",
                "category": "Địa lý",
                "difficulty": "easy",
                "explanation": "Paris là thủ đô.",
                "sourceNote": "Batch test",
                "options": [
                    {"optionText": "Paris", "isCorrect": True, "orderNum": 0},
                    {"optionText": "London", "isCorrect": False, "orderNum": 1},
                    {"optionText": "Berlin", "isCorrect": False, "orderNum": 2},
                ],
            },
            {
                "questionText": "2 + 2 = ?",
                "questionType": "single_choice",
                "category": "Toán",
                "difficulty": "easy",
                "options": [
                    {"optionText": "3", "isCorrect": False, "orderNum": 0},
                    {"optionText": "4", "isCorrect": True, "orderNum": 1},
                ],
            },
        ]
    }
    response = await client.post("/api/v1/bank/questions/batch", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert len(data) == 2
    assert data[0]["questionText"] == "Thủ đô Pháp là gì?"
    assert data[0]["category"] == "Địa lý"
    assert len(data[0]["options"]) == 3
    assert data[1]["questionText"] == "2 + 2 = ?"


@pytest.mark.asyncio
async def test_batch_create_empty_raises_422(client):
    """Batch rỗng trả về 422."""
    response = await client.post("/api/v1/bank/questions/batch", json={"questions": []})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_batch_create_exceeds_limit_raises_422(client):
    """Batch quá 100 câu trả về 422."""
    questions = [
        {
            "questionText": f"Câu {i}?",
            "questionType": "single_choice",
            "category": "Test",
            "difficulty": "easy",
            "options": [
                {"optionText": "A", "isCorrect": True, "orderNum": 0},
                {"optionText": "B", "isCorrect": False, "orderNum": 1},
            ],
        }
        for i in range(101)
    ]
    response = await client.post("/api/v1/bank/questions/batch", json={"questions": questions})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_batch_create_question_missing_correct_answer_raises_400(client):
    """Câu hỏi không có đáp án đúng trả về 400."""
    payload = {
        "questions": [
            {
                "questionText": "Câu hỏi không có đáp án đúng?",
                "questionType": "single_choice",
                "category": "Test",
                "difficulty": "easy",
                "options": [
                    {"optionText": "A", "isCorrect": False, "orderNum": 0},
                    {"optionText": "B", "isCorrect": False, "orderNum": 1},
                ],
            }
        ]
    }
    response = await client.post("/api/v1/bank/questions/batch", json=payload)
    assert response.status_code == 400


# ─── GET /api/v1/bank/questions ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_bank_questions_default(client):
    """Lấy danh sách câu hỏi mặc định trả về 200 và có phân trang."""
    response = await client.get("/api/v1/bank/questions")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data


@pytest.mark.asyncio
async def test_list_bank_questions_with_filter(client):
    """Lọc theo category và difficulty hoạt động."""
    # Seed
    await client.post("/api/v1/bank/questions/batch", json={
        "questions": [
            {
                "questionText": "Câu Lý khó?",
                "questionType": "single_choice",
                "category": "Vật lý API",
                "difficulty": "hard",
                "options": [
                    {"optionText": "A", "isCorrect": True, "orderNum": 0},
                    {"optionText": "B", "isCorrect": False, "orderNum": 1},
                ],
            }
        ]
    })

    response = await client.get("/api/v1/bank/questions?category=Vật lý API&difficulty=hard")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["category"] == "Vật lý API"
        assert item["difficulty"] == "hard"


@pytest.mark.asyncio
async def test_list_bank_questions_search(client):
    """Tìm kiếm theo từ khóa hoạt động."""
    unique_text = "Câu hỏi đặc biệt XYZ123"
    await client.post("/api/v1/bank/questions/batch", json={
        "questions": [
            {
                "questionText": unique_text,
                "questionType": "single_choice",
                "category": "Test",
                "difficulty": "easy",
                "options": [
                    {"optionText": "A", "isCorrect": True, "orderNum": 0},
                    {"optionText": "B", "isCorrect": False, "orderNum": 1},
                ],
            }
        ]
    })

    response = await client.get("/api/v1/bank/questions?search=XYZ123")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any("XYZ123" in item["questionText"] for item in data["items"])


# ─── GET /api/v1/bank/categories ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_categories(client):
    """Lấy danh sách categories trả về 200."""
    response = await client.get("/api/v1/bank/categories")
    assert response.status_code == 200

    data = response.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)


# ─── GET /api/v1/bank/questions/{id} ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_bank_question_by_id(client):
    """Lấy chi tiết 1 câu hỏi theo ID."""
    create_resp = await client.post("/api/v1/bank/questions/batch", json={
        "questions": [
            {
                "questionText": "Câu cần lấy chi tiết?",
                "questionType": "single_choice",
                "category": "Chung",
                "difficulty": "medium",
                "options": [
                    {"optionText": "A", "isCorrect": True, "orderNum": 0},
                    {"optionText": "B", "isCorrect": False, "orderNum": 1},
                ],
            }
        ]
    })
    q_id = create_resp.json()[0]["id"]

    response = await client.get(f"/api/v1/bank/questions/{q_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == q_id
    assert data["questionText"] == "Câu cần lấy chi tiết?"


@pytest.mark.asyncio
async def test_get_bank_question_not_found(client):
    """Trả về 404 nếu không tìm thấy câu hỏi."""
    import uuid
    response = await client.get(f"/api/v1/bank/questions/{uuid.uuid4()}")
    assert response.status_code == 404


# ─── PUT /api/v1/bank/questions/{id} ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_bank_question(client):
    """Cập nhật nội dung câu hỏi trong ngân hàng."""
    create_resp = await client.post("/api/v1/bank/questions/batch", json={
        "questions": [
            {
                "questionText": "Câu gốc chưa sửa?",
                "questionType": "single_choice",
                "category": "Cũ",
                "difficulty": "easy",
                "options": [
                    {"optionText": "A", "isCorrect": True, "orderNum": 0},
                    {"optionText": "B", "isCorrect": False, "orderNum": 1},
                ],
            }
        ]
    })
    q_id = create_resp.json()[0]["id"]

    response = await client.put(f"/api/v1/bank/questions/{q_id}", json={
        "questionText": "Câu đã được sửa!",
        "category": "Mới",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["questionText"] == "Câu đã được sửa!"
    assert data["category"] == "Mới"


# ─── DELETE /api/v1/bank/questions/{id} ──────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_bank_question(client):
    """Xóa câu hỏi khỏi ngân hàng."""
    create_resp = await client.post("/api/v1/bank/questions/batch", json={
        "questions": [
            {
                "questionText": "Câu cần xóa?",
                "questionType": "single_choice",
                "category": "Chung",
                "difficulty": "easy",
                "options": [
                    {"optionText": "A", "isCorrect": True, "orderNum": 0},
                    {"optionText": "B", "isCorrect": False, "orderNum": 1},
                ],
            }
        ]
    })
    q_id = create_resp.json()[0]["id"]

    del_response = await client.delete(f"/api/v1/bank/questions/{q_id}")
    assert del_response.status_code == 204

    # Xác nhận đã xóa
    get_response = await client.get(f"/api/v1/bank/questions/{q_id}")
    assert get_response.status_code == 404
