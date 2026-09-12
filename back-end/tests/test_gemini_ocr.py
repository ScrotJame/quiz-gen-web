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
            mock_settings.return_value.gemini_ocr_model = "gemini-3.1-flash-lite"
            mock_settings.return_value.gemini_ocr_system_prompt = (
                "Perform OCR on this image. Ignore perspective distortion and page curvature. "
                "Transcribe all readable text verbatim."
            )
            text = await extract_text_via_gemini(_make_dummy_image_bytes(), mime_type="image/jpeg")

            assert "Hà Nội" in text
            mock_client.aio.models.generate_content.assert_awaited_once()
            call_kwargs = mock_client.aio.models.generate_content.call_args.kwargs
            assert (
                call_kwargs["config"].system_instruction
                == "Perform OCR on this image. Ignore perspective distortion and page curvature. Transcribe all readable text verbatim."
            )

    @pytest.mark.asyncio
    async def test_extract_text_via_gemini_falls_back_to_next_model(self) -> None:
        """Khi model dau tien bi loi (vi du 429), he thong thu model tiep theo."""
        mock_response = MagicMock()
        mock_response.text = "Van ban tu model 2"

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[Exception("429 ResourceExhausted"), mock_response]
        )

        with patch("src.services.ai.gemini_client.get_gemini_client", return_value=mock_client), patch(
            "src.services.ai.gemini_client.get_settings"
        ) as mock_settings:
            mock_settings.return_value.ocr_model_list = ["gemini-2.5-flash", "gemini-2.0-flash"]
            mock_settings.return_value.gemini_ocr_system_prompt = "Perform OCR..."

            text = await extract_text_via_gemini(_make_dummy_image_bytes())

            assert text == "Van ban tu model 2"
            assert mock_client.aio.models.generate_content.await_count == 2
            # First call used gemini-2.5-flash
            assert mock_client.aio.models.generate_content.call_args_list[0].kwargs["model"] == "gemini-2.5-flash"
            # Second call used gemini-2.0-flash
            assert mock_client.aio.models.generate_content.call_args_list[1].kwargs["model"] == "gemini-2.0-flash"


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
    async def test_gemini_failure_falls_back_to_local_ocr(self) -> None:
        """Khi Gemini fail, phai fallback sang local OCR, khong raise loi len caller."""
        from unittest.mock import MagicMock

        mock_local_engine = MagicMock()
        mock_local_engine.extract_text_with_metadata = AsyncMock(
            return_value=OcrPageResponse(
                text="",
                line_count=0,
                average_confidence=0.0,
                provider="local_vietocr",
            )
        )

        with (
            patch("src.services.ai.ocr.has_gemini_key", return_value=True),
            patch(
                "src.services.ai.ocr.extract_text_via_gemini",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Google API 503 Overloaded"),
            ),
            patch(
                "src.services.ai.ocr.get_local_ocr_engine",
                return_value=mock_local_engine,
            ),
        ):
            # Khong raise — phai fallback va tra ve OcrPageResponse
            resp: OcrPageResponse = await extract_text_with_metadata(_make_dummy_image_bytes())
            assert resp.provider == "local_vietocr"

    @pytest.mark.asyncio
    async def test_no_gemini_key_returns_empty_response(self) -> None:
        with patch("src.services.ai.ocr.has_gemini_key", return_value=False):
            resp: OcrPageResponse = await extract_text_with_metadata(_make_dummy_image_bytes())
            assert resp.text == ""
            assert resp.line_count == 0
            assert resp.average_confidence == 0.0
