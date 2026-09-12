"""Tests cho Gemini Vision OCR service và fallback logic."""
from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from src.models.schemas import OcrPageResponse
from src.services.ai.gemini_client import (
    extract_text_via_gemini,
    get_gemini_client,
    has_gemini_key,
)
from src.services.ai.ocr import (
    extract_text_from_image,
    extract_text_with_metadata,
)


def _make_dummy_image_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), color="white").save(buf, format="JPEG")
    return buf.getvalue()


class TestGeminiClientConfig:
    def test_has_gemini_key_empty(self) -> None:
        with patch("src.services.ai.gemini_client.get_settings") as mock_settings:
            mock_settings.return_value.gemini_api_key = ""
            assert has_gemini_key() is False

    def test_has_gemini_key_placeholder(self) -> None:
        with patch("src.services.ai.gemini_client.get_settings") as mock_settings:
            mock_settings.return_value.gemini_api_key = "your-api-key-here"
            assert has_gemini_key() is False

    def test_has_gemini_key_valid(self) -> None:
        with patch("src.services.ai.gemini_client.get_settings") as mock_settings:
            mock_settings.return_value.gemini_api_key = "AIzaSyDummyKey12345"
            assert has_gemini_key() is True

    def test_get_gemini_client_none_when_no_key(self) -> None:
        with patch("src.services.ai.gemini_client.has_gemini_key", return_value=False):
            assert get_gemini_client() is None


class TestGeminiOcrCall:
    @pytest.mark.asyncio
    async def test_extract_text_via_gemini_no_key_raises_value_error(self) -> None:
        with patch("src.services.ai.gemini_client.get_gemini_client", return_value=None):
            with pytest.raises(ValueError, match="GEMINI_API_KEY chưa được cấu hình"):
                await extract_text_via_gemini(b"fake_bytes")

    @pytest.mark.asyncio
    async def test_extract_text_via_gemini_success(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "Câu 1: Thủ đô của Việt Nam là gì?\nA. Hà Nội\nB. TP HCM"

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("src.services.ai.gemini_client.get_gemini_client", return_value=mock_client), patch(
            "src.services.ai.gemini_client.get_settings"
        ) as mock_settings:
            mock_settings.return_value.gemini_ocr_model = "gemini-2.0-flash-lite"
            text = await extract_text_via_gemini(_make_dummy_image_bytes(), mime_type="image/jpeg")

            assert "Hà Nội" in text
            mock_client.aio.models.generate_content.assert_awaited_once()


class TestOcrPipelineIntegration:
    @pytest.mark.asyncio
    async def test_extract_text_with_gemini_active(self) -> None:
        mock_ocr_text = "Câu 1: Đâu là ngôn ngữ lập trình?\nA. Python\nB. HTML"
        with patch("src.services.ai.ocr.has_gemini_key", return_value=True), patch(
            "src.services.ai.ocr.extract_text_via_gemini",
            new_callable=AsyncMock,
            return_value=mock_ocr_text,
        ):
            resp: OcrPageResponse = await extract_text_with_metadata(_make_dummy_image_bytes())

            assert resp.text == mock_ocr_text
            assert resp.line_count == 3
            assert resp.average_confidence == 1.0

    @pytest.mark.asyncio
    async def test_gemini_failure_falls_back_to_rapidocr(self) -> None:
        with patch("src.services.ai.ocr.has_gemini_key", return_value=True), patch(
            "src.services.ai.ocr.extract_text_via_gemini",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Google API 503 Overloaded"),
        ), patch("src.services.ai.ocr._extract_rapidocr_with_metadata") as mock_rapid:
            mock_rapid.return_value = OcrPageResponse(
                text="Fallback text from RapidOCR",
                line_count=1,
                average_confidence=0.88,
            )

            resp: OcrPageResponse = await extract_text_with_metadata(_make_dummy_image_bytes())

            assert resp.text == "Fallback text from RapidOCR"
            assert resp.average_confidence == 0.88
            mock_rapid.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_gemini_key_uses_rapidocr_directly(self) -> None:
        with patch("src.services.ai.ocr.has_gemini_key", return_value=False), patch(
            "src.services.ai.ocr._extract_rapidocr_with_metadata"
        ) as mock_rapid:
            mock_rapid.return_value = OcrPageResponse(
                text="Offline RapidOCR text",
                line_count=1,
                average_confidence=0.92,
            )

            resp: OcrPageResponse = await extract_text_with_metadata(_make_dummy_image_bytes())

            assert resp.text == "Offline RapidOCR text"
            assert resp.average_confidence == 0.92
            mock_rapid.assert_called_once()
