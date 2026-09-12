"""Tests for OCR fallback logic (Gemini -> Local OCR).

Mocks all external dependencies (Gemini API, rapidocr, vietocr ONNX)
so tests can run without network or model weights.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.models.schemas import OcrPageResponse


# ---------------------------------------------------------------------------
# Tests: extract_text_from_image
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_text_uses_gemini_when_available():
    """Khi Gemini key ton tai va tra ve text, ket qua den tu Gemini."""
    with (
        patch("src.services.ai.ocr.has_gemini_key", return_value=True),
        patch(
            "src.services.ai.ocr.extract_text_via_gemini",
            new_callable=AsyncMock,
            return_value="Van ban tieng Viet co dau.",
        ),
        patch("src.services.ai.ocr.get_local_ocr_engine") as mock_engine_factory,
    ):
        from src.services.ai.ocr import extract_text_from_image

        result = await extract_text_from_image(b"fake_image_bytes")

    assert result == "Van ban tieng Viet co dau."
    # Local OCR khong duoc goi khi Gemini thanh cong
    mock_engine_factory.assert_not_called()


@pytest.mark.asyncio
async def test_extract_text_falls_back_to_local_ocr_on_gemini_429():
    """Khi Gemini raise loi 429, phai tu dong chuyen sang Local OCR."""
    mock_local_engine = MagicMock()
    mock_local_engine.extract_text = AsyncMock(return_value="Van ban tu Local OCR.")

    with (
        patch("src.services.ai.ocr.has_gemini_key", return_value=True),
        patch(
            "src.services.ai.ocr.extract_text_via_gemini",
            new_callable=AsyncMock,
            side_effect=Exception("429 RESOURCE_EXHAUSTED"),
        ),
        patch(
            "src.services.ai.ocr.get_local_ocr_engine",
            return_value=mock_local_engine,
        ),
    ):
        from src.services.ai.ocr import extract_text_from_image

        result = await extract_text_from_image(b"fake_image_bytes")

    assert result == "Van ban tu Local OCR."
    mock_local_engine.extract_text.assert_called_once()


@pytest.mark.asyncio
async def test_extract_text_falls_back_to_local_ocr_on_gemini_422():
    """Khi Gemini raise loi 422, phai tu dong chuyen sang Local OCR."""
    mock_local_engine = MagicMock()
    mock_local_engine.extract_text = AsyncMock(return_value="Text tu VietOCR.")

    with (
        patch("src.services.ai.ocr.has_gemini_key", return_value=True),
        patch(
            "src.services.ai.ocr.extract_text_via_gemini",
            new_callable=AsyncMock,
            side_effect=Exception("422 INVALID_ARGUMENT"),
        ),
        patch(
            "src.services.ai.ocr.get_local_ocr_engine",
            return_value=mock_local_engine,
        ),
    ):
        from src.services.ai.ocr import extract_text_from_image

        result = await extract_text_from_image(b"fake_image_bytes")

    assert result == "Text tu VietOCR."


@pytest.mark.asyncio
async def test_extract_text_uses_local_ocr_when_no_gemini_key():
    """Khi khong co Gemini key, dung Local OCR ngay."""
    mock_local_engine = MagicMock()
    mock_local_engine.extract_text = AsyncMock(return_value="Local text.")

    with (
        patch("src.services.ai.ocr.has_gemini_key", return_value=False),
        patch(
            "src.services.ai.ocr.get_local_ocr_engine",
            return_value=mock_local_engine,
        ),
    ):
        from src.services.ai.ocr import extract_text_from_image

        result = await extract_text_from_image(b"fake_image_bytes")

    assert result == "Local text."


@pytest.mark.asyncio
async def test_extract_text_returns_empty_when_both_fail():
    """Khi ca Gemini lan Local OCR deu that bai, tra ve string rong."""
    mock_local_engine = MagicMock()
    mock_local_engine.extract_text = AsyncMock(side_effect=Exception("GPU OOM"))

    with (
        patch("src.services.ai.ocr.has_gemini_key", return_value=True),
        patch(
            "src.services.ai.ocr.extract_text_via_gemini",
            new_callable=AsyncMock,
            side_effect=Exception("429 RESOURCE_EXHAUSTED"),
        ),
        patch(
            "src.services.ai.ocr.get_local_ocr_engine",
            return_value=mock_local_engine,
        ),
    ):
        from src.services.ai.ocr import extract_text_from_image

        result = await extract_text_from_image(b"fake_image_bytes")

    assert result == ""


# ---------------------------------------------------------------------------
# Tests: extract_text_with_metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_metadata_gemini_sets_provider_gemini():
    """Khi Gemini thanh cong, provider phai la 'gemini'."""
    with (
        patch("src.services.ai.ocr.has_gemini_key", return_value=True),
        patch(
            "src.services.ai.ocr.extract_text_via_gemini",
            new_callable=AsyncMock,
            return_value="Dong 1\nDong 2\nDong 3",
        ),
    ):
        from src.services.ai.ocr import extract_text_with_metadata

        result = await extract_text_with_metadata(b"fake_image_bytes")

    assert result.provider == "gemini"
    assert result.line_count == 3
    assert result.average_confidence == 1.0


@pytest.mark.asyncio
async def test_extract_metadata_local_sets_provider_local_vietocr():
    """Khi dung Local OCR fallback, provider phai la 'local_vietocr'."""
    local_response = OcrPageResponse(
        text="Text tu VietOCR local.",
        line_count=1,
        average_confidence=0.85,
        provider="local_vietocr",
    )
    mock_local_engine = MagicMock()
    mock_local_engine.extract_text_with_metadata = AsyncMock(return_value=local_response)

    with (
        patch("src.services.ai.ocr.has_gemini_key", return_value=True),
        patch(
            "src.services.ai.ocr.extract_text_via_gemini",
            new_callable=AsyncMock,
            side_effect=Exception("429"),
        ),
        patch(
            "src.services.ai.ocr.get_local_ocr_engine",
            return_value=mock_local_engine,
        ),
    ):
        from src.services.ai.ocr import extract_text_with_metadata

        result = await extract_text_with_metadata(b"fake_image_bytes")

    assert result.provider == "local_vietocr"
    assert result.average_confidence == 0.85


@pytest.mark.asyncio
async def test_extract_metadata_falls_back_when_gemini_returns_empty():
    """Khi Gemini tra ve text rong, he thong phai tu dong fallback sang Local OCR."""
    local_response = OcrPageResponse(
        text="Van ban tu Local OCR khi Gemini rong.",
        line_count=1,
        average_confidence=0.88,
        provider="local_vietocr",
    )
    mock_local_engine = MagicMock()
    mock_local_engine.extract_text_with_metadata = AsyncMock(return_value=local_response)

    with (
        patch("src.services.ai.ocr.has_gemini_key", return_value=True),
        patch(
            "src.services.ai.ocr.extract_text_via_gemini",
            new_callable=AsyncMock,
            return_value="   ",
        ),
        patch(
            "src.services.ai.ocr.get_local_ocr_engine",
            return_value=mock_local_engine,
        ),
    ):
        from src.services.ai.ocr import extract_text_with_metadata

        result = await extract_text_with_metadata(b"fake_image_bytes")

    assert result.provider == "local_vietocr"
    assert result.text == "Van ban tu Local OCR khi Gemini rong."
    mock_local_engine.extract_text_with_metadata.assert_called_once()


@pytest.mark.asyncio
async def test_extract_metadata_preferred_engine_local_vietocr():
    """Khi nguoi dung yeu cau preferred_engine='local_vietocr', bo qua Gemini va dung thang Local OCR."""
    local_response = OcrPageResponse(
        text="Truc tiep Local OCR.",
        line_count=1,
        average_confidence=0.9,
        provider="local_vietocr",
    )
    mock_local_engine = MagicMock()
    mock_local_engine.extract_text_with_metadata = AsyncMock(return_value=local_response)
    mock_gemini = AsyncMock()

    with (
        patch("src.services.ai.ocr.has_gemini_key", return_value=True),
        patch("src.services.ai.ocr.extract_text_via_gemini", new=mock_gemini),
        patch(
            "src.services.ai.ocr.get_local_ocr_engine",
            return_value=mock_local_engine,
        ),
    ):
        from src.services.ai.ocr import extract_text_with_metadata

        result = await extract_text_with_metadata(
            b"fake_image_bytes", preferred_engine="local_vietocr"
        )

    assert result.provider == "local_vietocr"
    assert result.text == "Truc tiep Local OCR."
    mock_gemini.assert_not_called()
    mock_local_engine.extract_text_with_metadata.assert_called_once()



# ---------------------------------------------------------------------------
# Tests: LocalOcrEngine utilities (no model weights needed)
# ---------------------------------------------------------------------------


def test_sort_reading_order_single_column():
    """Tai lieu 1 cot: boxes phai duoc sap xep theo Y tang dan."""
    from src.services.ai.local_ocr import LocalOcrEngine

    boxes = [
        [[100.0, 200.0], [300.0, 200.0], [300.0, 220.0], [100.0, 220.0]],  # Y=210 (dong 2)
        [[100.0, 50.0], [300.0, 50.0], [300.0, 70.0], [100.0, 70.0]],   # Y=60  (dong 1)
        [[100.0, 150.0], [300.0, 150.0], [300.0, 170.0], [100.0, 170.0]], # Y=160 (dong 3 - but center is 160)
    ]
    # Mong doi: dong Y=60, Y=160, Y=210
    sorted_boxes = LocalOcrEngine._sort_reading_order(boxes)
    centers_y = [
        np.array(b, dtype=np.float32)[:, 1].mean() for b in sorted_boxes
    ]
    assert centers_y == sorted(centers_y), "Boxes phai duoc sap xep theo Y tang dan."


def test_sort_reading_order_two_columns():
    """Tai lieu 2 cot: cot trai truoc, cot phai sau."""
    from src.services.ai.local_ocr import LocalOcrEngine

    # Cot trai (x ~ 100), cot phai (x ~ 600) — max_x = 700
    # col_threshold=0.45 -> pivot = 700*0.45 = 315
    left_box_top = [[50.0, 50.0], [200.0, 50.0], [200.0, 70.0], [50.0, 70.0]]   # cx=125, cy=60
    left_box_bot = [[50.0, 200.0], [200.0, 200.0], [200.0, 220.0], [50.0, 220.0]] # cx=125, cy=210
    right_box_top = [[550.0, 50.0], [700.0, 50.0], [700.0, 70.0], [550.0, 70.0]]   # cx=625, cy=60
    right_box_bot = [[550.0, 200.0], [700.0, 200.0], [700.0, 220.0], [550.0, 220.0]] # cx=625, cy=210

    # Dau vao xen ke
    boxes = [right_box_top, left_box_bot, right_box_bot, left_box_top]
    sorted_boxes = LocalOcrEngine._sort_reading_order(boxes)

    # Ket qua mong doi: left_top, left_bot, right_top, right_bot
    def cx(b: list) -> float:
        return np.array(b, dtype=np.float32)[:, 0].mean()

    assert cx(sorted_boxes[0]) < 315  # left
    assert cx(sorted_boxes[1]) < 315  # left
    assert cx(sorted_boxes[2]) > 315  # right
    assert cx(sorted_boxes[3]) > 315  # right


def test_sort_reading_order_empty():
    """Danh sach rong khong gay loi."""
    from src.services.ai.local_ocr import LocalOcrEngine

    assert LocalOcrEngine._sort_reading_order([]) == []


def test_get_local_ocr_engine_returns_none_when_disabled(monkeypatch):
    """Engine factory phai tra ve None khi local_ocr_enabled=False."""
    import importlib

    import src.services.ai.local_ocr as local_ocr_mod

    # Reset lru_cache
    local_ocr_mod.get_local_ocr_engine.cache_clear()

    mock_settings = MagicMock()
    mock_settings.local_ocr_enabled = False

    with patch("src.services.ai.local_ocr.get_settings", return_value=mock_settings):
        result = local_ocr_mod.get_local_ocr_engine()

    assert result is None
    # Cleanup cache sau test
    local_ocr_mod.get_local_ocr_engine.cache_clear()


def test_ctc_greedy_decode_basic():
    """CTC greedy decode: blank tokens va repeated chars phai duoc xu ly dung."""
    from src.services.ai.local_ocr import VietOCROnnxRecognizer, _VIETOCR_VOCAB

    # Tao recognizer voi session mock (khong can ONNX session)
    recognizer = object.__new__(VietOCROnnxRecognizer)

    vocab_size = len(_VIETOCR_VOCAB)
    # Tim index chinh xac cua 'A' va 'B' trong vocab
    idx_A = _VIETOCR_VOCAB.index("A")
    idx_B = _VIETOCR_VOCAB.index("B")

    # Simulate: 'A', blank, 'B', 'B' repeat (CTC collapses), blank -> "AB"
    logits = np.zeros((5, vocab_size + 1), dtype=np.float32)
    logits[0, idx_A] = 10.0       # 'A'
    logits[1, vocab_size] = 10.0  # blank
    logits[2, idx_B] = 10.0       # 'B'
    logits[3, idx_B] = 10.0       # 'B' repeat -> CTC collapses
    logits[4, vocab_size] = 10.0  # blank

    result = recognizer._ctc_greedy_decode(logits)
    assert result == "AB"


@pytest.mark.asyncio
async def test_real_local_ocr_engine_extracts_text():
    """Kiem tra LocalOcrEngine that khoi tao va extract text tu anh mau khong loi."""
    import io
    from PIL import Image, ImageDraw
    from src.services.ai.local_ocr import LocalOcrEngine

    engine = LocalOcrEngine()
    img = Image.new("RGB", (300, 80), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 20), "Test OCR Local", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    resp = await engine.extract_text_with_metadata(buf.getvalue())
    assert resp.provider == "local_vietocr"
    assert resp.line_count >= 1
    assert "Test" in resp.text or "OCR" in resp.text


def test_sort_and_group_lines_multiline():
    """Gom nhóm các box thành từng dòng và sắp xếp trái sang phải."""
    from src.services.ai.local_ocr import LocalOcrEngine

    test_boxes = [
        [[120.0, 20.0], [180.0, 20.0], [180.0, 40.0], [120.0, 40.0]],  # Line 1, Word 2
        [[50.0, 20.0], [100.0, 20.0], [100.0, 40.0], [50.0, 40.0]],    # Line 1, Word 1
        [[50.0, 70.0], [110.0, 70.0], [110.0, 90.0], [50.0, 90.0]],    # Line 2, Word 1
    ]
    grouped = LocalOcrEngine._sort_and_group_lines(test_boxes)
    assert len(grouped) == 2
    assert len(grouped[0]) == 2
    assert len(grouped[1]) == 1
    # Trong line 1: box cx nhỏ hơn (50-100) phải đứng trước (120-180)
    assert grouped[0][0][0][0] == 50.0
    assert grouped[0][1][0][0] == 120.0


def test_sort_and_group_lines_empty():
    """Danh sách box rỗng không gây lỗi."""
    from src.services.ai.local_ocr import LocalOcrEngine

    assert LocalOcrEngine._sort_and_group_lines([]) == []
    assert LocalOcrEngine._sort_and_group_lines(None) == []  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_real_vietocr_seq2seq_recognizer():
    """Kiểm tra nhận diện trực tiếp bằng VietOCRSeq2SeqRecognizer nếu có file weights."""
    import os
    from PIL import Image, ImageDraw, ImageFont
    from src.services.ai.local_ocr import VietOCRSeq2SeqRecognizer, _resolve_vgg_seq2seq_path

    model_path = _resolve_vgg_seq2seq_path()
    if not model_path or not os.path.isfile(model_path):
        pytest.skip("Chưa có file weights vgg_seq2seq.pth")

    recognizer = VietOCRSeq2SeqRecognizer(weights_path=model_path, device="cpu")
    img = Image.new("RGB", (400, 60), color="white")
    draw = ImageDraw.Draw(img)

    font = None
    for font_path in ("C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.isfile(font_path):
            try:
                font = ImageFont.truetype(font_path, 28)
                break
            except Exception:
                pass

    draw.text((10, 15), "Viet Nam", fill="black", font=font)

    sents, probs = recognizer.recognize_batch([img])
    assert len(sents) == 1
    assert len(probs) == 1
    assert len(sents[0]) > 0
    assert probs[0] > 0.0


def test_split_tall_boxes():
    """Kiểm tra tự động chia đôi bounding box bị gộp nhầm 2 dòng."""
    from src.services.ai.local_ocr import LocalOcrEngine

    boxes = [
        [[50.0, 10.0], [400.0, 10.0], [400.0, 30.0], [50.0, 30.0]],   # h=20 (dòng 1)
        [[50.0, 35.0], [400.0, 35.0], [400.0, 55.0], [50.0, 55.0]],   # h=20 (dòng 2)
        [[50.0, 60.0], [400.0, 60.0], [400.0, 100.0], [50.0, 100.0]], # h=40 (> 1.75 * 20 -> gộp 2 dòng)
    ]
    refined = LocalOcrEngine._split_tall_boxes(boxes)
    assert len(refined) == 4
    # Box 3 và Box 4 được tách từ box cao h=40
    pts_b3 = np.array(refined[2])
    pts_b4 = np.array(refined[3])
    assert pts_b3[:, 1].max() == 80.0
    assert pts_b4[:, 1].min() == 80.0


def test_enhance_contrast_returns_valid_image():
    """Kiểm tra bộ lọc CLAHE không làm hỏng shape và định dạng ảnh."""
    from src.services.ai.local_ocr import LocalOcrEngine

    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    enhanced = LocalOcrEngine._enhance_contrast(dummy_img)
    assert enhanced.shape == dummy_img.shape
    assert enhanced.dtype == np.uint8





