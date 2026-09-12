"""Tests cho 2 endpoint OCR Studio: /ai/ocr-page va /ai/clean-text."""
from __future__ import annotations

import io
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from src.main import app

client = TestClient(app)


def _make_png_bytes(width: int = 10, height: int = 10, color: str = "white") -> bytes:
    """Tao file PNG nho hop le cho test."""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(buf, format="PNG")
    return buf.getvalue()


# POST /api/v1/ai/ocr-page


class TestOcrPage:
    def test_bad_content_type_returns_400(self) -> None:
        response = client.post(
            "/api/v1/ai/ocr-page",
            files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_empty_file_returns_400(self) -> None:
        response = client.post(
            "/api/v1/ai/ocr-page",
            files={"file": ("empty.png", b"", "image/png")},
        )
        assert response.status_code == 400

    def test_file_too_large_returns_400(self) -> None:
        with patch("src.api.ai.get_settings") as mock_settings:
            mock_settings.return_value.max_upload_size_mb = 0
            response = client.post(
                "/api/v1/ai/ocr-page",
                files={"file": ("big.png", _make_png_bytes(), "image/png")},
            )
        assert response.status_code == 400

    def test_blank_image_returns_422_no_text_found(self) -> None:
        from src.models.schemas import OcrPageResponse
        blank_png = _make_png_bytes(color="white")
        with patch("src.api.ai.extract_text_with_metadata", new_callable=AsyncMock) as mock_ocr:
            mock_ocr.return_value = OcrPageResponse(text="", line_count=0, average_confidence=0.0)
            response = client.post(
                "/api/v1/ai/ocr-page",
                files={"file": ("blank.png", blank_png, "image/png")},
            )
        assert response.status_code == 422
        body = response.json()["detail"]
        assert body["error_code"] == "NO_TEXT_FOUND"

    def test_valid_image_returns_ocr_response(self) -> None:
        from src.models.schemas import OcrPageResponse
        png = _make_png_bytes()
        with patch("src.api.ai.extract_text_with_metadata", new_callable=AsyncMock) as mock_ocr:
            mock_ocr.return_value = OcrPageResponse(
                text="Cau 1: Thu do Viet Nam la gi?",
                line_count=1,
                average_confidence=0.95,
            )
            response = client.post(
                "/api/v1/ai/ocr-page",
                files={"file": ("page.png", png, "image/png")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Cau 1: Thu do Viet Nam la gi?"
        assert data["lineCount"] == 1
        assert data["averageConfidence"] == 0.95


# POST /api/v1/ai/clean-text


class TestCleanText:
    def test_no_api_key_returns_raw_text_fallback(self) -> None:
        with patch("src.api.ai.has_gemini_key", return_value=False):
            response = client.post(
                "/api/v1/ai/clean-text",
                json={"rawText": "Van ban loi chinh ta", "targetLanguage": "vi"},
            )
        assert response.status_code == 200
        assert response.json()["cleanedText"] == "Van ban loi chinh ta"

    def test_gemini_error_returns_502(self) -> None:
        with patch("src.api.ai.has_gemini_key", return_value=True), patch(
            "src.api.ai.call_gemini_chat", new_callable=AsyncMock, side_effect=Exception("timeout")
        ):
            response = client.post(
                "/api/v1/ai/clean-text",
                json={"rawText": "Some text", "targetLanguage": "vi"},
            )
        assert response.status_code == 502

    def test_gemini_bad_json_returns_raw_text_fallback(self) -> None:
        with patch("src.api.ai.has_gemini_key", return_value=True), patch(
            "src.api.ai.call_gemini_chat",
            new_callable=AsyncMock,
            return_value="khong phai JSON hop le",
        ):
            response = client.post(
                "/api/v1/ai/clean-text",
                json={"rawText": "Van ban goc", "targetLanguage": "vi"},
            )
        assert response.status_code == 200
        assert response.json()["cleanedText"] == "Van ban goc"

    def test_gemini_success_returns_cleaned_text(self) -> None:
        ai_response = json.dumps({"cleanedText": "Van ban da duoc lam sach."})
        with patch("src.api.ai.has_gemini_key", return_value=True), patch(
            "src.api.ai.call_gemini_chat",
            new_callable=AsyncMock,
            return_value=ai_response,
        ):
            response = client.post(
                "/api/v1/ai/clean-text",
                json={"rawText": "Van ban loi chinh ta nhieu.", "targetLanguage": "vi"},
            )
        assert response.status_code == 200
        assert response.json()["cleanedText"] == "Van ban da duoc lam sach."

    def test_default_target_language_is_vi(self) -> None:
        with patch("src.api.ai.has_gemini_key", return_value=False):
            response = client.post(
                "/api/v1/ai/clean-text",
                json={"rawText": "test"},
            )
        assert response.status_code == 200

